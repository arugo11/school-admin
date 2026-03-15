from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.schemas import NormalizedOcrDocument, OcrConfidenceSummary, OcrItem

PROBLEM_RE = re.compile(r"^(?:Q|問|No\.)\s*(\d+)(?:[\s:：-]+(.*))?$", re.IGNORECASE)
TEST_ID_RE = re.compile(r"^(?:test[_\s-]*id)\s*[:：]\s*([a-zA-Z0-9-]+)", re.IGNORECASE)
MARK_CIRCLE = ("○", "◯", "⭕", "circle")
MARK_TRIANGLE = ("△", "▲", "triangle")
MARK_CROSS = ("×", "✕", "cross")
HELP_LINE_HINTS = (
    "answer space for ocr",
    "manifest",
    "page ",
    "ocr向け",
    "大きく",
    "1行1問",
    "解答用紙",
    "名前",
    "学年",
    "メモ",
    "計算過程",
    "最終解答",
)


@dataclass
class ParsedLine:
    problem_no: str
    answer: str
    work_text: str | None
    final_answer: str | None
    answer_source: str
    marks: list[str]
    rewrite_detected: bool
    scratch_notes: str
    raw_text: str
    uncertainty: list[str]
    confidence: float


@dataclass
class OcrLine:
    text: str
    confidence: float
    bounding_box: list[float]
    center_x: float
    center_y: float
    left: float
    right: float
    top: float
    bottom: float


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


def _to_ocr_line(line: dict[str, Any]) -> OcrLine:
    text = str(line.get("text", "")).strip()
    confidence = float(line.get("confidence", 0.9) or 0.9)
    bbox = line.get("boundingBox") or line.get("polygon") or []
    coords = [float(value) for value in bbox] if bbox else []
    if len(coords) >= 8:
        xs = coords[0::2]
        ys = coords[1::2]
        left = min(xs)
        right = max(xs)
        top = min(ys)
        bottom = max(ys)
    else:
        left = right = top = bottom = 0.0
    return OcrLine(
        text=text,
        confidence=confidence,
        bounding_box=coords,
        center_x=(left + right) / 2,
        center_y=(top + bottom) / 2,
        left=left,
        right=right,
        top=top,
        bottom=bottom,
    )


def _detect_marks(text: str) -> list[str]:
    marks: list[str] = []
    lowered = text.lower()
    if any(marker in text or marker in lowered for marker in MARK_CIRCLE):
        marks.append("circle")
    if any(marker in text or marker in lowered for marker in MARK_TRIANGLE):
        marks.append("triangle")
    if any(marker in text or marker in lowered for marker in MARK_CROSS):
        marks.append("cross")
    return marks


def _build_uncertainty(text: str, confidence: float) -> list[str]:
    uncertainty: list[str] = []
    if confidence < 0.7:
        uncertainty.append("low-confidence")
    if "?" in text:
        uncertainty.append("ambiguous-character")
    if "->" in text or "→" in text:
        uncertainty.append("rewrite-heuristic")
    if not re.search(r"\d|x|y|=|[a-z]", text, re.IGNORECASE):
        uncertainty.append("answer-missing")
    return uncertainty


def _scratch_notes(text: str, marks: list[str], rewrite_detected: bool, uncertainty: list[str]) -> str:
    notes: list[str] = []
    if "triangle" in marks:
        notes.append("teacher likely marked partial understanding")
    if "cross" in marks:
        notes.append("teacher likely marked incorrect")
    if rewrite_detected:
        notes.append("possible rewrite trace")
    if "low-confidence" in uncertainty:
        notes.append("OCR confidence is low")
    return "; ".join(notes)


def _is_help_line(text: str) -> bool:
    lowered = text.lower().strip()
    if not lowered:
        return True
    if TEST_ID_RE.match(lowered):
        return True
    if lowered.startswith("ct-") and "answer space for ocr" in lowered:
        return True
    return any(hint in lowered for hint in HELP_LINE_HINTS)


def parse_line(text: str, confidence: float) -> ParsedLine | None:
    stripped = text.strip()
    if not stripped or TEST_ID_RE.match(stripped):
        return None
    match = PROBLEM_RE.match(stripped)
    if not match:
        return None
    problem_no = f"Q{match.group(1)}"
    remainder = (match.group(2) or "").strip()
    rewrite_detected = "->" in stripped or "→" in stripped or stripped.count("=") > 1
    marks = _detect_marks(stripped)
    uncertainty = _build_uncertainty(stripped, confidence)
    answer = remainder or "unknown"
    return ParsedLine(
        problem_no=problem_no,
        answer=answer,
        work_text=remainder or None,
        final_answer=remainder or None,
        answer_source="work_text" if remainder else "unknown",
        marks=marks,
        rewrite_detected=rewrite_detected,
        scratch_notes=_scratch_notes(stripped, marks, rewrite_detected, uncertainty),
        raw_text=stripped,
        uncertainty=uncertainty,
        confidence=confidence,
    )


def _collect_test_id(lines: list[OcrLine]) -> str | None:
    for line in lines:
        test_match = TEST_ID_RE.match(line.text.strip())
        if test_match:
            return test_match.group(1)
    return None


def _join_line_text(lines: list[OcrLine]) -> str | None:
    if not lines:
        return None
    return " ".join(line.text.strip() for line in sorted(lines, key=lambda item: (item.left, item.center_x)) if line.text.strip()).strip() or None


def _parse_confirmation_test_lines(lines: list[OcrLine]) -> tuple[list[ParsedLine], list[dict[str, Any]]]:
    labels = [(index, line) for index, line in enumerate(lines) if PROBLEM_RE.match(line.text)]
    if not labels:
        return [], []
    all_right = [line.right for _, line in labels if line.right]
    label_edge = max(all_right) if all_right else 60.0
    all_x = [line.center_x for line in lines if line.center_x > 0]
    page_right = max(all_x) if all_x else 1000.0
    final_boundary = label_edge + (page_right - label_edge) * 0.72

    parsed: list[ParsedLine] = []
    debug_pairs: list[dict[str, Any]] = []

    for position, (index, line) in enumerate(labels):
        match = PROBLEM_RE.match(line.text)
        if not match:
            continue
        problem_no = f"Q{match.group(1)}"
        next_label_y = labels[position + 1][1].center_y if position + 1 < len(labels) else float("inf")
        row_candidates = [
            candidate
            for candidate_index, candidate in enumerate(lines)
            if candidate_index != index
            and candidate.center_y >= line.top - 10
            and candidate.center_y < next_label_y - 10
            and not PROBLEM_RE.match(candidate.text)
            and not _is_help_line(candidate.text)
        ]

        work_lines = [candidate for candidate in row_candidates if candidate.center_x < final_boundary and candidate.left > label_edge + 8]
        final_lines = [candidate for candidate in row_candidates if candidate.center_x >= final_boundary]

        inline_answer = (match.group(2) or "").strip()
        work_text = _join_line_text(work_lines)
        final_answer = _join_line_text(final_lines) or (inline_answer or None)
        recognized_answer = final_answer or "unknown"
        answer_source = "final_answer" if final_answer else "unknown"

        raw_chunks = [line.text]
        if work_text:
            raw_chunks.append(f"work={work_text}")
        if final_answer:
            raw_chunks.append(f"final={final_answer}")
        raw_text = " | ".join(raw_chunks)
        confidence_pool = [line.confidence] + [candidate.confidence for candidate in work_lines + final_lines]
        confidence = min(confidence_pool) if confidence_pool else line.confidence
        uncertainty = _build_uncertainty(recognized_answer, confidence)
        if work_text and not final_answer and "final-answer-missing" not in uncertainty:
            uncertainty.append("final-answer-missing")
        if work_text and final_answer and work_text != final_answer:
            uncertainty.append("work-final-mismatch")
        rewrite_detected = any(marker in raw_text for marker in ("->", "→")) or raw_text.count("=") > 1
        marks = _detect_marks(raw_text)
        parsed.append(
            ParsedLine(
                problem_no=problem_no,
                answer=recognized_answer,
                work_text=work_text,
                final_answer=final_answer,
                answer_source=answer_source,
                marks=marks,
                rewrite_detected=rewrite_detected,
                scratch_notes=_scratch_notes(raw_text, marks, rewrite_detected, uncertainty),
                raw_text=raw_text,
                uncertainty=uncertainty,
                confidence=confidence,
            )
        )
        debug_pairs.append(
            {
                "problem_no": problem_no,
                "label": line.text,
                "label_y": line.center_y,
                "work_text": work_text,
                "final_answer": final_answer,
                "answer_source": answer_source,
                "strategy": "row-bucket-template-aware",
                "final_boundary": final_boundary,
                "work_candidates": [candidate.text for candidate in work_lines],
                "final_candidates": [candidate.text for candidate in final_lines],
            }
        )
    return parsed, debug_pairs


def _normalize_with_debug(raw_ocr: dict, student_id: str, source_image_id: str) -> tuple[NormalizedOcrDocument, dict[str, Any]]:
    ocr_lines = [_to_ocr_line(line) for line in _extract_lines(raw_ocr)]
    test_id = _collect_test_id(ocr_lines)
    notes: list[str] = []
    parsed: list[ParsedLine] = []
    debug_pairs: list[dict[str, Any]] = []

    if test_id:
        parsed, debug_pairs = _parse_confirmation_test_lines(ocr_lines)
    else:
        for line in ocr_lines:
            parsed_line = parse_line(line.text, line.confidence)
            if not parsed_line:
                continue
            parsed.append(parsed_line)

    for parsed_line in parsed:
        if parsed_line.uncertainty:
            notes.append(f"{parsed_line.problem_no}: {', '.join(parsed_line.uncertainty)}")

    items = [
        OcrItem(
            problem_no=item.problem_no,
            recognized_answer=item.answer,
            work_text=item.work_text,
            final_answer=item.final_answer,
            answer_source=item.answer_source,
            teacher_marks=item.marks,
            rewrite_detected=item.rewrite_detected,
            scratch_notes=item.scratch_notes,
            raw_text=item.raw_text,
            uncertainty=item.uncertainty,
        )
        for item in parsed
    ]
    document = NormalizedOcrDocument(
        student_id=student_id,
        source_image_id=source_image_id,
        page_type="worksheet",
        ocr_confidence_summary=OcrConfidenceSummary(
            low_confidence_count=sum(1 for item in parsed if item.confidence < 0.7),
            notes=notes,
        ),
        items=items,
        test_id=test_id,
        source_alias="qa-verify-10k-jp" if test_id else None,
    )
    debug_payload = {
        "student_id": student_id,
        "source_image_id": source_image_id,
        "test_id": test_id,
        "raw_lines": [
            {
                "text": line.text,
                "confidence": line.confidence,
                "bounding_box": line.bounding_box,
                "center_x": line.center_x,
                "center_y": line.center_y,
            }
            for line in ocr_lines
        ],
        "mapping": debug_pairs,
        "normalized": document.model_dump(),
    }
    return document, debug_payload


def normalize_ocr_result(raw_ocr: dict, student_id: str, source_image_id: str) -> NormalizedOcrDocument:
    document, _ = _normalize_with_debug(raw_ocr, student_id, source_image_id)
    return document


def build_ocr_debug_artifact(raw_ocr: dict, student_id: str, source_image_id: str) -> dict[str, Any]:
    _, debug_payload = _normalize_with_debug(raw_ocr, student_id, source_image_id)
    return debug_payload


def persist_ocr_debug_artifact(source_image_id: str, payload: dict[str, Any]) -> Path:
    target = settings.ocr_debug_dir / f"{source_image_id}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
