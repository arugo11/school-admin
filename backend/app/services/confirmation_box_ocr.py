from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps

from app.clients.azure_openai import AzureOpenAIClient
from app.core.config import settings
from app.schemas import NormalizedOcrDocument, OcrConfidenceSummary, OcrItem


@dataclass
class QuestionRegion:
    problem_no: str
    row_box: tuple[int, int, int, int]
    work_box: tuple[int, int, int, int]
    final_box: tuple[int, int, int, int]


def _cleanup_math_ocr_text(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    replacements = {
        "Ifrac": "\\frac",
        "lfrac": "\\frac",
        "|frac": "\\frac",
        "Isqrt": "\\sqrt",
        "lsqrt": "\\sqrt",
        "|sqrt": "\\sqrt",
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    text = re.sub(r"}\s+{", "}{", text)
    text = re.sub(r"\\frac\s*{", r"\\frac{", text)
    text = re.sub(r"\\sqrt\s*{", r"\\sqrt{", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _open_image(image_path: Path) -> Image.Image:
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image)
    return image.convert("RGB")


def _save_crop(image: Image.Image, crop_box: tuple[int, int, int, int], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    image.crop(crop_box).save(target, format="PNG")


def _extract_lines(raw_ocr: dict) -> list[dict]:
    analyze_result = raw_ocr.get("analyzeResult", {})
    if "readResults" in analyze_result:
        pages = analyze_result.get("readResults", [])
    else:
        pages = analyze_result.get("pages", [])
    lines: list[dict] = []
    for page in pages:
        lines.extend(page.get("lines", []))
    return lines


def _parse_problem_no(text: str) -> str | None:
    upper = text.strip().upper()
    match = re.search(r"Q\s*0*([0-9]+)", upper)
    if not match:
        return None
    return f"Q{int(match.group(1))}"


def _label_lines(raw_ocr: dict) -> list[tuple[str, list[float]]]:
    labels: list[tuple[str, list[float]]] = []
    for line in _extract_lines(raw_ocr):
        text = str(line.get("text", ""))
        if "CT-" in text.upper():
            continue
        problem_no = _parse_problem_no(text)
        if problem_no is None:
            continue
        bbox = line.get("boundingBox") or line.get("polygon") or []
        if bbox:
            labels.append((problem_no, [float(value) for value in bbox]))
    return labels


def _help_line_rects(raw_ocr: dict) -> dict[str, tuple[float, float, float, float]]:
    result: dict[str, tuple[float, float, float, float]] = {}
    for line in _extract_lines(raw_ocr):
        text = str(line.get("text", "")).strip().upper()
        bbox = line.get("boundingBox") or line.get("polygon") or []
        if "CT-" not in text or "-Q" not in text or not bbox:
            continue
        problem_no = _parse_problem_no(text)
        if problem_no is None:
            continue
        result[problem_no] = _bbox_to_rect([float(value) for value in bbox])
    return result


def _bbox_to_rect(bbox: list[float]) -> tuple[float, float, float, float]:
    xs = bbox[0::2]
    ys = bbox[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def detect_question_regions(image_path: Path, raw_ocr: dict) -> list[QuestionRegion]:
    image = _open_image(image_path)
    width, height = image.size
    labels = _label_lines(raw_ocr)
    help_rects = _help_line_rects(raw_ocr)
    if not labels and not help_rects:
        return []
    label_rects = {problem_no: _bbox_to_rect(bbox) for problem_no, bbox in labels}
    help_tops = {problem_no: rect[1] for problem_no, rect in help_rects.items()}
    problem_nos = sorted(set(label_rects) | set(help_rects), key=lambda value: int(value[1:]))
    if not problem_nos:
        return []
    inferred_offsets = [
        help_tops[problem_no] - label_rects[problem_no][1]
        for problem_no in problem_nos
        if problem_no in help_tops and problem_no in label_rects
    ]
    default_offset = sum(inferred_offsets) / len(inferred_offsets) if inferred_offsets else 94.0
    label_right = max((rect[2] for rect in label_rects.values()), default=int(width * 0.08))
    final_left = int(width * 0.74)
    work_left = int(label_right + 18)
    bottom_margin = int(height * 0.08)
    regions: list[QuestionRegion] = []
    for index, problem_no in enumerate(problem_nos):
        label_rect = label_rects.get(problem_no)
        help_top = help_tops.get(problem_no)
        label_top = label_rect[1] if label_rect else max(0.0, (help_top or 0.0) - default_offset)
        next_help_top = help_tops.get(problem_nos[index + 1]) if index + 1 < len(problem_nos) else None
        row_top = max(0, int(label_top - 16))
        if help_top is not None:
            content_bottom = min(height, int(help_top - 8))
        elif next_help_top is not None:
            content_bottom = min(height, int(next_help_top - default_offset - 8))
        else:
            content_bottom = height - bottom_margin
        inner_top = min(content_bottom - 10, row_top + 14)
        row_bottom = content_bottom
        work_box = (min(width - 1, work_left), inner_top, max(min(width - 1, final_left - 12), min(width - 1, work_left + 50)), content_bottom)
        final_box = (min(width - 1, final_left), inner_top, width - 12, content_bottom)
        row_box = (0, row_top, width, row_bottom)
        regions.append(QuestionRegion(problem_no=problem_no, row_box=row_box, work_box=work_box, final_box=final_box))
    return regions


def _fallback_row_texts(raw_ocr: dict, regions: list[QuestionRegion]) -> dict[str, dict[str, str]]:
    lines = []
    for line in _extract_lines(raw_ocr):
        bbox = line.get("boundingBox") or line.get("polygon") or []
        if not bbox:
            continue
        xs = [float(v) for v in bbox[0::2]]
        ys = [float(v) for v in bbox[1::2]]
        text = str(line.get("text", "")).strip()
        if not text:
            continue
        lines.append(
            {
                "text": text,
                "center_x": (min(xs) + max(xs)) / 2,
                "center_y": (min(ys) + max(ys)) / 2,
                "right": max(xs),
            }
        )
    if not lines:
        return {}
    final_boundary = max(line["right"] for line in lines) * 0.72
    result: dict[str, dict[str, str]] = {}
    for region in regions:
        row_lines = [
            line for line in lines
            if region.row_box[1] <= line["center_y"] <= region.row_box[3]
            and not line["text"].upper().startswith(region.problem_no)
            and "CT-" not in line["text"]
        ]
        work_text = " ".join(line["text"] for line in row_lines if line["center_x"] < final_boundary).strip()
        final_answer = " ".join(line["text"] for line in row_lines if line["center_x"] >= final_boundary).strip()
        result[region.problem_no] = {"work_text": work_text, "final_answer": final_answer}
    return result


def _build_contact_sheet(crop_dir: Path, regions: list[QuestionRegion], crop_kind: str) -> bytes:
    label_width = 86
    padding = 12
    entries: list[tuple[str, Image.Image]] = []
    max_width = 0
    total_height = padding
    for region in regions:
        crop_path = crop_dir / f"{region.problem_no.lower()}-{crop_kind}.png"
        crop = Image.open(crop_path).convert("RGB")
        entries.append((region.problem_no, crop))
        max_width = max(max_width, crop.width)
        total_height += crop.height + padding
    sheet = Image.new("RGB", (label_width + max_width + padding * 2, total_height), color=(250, 247, 240))
    draw = ImageDraw.Draw(sheet)
    y = padding
    for problem_no, crop in entries:
        draw.text((12, y + 10), problem_no, fill=(25, 37, 45))
        sheet.paste(crop, (label_width, y))
        y += crop.height + padding
    buffer = io.BytesIO()
    sheet.save(buffer, format="PNG")
    return buffer.getvalue()


async def extract_confirmation_test_boxes(
    *,
    image_path: Path,
    raw_ocr: dict,
    student_id: str,
    source_image_id: str,
    test_id: str,
    source_image_relpath: str,
    aoai_client: AzureOpenAIClient,
) -> tuple[NormalizedOcrDocument, dict[str, Any]]:
    image = _open_image(image_path)
    regions = detect_question_regions(image_path, raw_ocr)
    notes: list[str] = []
    items: list[OcrItem] = []
    debug_mapping: list[dict[str, Any]] = []
    crop_dir = settings.ocr_debug_dir / f"{source_image_id}_crops"
    crop_dir.mkdir(parents=True, exist_ok=True)

    for region in regions:
        _save_crop(image, region.work_box, crop_dir / f"{region.problem_no.lower()}-work.png")
        _save_crop(image, region.final_box, crop_dir / f"{region.problem_no.lower()}-final.png")

    fallback_rows = _fallback_row_texts(raw_ocr, regions)
    bulk_result: dict[str, Any] = {"items": []}
    bulk_failure: str | None = None
    try:
        bulk_result = await aoai_client.extract_box_ocr_bulk(
            work_sheet_bytes=_build_contact_sheet(crop_dir, regions, "work"),
            final_sheet_bytes=_build_contact_sheet(crop_dir, regions, "final"),
            problem_nos=[region.problem_no for region in regions],
        )
    except Exception as exc:
        bulk_failure = exc.__class__.__name__

    bulk_map = {str(item.get("problem_no", "")).upper(): item for item in bulk_result.get("items", [])}

    for region in regions:
        work_path = crop_dir / f"{region.problem_no.lower()}-work.png"
        final_path = crop_dir / f"{region.problem_no.lower()}-final.png"
        extracted = bulk_map.get(region.problem_no, {})
        work_text = _cleanup_math_ocr_text(
            str(extracted.get("work_text", "") or "").strip() or fallback_rows.get(region.problem_no, {}).get("work_text", "")
        )
        final_answer = _cleanup_math_ocr_text(
            str(extracted.get("final_answer", "") or "").strip() or fallback_rows.get(region.problem_no, {}).get("final_answer", "")
        )
        confidence = str(extracted.get("confidence", "low") or "low")
        box_notes = [str(note) for note in extracted.get("notes", [])]
        if bulk_failure:
            box_notes.append(f"aoai-bulk-fallback: {bulk_failure}")
        recognized_answer = final_answer.strip() or "unknown"
        uncertainty: list[str] = []
        if confidence == "low":
            uncertainty.append("low-confidence")
        if not final_answer.strip():
            uncertainty.append("final-answer-missing")
        if work_text.strip() and final_answer.strip() and work_text.strip() != final_answer.strip():
            uncertainty.append("work-final-mismatch")
        if box_notes:
            uncertainty.extend(box_notes)
        if uncertainty:
            notes.append(f"{region.problem_no}: {', '.join(uncertainty)}")
        items.append(
            OcrItem(
                problem_no=region.problem_no,
                recognized_answer=recognized_answer,
                work_text=work_text or None,
                final_answer=final_answer or None,
                answer_source="final_answer" if final_answer.strip() else "unknown",
                source_image_path=source_image_relpath,
                work_image_path=str(work_path.relative_to(settings.repo_root)),
                final_image_path=str(final_path.relative_to(settings.repo_root)),
                raw_text=f"{region.problem_no} | work={work_text or ''} | final={final_answer or ''}",
                uncertainty=uncertainty,
            )
        )
        debug_mapping.append(
            {
                "problem_no": region.problem_no,
                "row_box": region.row_box,
                "work_box": region.work_box,
                "final_box": region.final_box,
                "work_image_path": str(work_path.relative_to(settings.repo_root)),
                "final_image_path": str(final_path.relative_to(settings.repo_root)),
                "work_text": work_text,
                "final_answer": final_answer,
                "confidence": confidence,
                "notes": box_notes,
            }
        )

    document = NormalizedOcrDocument(
        student_id=student_id,
        source_image_id=source_image_id,
        source_image_paths=[source_image_relpath],
        page_type="worksheet",
        ocr_confidence_summary=OcrConfidenceSummary(
            low_confidence_count=sum(1 for item in items if "low-confidence" in item.uncertainty),
            notes=notes,
        ),
        items=items,
        test_id=test_id,
        source_alias="qa-verify-10k-jp",
    )
    debug_payload = {
        "student_id": student_id,
        "source_image_id": source_image_id,
        "test_id": test_id,
        "source_image_path": source_image_relpath,
        "box_ocr": True,
        "mapping": debug_mapping,
        "normalized": document.model_dump(),
    }
    return document, debug_payload
