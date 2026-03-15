from __future__ import annotations

import json
from pathlib import Path

from app.services.ocr_normalizer import build_ocr_debug_artifact, normalize_ocr_result

DATA = Path(__file__).resolve().parents[2] / "data" / "raw_ocr"


def test_normalize_preserves_uncertainty_and_marks() -> None:
    raw = json.loads((DATA / "case-s03-signs.json").read_text())
    doc = normalize_ocr_result(raw, "s-03", "img-1")
    assert doc.ocr_confidence_summary.low_confidence_count == 2
    assert doc.items[1].teacher_marks == ["triangle"]
    assert "low-confidence" in doc.items[1].uncertainty
    assert doc.items[3].rewrite_detected is True


def test_normalize_uses_unknown_for_missing_answer() -> None:
    raw = {
        "analyzeResult": {
            "readResults": [{"lines": [{"text": "Q8", "confidence": 0.91}]}]
        }
    }
    doc = normalize_ocr_result(raw, "s-01", "img-2")
    assert doc.items[0].recognized_answer == "unknown"


def test_normalize_extracts_test_id_and_ignores_header_lines() -> None:
    raw = {
        "analyzeResult": {
            "readResults": [{"lines": [
                {"text": "TEST ID: ct-exhibit-main", "confidence": 0.99},
                {"text": "名前", "confidence": 0.95},
                {"text": "Q1 15", "confidence": 0.94}
            ]}]
        }
    }
    doc = normalize_ocr_result(raw, "s-03", "img-5")
    assert doc.test_id == "ct-exhibit-main"
    assert len(doc.items) == 1
    assert doc.items[0].problem_no == "Q1"


def test_confirmation_test_pairs_question_line_with_adjacent_answer_line() -> None:
    raw = {
        "analyzeResult": {
            "readResults": [{"lines": [
                {"text": "test_id: ct-exhibit-main", "boundingBox": [100, 0, 200, 0, 200, 10, 100, 10]},
                {"text": "Q1", "boundingBox": [10, 100, 30, 100, 30, 120, 10, 120]},
                {"text": "x+1=2", "boundingBox": [120, 100, 220, 100, 220, 120, 120, 120]},
                {"text": "2", "boundingBox": [320, 101, 360, 101, 360, 121, 320, 121]},
                {"text": "CT-EXHIBIT-MAIN-Q01 / Prealgebra / answer space for OCR", "boundingBox": [10, 140, 250, 140, 250, 152, 10, 152]},
                {"text": "Q2", "boundingBox": [10, 200, 30, 200, 30, 220, 10, 220]},
                {"text": "tan x = 1/x", "boundingBox": [120, 200, 240, 200, 240, 220, 120, 220]},
                {"text": "\\cot x", "boundingBox": [320, 201, 400, 201, 400, 221, 320, 221]},
            ]}]
        }
    }
    doc = normalize_ocr_result(raw, "s-03", "img-6")
    assert doc.test_id == "ct-exhibit-main"
    assert [item.problem_no for item in doc.items] == ["Q1", "Q2"]
    assert doc.items[0].recognized_answer == "2"
    assert doc.items[0].work_text == "x+1=2"
    assert doc.items[0].final_answer == "2"
    assert doc.items[1].recognized_answer == "\\cot x"
    assert doc.items[1].answer_source == "final_answer"


def test_build_debug_artifact_includes_confirmation_mapping() -> None:
    raw = {
        "analyzeResult": {
            "readResults": [{"lines": [
                {"text": "test_id: ct-exhibit-main", "boundingBox": [100, 0, 200, 0, 200, 10, 100, 10]},
                {"text": "Q1", "boundingBox": [10, 100, 30, 100, 30, 120, 10, 120]},
                {"text": "x+1=2", "boundingBox": [120, 100, 220, 100, 220, 120, 120, 120]},
                {"text": "2", "boundingBox": [320, 101, 360, 101, 360, 121, 320, 121]},
            ]}]
        }
    }
    artifact = build_ocr_debug_artifact(raw, "s-03", "img-7")
    assert artifact["test_id"] == "ct-exhibit-main"
    assert artifact["mapping"][0]["problem_no"] == "Q1"
    assert artifact["mapping"][0]["work_text"] == "x+1=2"
    assert artifact["mapping"][0]["final_answer"] == "2"
