from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

from app.core.config import settings
from app.schemas import AnalysisResult, HomeworkRecommendation
from app.services.analysis import AnalysisService
from app.services.data_store import load_catalog, load_students
from app.services.ocr_normalizer import normalize_ocr_result

DATA = Path(__file__).resolve().parents[2] / "data" / "raw_ocr"


def test_analysis_falls_back_and_stays_in_catalog() -> None:
    raw = json.loads((DATA / "case-s03-signs.json").read_text())
    normalized = normalize_ocr_result(raw, "s-03", "img-3")
    student = next(student for student in load_students() if student.student_id == "s-03")
    catalog = load_catalog()
    service = AnalysisService()
    result = asyncio.run(service.run(student, normalized, catalog, mode="live"))
    assert result.recommended_homework
    catalog_problem_nos = {item.problem_no for item in catalog}
    assert {rec.problem_no for rec in result.recommended_homework} <= catalog_problem_nos
    assert result.homework_load_fit in {"light", "appropriate", "heavy"}


def test_replay_mode_uses_deterministic_result() -> None:
    raw = json.loads((DATA / "case-s02-steps.json").read_text())
    normalized = normalize_ocr_result(raw, "s-02", "img-4")
    student = next(student for student in load_students() if student.student_id == "s-02")
    catalog = load_catalog()
    service = AnalysisService()
    result = asyncio.run(service.run(student, normalized, catalog, mode="replay", action="lighten"))
    assert result.source_mode == "replay"
    assert len(result.recommended_homework) <= 3


def test_live_analysis_payload_includes_problem_feedback_seed() -> None:
    raw = {
        "analyzeResult": {
            "readResults": [{
                "lines": [
                    {"text": "TEST ID: ct-exhibit-main", "confidence": 0.99},
                    {"text": "Q1 2", "confidence": 0.98},
                    {"text": "Q2 wrong", "confidence": 0.98},
                ]
            }]
        }
    }
    normalized = normalize_ocr_result(raw, "s-03", "img-confirm")
    student = next(student for student in load_students() if student.student_id == "s-03")
    catalog = load_catalog()
    client = AsyncMock()
    client.analyze.return_value = AnalysisResult(
        weak_units=["一次方程式"],
        error_patterns=["Q2 で模範解答との差があった"],
        homework_load_fit="appropriate",
        analysis_rationale=["Q2 の最終解答が模範解答と一致しなかった"],
        recommended_homework=[HomeworkRecommendation(problem_no=catalog[0].problem_no, reason="復習", difficulty=catalog[0].difficulty)],
        teacher_note="誤答理由を口頭で確認してから短く復習する。",
        fallback_used=False,
        source_mode="live",
    )
    service = AnalysisService(client=client)
    previous = settings.azure_analysis_live_enabled
    settings.azure_analysis_live_enabled = True
    try:
        result = asyncio.run(service.run(student, normalized, catalog, mode="live"))
    finally:
        settings.azure_analysis_live_enabled = previous

    assert result.problem_feedback
    client.analyze.assert_awaited_once()
    _, payload = client.analyze.await_args.args
    assert payload["problem_feedback_seed"]
    assert payload["problem_feedback_seed"][0]["problem_no"] == "Q1"
    assert "confirmation_test_context" in payload
