from __future__ import annotations

import mimetypes
import re
import io
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
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
    notes: list[str]


def _open_image(image_path: Path) -> Image.Image:
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image)
    return image.convert("RGB")


def _prepare_llm_image(image: Image.Image, mime_type: str) -> tuple[bytes, str]:
    target = image.copy()
    max_side = 1280
    if max(target.size) > max_side:
        target.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    normalized_mime = "image/jpeg" if mime_type not in {"image/png", "image/webp"} else mime_type
    if normalized_mime == "image/png":
        target.save(output, format="PNG")
    elif normalized_mime == "image/webp":
        target.save(output, format="WEBP", quality=90)
    else:
        target.save(output, format="JPEG", quality=82, optimize=True)
        normalized_mime = "image/jpeg"
    return output.getvalue(), normalized_mime


def _clamp_box(values: list[Any], width: int, height: int) -> tuple[int, int, int, int]:
    if len(values) != 4:
        raise ValueError("invalid-box")
    left, top, right, bottom = [int(float(value)) for value in values]
    left = max(0, min(width - 1, round(width * left / 1000)))
    right = max(left + 1, min(width, round(width * right / 1000)))
    top = max(0, min(height - 1, round(height * top / 1000)))
    bottom = max(top + 1, min(height, round(height * bottom / 1000)))
    return left, top, right, bottom


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
        "√": "\\sqrt",
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    text = re.sub(r"}\s+{", "}{", text)
    text = re.sub(r"\\frac\s*{", r"\\frac{", text)
    text = re.sub(r"\\sqrt\s*{", r"\\sqrt{", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _save_crop(image: Image.Image, crop_box: tuple[int, int, int, int], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    image.crop(crop_box).save(target, format="PNG")


def _build_contact_sheet(crop_dir: Path, regions: list[QuestionRegion], crop_kind: str) -> bytes:
    label_width = 86
    padding = 12
    entries: list[tuple[str, Image.Image]] = []
    max_width = 0
    total_height = padding
    for region in regions:
        crop_path = crop_dir / f"{region.problem_no.lower()}-{crop_kind}.png"
        crop = Image.open(crop_path).convert("RGB")
        crop.thumbnail((560, 160), Image.Resampling.LANCZOS)
        entries.append((region.problem_no, crop))
        max_width = max(max_width, crop.width)
        total_height += crop.height + padding
    sheet = Image.new("RGB", (label_width + max_width + padding * 2, total_height), color=(248, 248, 248))
    draw = ImageDraw.Draw(sheet)
    y = padding
    for problem_no, crop in entries:
        draw.text((12, y + 10), problem_no, fill=(25, 25, 25))
        sheet.paste(crop, (label_width, y))
        y += crop.height + padding
    buffer = io.BytesIO()
    sheet.save(buffer, format="PNG")
    return buffer.getvalue()


def _extract_regions(layout_payload: dict[str, Any], image_size: tuple[int, int]) -> list[QuestionRegion]:
    width, height = image_size
    regions: list[QuestionRegion] = []
    for raw in layout_payload.get("regions", []):
        problem_no = str(raw.get("problem_no", "")).strip().upper()
        if not re.fullmatch(r"Q\d+", problem_no):
            continue
        try:
            regions.append(
                QuestionRegion(
                    problem_no=problem_no,
                    row_box=_clamp_box(list(raw.get("row_box", [])), width, height),
                    work_box=_clamp_box(list(raw.get("work_box", [])), width, height),
                    final_box=_clamp_box(list(raw.get("final_box", [])), width, height),
                    notes=[str(note) for note in raw.get("notes", [])],
                )
            )
        except Exception:
            continue
    regions.sort(key=lambda item: int(item.problem_no[1:]))
    return regions


def _detect_dark_label_rows(image: Image.Image) -> list[tuple[int, int]]:
    gray = image.convert("L")
    width, height = gray.size
    left_band = max(1, int(width * 0.14))
    row_scores: list[int] = []
    for y in range(height):
        darkness = 0
        for x in range(left_band):
            darkness += 255 - gray.getpixel((x, y))
        row_scores.append(darkness // left_band)
    threshold = max(40, int(max(row_scores) * 0.55))
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for y, score in enumerate(row_scores):
        if score >= threshold and start is None:
            start = y
        elif score < threshold and start is not None:
            if y - start >= max(20, height // 45):
                spans.append((start, y))
            start = None
    if start is not None and height - start >= max(20, height // 45):
        spans.append((start, height - 1))
    merged: list[tuple[int, int]] = []
    for top, bottom in spans:
        if merged and top - merged[-1][1] < max(8, height // 120):
            merged[-1] = (merged[-1][0], bottom)
        else:
            merged.append((top, bottom))
    return merged


def _dedupe_rectangles(rectangles: list[tuple[int, int, int, int]], *, tolerance: int = 18) -> list[tuple[int, int, int, int]]:
    deduped: list[tuple[int, int, int, int]] = []
    for rect in sorted(rectangles, key=lambda item: (item[1], item[0], item[2] * item[3]), reverse=False):
        x, y, w, h = rect
        if any(abs(x - dx) <= tolerance and abs(y - dy) <= tolerance and abs(w - dw) <= tolerance and abs(h - dh) <= tolerance for dx, dy, dw, dh in deduped):
            continue
        deduped.append(rect)
    return deduped


def _detect_box_regions(image: Image.Image, visible_problem_nos: list[str]) -> list[QuestionRegion]:
    rgb = np.array(image)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, threshold = cv2.threshold(blur, 200, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    height, width = gray.shape
    final_candidates: list[tuple[int, int, int, int]] = []
    row_candidates: list[tuple[int, int, int, int]] = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < 10_000 or w < 120 or h < 40:
            continue
        aspect_ratio = w / max(h, 1)
        width_ratio = w / width
        height_ratio = h / height
        if x > int(width * 0.55) and 0.9 <= aspect_ratio <= 1.8 and 0.08 <= width_ratio <= 0.24 and 0.06 <= height_ratio <= 0.18:
            final_candidates.append((x, y, w, h))
        if width_ratio >= 0.68 and aspect_ratio >= 3.0 and 0.08 <= height_ratio <= 0.24:
            row_candidates.append((x, y, w, h))

    final_candidates = sorted(_dedupe_rectangles(final_candidates, tolerance=14), key=lambda item: item[1])
    row_candidates = sorted(_dedupe_rectangles(row_candidates, tolerance=24), key=lambda item: item[1])
    if not final_candidates:
        return []

    ordered_problem_nos = sorted(set(visible_problem_nos), key=lambda value: int(value[1:])) if visible_problem_nos else [f"Q{index + 1}" for index in range(len(final_candidates))]
    if len(ordered_problem_nos) != len(final_candidates):
        count = min(len(ordered_problem_nos), len(final_candidates))
        final_candidates = final_candidates[:count]
        ordered_problem_nos = ordered_problem_nos[:count]

    regions: list[QuestionRegion] = []
    default_row_left = int(width * 0.09)
    default_row_right = int(width * 0.92)
    for problem_no, (fx, fy, fw, fh) in zip(ordered_problem_nos, final_candidates, strict=True):
        final_box = (fx, fy, fx + fw, fy + fh)
        final_center_y = fy + fh / 2
        containing_rows = [
            rect
            for rect in row_candidates
            if rect[1] <= final_center_y <= rect[1] + rect[3] and rect[0] <= fx <= rect[0] + rect[2]
        ]
        if containing_rows:
            row_x, row_y, row_w, row_h = min(containing_rows, key=lambda rect: abs((rect[1] + rect[3] / 2) - final_center_y))
            row_box = (row_x, row_y, row_x + row_w, row_y + row_h)
            note = "contour-row+final-box-detection"
        else:
            row_margin_y = int(fh * 0.42)
            row_box = (
                default_row_left,
                max(0, fy - row_margin_y),
                default_row_right,
                min(height, fy + fh + row_margin_y),
            )
            note = "contour-final-box-detection"

        gap_left = max(10, fx - row_box[0])
        work_left = row_box[0] + int(gap_left * 0.16)
        work_right = max(work_left + 60, fx - 18)
        work_box = (
            work_left,
            max(0, row_box[1] + 6),
            work_right,
            min(height, row_box[3] - 6),
        )
        regions.append(
            QuestionRegion(
                problem_no=problem_no,
                row_box=row_box,
                work_box=work_box,
                final_box=final_box,
                notes=[note],
            )
        )
    return regions


def _regions_from_visible_questions(image: Image.Image, visible_problem_nos: list[str]) -> list[QuestionRegion]:
    contour_regions = _detect_box_regions(image, visible_problem_nos)
    if contour_regions:
        return contour_regions
    width, height = image.size
    row_spans = _detect_dark_label_rows(image)
    if not row_spans:
        return []
    if visible_problem_nos:
        ordered_problem_nos = sorted(set(visible_problem_nos), key=lambda value: int(value[1:]))
    else:
        ordered_problem_nos = [f"Q{index + 1}" for index in range(len(row_spans))]
    if len(ordered_problem_nos) != len(row_spans):
        count = min(len(ordered_problem_nos), len(row_spans))
        row_spans = row_spans[:count]
        ordered_problem_nos = ordered_problem_nos[:count]
    left_label_right = int(width * 0.11)
    final_left = int(width * 0.77)
    work_left = left_label_right + 10
    row_margin = max(4, height // 250)
    regions: list[QuestionRegion] = []
    for problem_no, (top, bottom) in zip(ordered_problem_nos, row_spans, strict=True):
        row_top = max(0, top - row_margin)
        row_bottom = min(height, bottom + row_margin)
        work_box = (work_left, row_top + 4, max(work_left + 50, final_left - 10), row_bottom - 4)
        final_box = (final_left, row_top + 4, width - 8, row_bottom - 4)
        regions.append(
            QuestionRegion(
                problem_no=problem_no,
                row_box=(0, row_top, width, row_bottom),
                work_box=work_box,
                final_box=final_box,
                notes=["image-processed-row-detection"],
            )
        )
    return regions


def _confidence_summary(items: list[OcrItem]) -> OcrConfidenceSummary:
    notes: list[str] = []
    for item in items:
        if item.uncertainty:
            notes.append(f"{item.problem_no}: {', '.join(item.uncertainty)}")
    return OcrConfidenceSummary(
        low_confidence_count=sum(1 for item in items if item.uncertainty),
        notes=notes,
    )


async def extract_llm_ocr_document(
    *,
    image_path: Path,
    student_id: str,
    source_image_id: str,
    source_image_relpath: str,
    aoai_client: AzureOpenAIClient,
) -> tuple[dict[str, Any], NormalizedOcrDocument, dict[str, Any]]:
    image = _open_image(image_path)
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    started_total = time.perf_counter()
    image_bytes, mime_type = _prepare_llm_image(image, mime_type)

    started_layout = time.perf_counter()
    layout_payload = await aoai_client.detect_sheet_layout(
        image_bytes=image_bytes,
        mime_type=mime_type,
        mode_hint="auto",
    )
    layout_duration_ms = (time.perf_counter() - started_layout) * 1000
    mode = str(layout_payload.get("mode", "unknown") or "unknown")
    if mode == "confirmation_test":
        visible_problem_nos = [str(problem_no).upper() for problem_no in layout_payload.get("visible_problem_nos", [])]
        region_list = _extract_regions(layout_payload, image.size)
        if not region_list:
            region_list = _regions_from_visible_questions(image, visible_problem_nos)
        regions = {region.problem_no: region for region in region_list}
        crop_dir = settings.ocr_debug_dir / f"{source_image_id}_crops"
        crop_dir.mkdir(parents=True, exist_ok=True)
        for region in region_list:
            _save_crop(image, region.work_box, crop_dir / f"{region.problem_no.lower()}-work.png")
            _save_crop(image, region.final_box, crop_dir / f"{region.problem_no.lower()}-final.png")
        started_read = time.perf_counter()
        read_payload = await aoai_client.extract_box_ocr_bulk(
            work_sheet_bytes=_build_contact_sheet(crop_dir, region_list, "work"),
            final_sheet_bytes=_build_contact_sheet(crop_dir, region_list, "final"),
            problem_nos=[region.problem_no for region in region_list],
        )
        read_duration_ms = (time.perf_counter() - started_read) * 1000
        read_payload = {
            "mode": "confirmation_test",
            "test_id": layout_payload.get("test_id"),
            "items": read_payload.get("items", []),
            "notes": read_payload.get("notes", []),
        }
        items: list[OcrItem] = []
        mapping: list[dict[str, Any]] = []
        for raw_item in read_payload.get("items", []):
            problem_no = str(raw_item.get("problem_no", "")).strip().upper()
            if not re.fullmatch(r"Q\d+", problem_no):
                continue
            region = regions.get(problem_no)
            work_path: str | None = None
            final_path: str | None = None
            row_box = work_box = final_box = None
            if region is not None:
                work_target = crop_dir / f"{problem_no.lower()}-work.png"
                final_target = crop_dir / f"{problem_no.lower()}-final.png"
                _save_crop(image, region.work_box, work_target)
                _save_crop(image, region.final_box, final_target)
                work_path = str(work_target.relative_to(settings.repo_root))
                final_path = str(final_target.relative_to(settings.repo_root))
                row_box = region.row_box
                work_box = region.work_box
                final_box = region.final_box
            work_text = _cleanup_math_ocr_text(str(raw_item.get("work_text", "") or ""))
            final_answer = _cleanup_math_ocr_text(str(raw_item.get("final_answer", "") or ""))
            recognized_answer = _cleanup_math_ocr_text(str(raw_item.get("recognized_answer", "") or "")) or final_answer or "unknown"
            uncertainty = [str(note) for note in raw_item.get("uncertainty", [])]
            notes = [str(note) for note in raw_item.get("notes", [])]
            uncertainty.extend(note for note in notes if note not in uncertainty)
            if not final_answer:
                uncertainty.append("final-answer-missing")
            items.append(
                OcrItem(
                    problem_no=problem_no,
                    recognized_answer=recognized_answer,
                    work_text=work_text or None,
                    final_answer=final_answer or None,
                    answer_source="final_answer" if final_answer else ("work_text" if work_text else "unknown"),
                    source_image_path=source_image_relpath,
                    work_image_path=work_path,
                    final_image_path=final_path,
                    raw_text=f"{problem_no} | work={work_text} | final={final_answer}",
                    uncertainty=uncertainty,
                )
            )
            mapping.append(
                {
                    "problem_no": problem_no,
                    "row_box": row_box,
                    "work_box": work_box,
                    "final_box": final_box,
                    "work_image_path": work_path,
                    "final_image_path": final_path,
                    "work_text": work_text,
                    "final_answer": final_answer,
                    "uncertainty": uncertainty,
                }
            )
        items.sort(key=lambda item: int(item.problem_no[1:]))
        document = NormalizedOcrDocument(
            student_id=student_id,
            source_image_id=source_image_id,
            source_image_paths=[source_image_relpath],
            page_type="worksheet",
            ocr_confidence_summary=_confidence_summary(items),
            items=items,
            test_id=str(read_payload.get("test_id") or layout_payload.get("test_id") or "") or None,
            source_alias="qa-verify-10k-jp",
        )
        raw_payload = {"layout": layout_payload, "read": read_payload}
        debug_payload = {
            "student_id": student_id,
            "source_image_id": source_image_id,
            "source_image_path": source_image_relpath,
            "mode": mode,
            "test_id": document.test_id,
            "timing_ms": {
                "layout_pass": round(layout_duration_ms, 1),
                "reading_pass": round(read_duration_ms, 1),
                "total_ocr": round((time.perf_counter() - started_total) * 1000, 1),
            },
            "layout": layout_payload,
            "mapping": mapping,
            "read": read_payload,
            "normalized": document.model_dump(),
        }
        return raw_payload, document, debug_payload

    started_read = time.perf_counter()
    worksheet_payload = await aoai_client.read_worksheet_image(
        image_bytes=image_bytes,
        mime_type=mime_type,
    )
    read_duration_ms = (time.perf_counter() - started_read) * 1000
    items: list[OcrItem] = []
    for raw_item in worksheet_payload.get("items", []):
        problem_no = str(raw_item.get("problem_no", "")).strip().upper()
        if not re.fullmatch(r"Q\d+", problem_no):
            continue
        recognized_answer = _cleanup_math_ocr_text(str(raw_item.get("recognized_answer", "") or "")) or "unknown"
        items.append(
            OcrItem(
                problem_no=problem_no,
                recognized_answer=recognized_answer,
                source_image_path=source_image_relpath,
                raw_text=str(raw_item.get("raw_text", "") or recognized_answer),
                uncertainty=[str(note) for note in raw_item.get("uncertainty", [])],
            )
        )
    items.sort(key=lambda item: int(item.problem_no[1:]))
    document = NormalizedOcrDocument(
        student_id=student_id,
        source_image_id=source_image_id,
        source_image_paths=[source_image_relpath],
        page_type="worksheet",
        ocr_confidence_summary=_confidence_summary(items),
        items=items,
        test_id=str(worksheet_payload.get("test_id") or "") or None,
        source_alias=None,
    )
    raw_payload = {"layout": layout_payload, "read": worksheet_payload}
    debug_payload = {
        "student_id": student_id,
        "source_image_id": source_image_id,
        "source_image_path": source_image_relpath,
        "mode": mode,
        "timing_ms": {
            "layout_pass": round(layout_duration_ms, 1),
            "reading_pass": round(read_duration_ms, 1),
            "total_ocr": round((time.perf_counter() - started_total) * 1000, 1),
        },
        "layout": layout_payload,
        "read": worksheet_payload,
        "normalized": document.model_dump(),
    }
    return raw_payload, document, debug_payload
