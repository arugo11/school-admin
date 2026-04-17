from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.services.analysis import AnalysisService
from app.services.data_store import load_catalog, load_students
from app.services.ocr_normalizer import normalize_ocr_result

DATA = Path(__file__).resolve().parents[2] / "data" / "raw_ocr"


class FailingClient:
    async def analyze(self, system_prompt: str, user_payload: dict) -> dict:
        raise RuntimeError("skip-live-call")


def test_analysis_falls_back_and_stays_in_catalog() -> None:
    raw = json.loads((DATA / "case-s03-signs.json").read_text())
    normalized = normalize_ocr_result(raw, "s-03", "img-3")
    student = next(student for student in load_students() if student.student_id == "s-03")
    catalog = load_catalog()
    service = AnalysisService(client=FailingClient())
    result = asyncio.run(service.run(student, normalized, catalog))
    assert result.recommended_homework
    catalog_problem_nos = {item.problem_no for item in catalog}
    assert {rec.problem_no for rec in result.recommended_homework} <= catalog_problem_nos
    assert result.homework_load_fit in {"light", "appropriate", "heavy"}


def test_lighten_action_returns_small_set() -> None:
    raw = json.loads((DATA / "case-s02-steps.json").read_text())
    normalized = normalize_ocr_result(raw, "s-02", "img-4")
    student = next(student for student in load_students() if student.student_id == "s-02")
    catalog = load_catalog()
    service = AnalysisService(client=FailingClient())
    result = asyncio.run(service.run(student, normalized, catalog, action="lighten"))
    assert result.source_mode == "live"
    assert len(result.recommended_homework) <= 3
