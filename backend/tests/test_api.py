from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import time

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.api import routes
from app.schemas import NormalizedOcrDocument, OcrConfidenceSummary, OcrItem

client = TestClient(app)


def test_students_endpoint_returns_six_students() -> None:
    response = client.get("/api/students")
    assert response.status_code == 200
    assert len(response.json()) >= 6


def test_upload_rejects_large_image() -> None:
    payload = BytesIO(b"0" * (5 * 1024 * 1024 + 1))
    response = client.post(
        "/api/uploads",
        data={"student_id": "s-03", "mode": "replay"},
        files={"file": ("large.png", payload, "image/png")},
    )
    assert response.status_code == 400


def test_replay_endpoint_returns_seeded_snapshot() -> None:
    response = client.get("/api/demo/s-03/replay")
    assert response.status_code == 200
    payload = response.json()
    assert payload["student_id"] == "s-03"
    assert payload["analysis"]["source_mode"] == "replay"


def test_replay_endpoint_returns_404_for_student_without_snapshot() -> None:
    response = client.get("/api/demo/s-01/replay")
    assert response.status_code == 404
    assert response.json()["detail"] == "Replay snapshot not found for this student"


def test_homework_approval_persists() -> None:
    response = client.post(
        "/api/homework/approve",
        json={
            "student_id": "s-03",
            "approved_problem_nos": ["A-02", "A-04"],
            "removed_problem_nos": ["A-07"],
            "approval_mode": "manual-test",
            "teacher_comment": "Keep it short",
            "approved_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 200
    assert response.json()["approved_problem_nos"] == ["A-02", "A-04"]


def test_analysis_run_replay_lighten() -> None:
    ocr_response = client.get("/api/demo/s-03/replay")
    normalized = ocr_response.json()["normalized_ocr"]
    response = client.post(
        "/api/analysis/run",
        json={
            "student_id": "s-03",
            "normalized_ocr": normalized,
            "mode": "replay",
            "action": "lighten",
        },
    )
    assert response.status_code == 200
    assert len(response.json()["recommended_homework"]) <= 3


def test_analysis_run_includes_problem_feedback_for_confirmation_test() -> None:
    ocr_response = client.post(
        "/api/ocr/normalize",
        json={
            "student_id": "s-03",
            "source_image_id": "img-confirm",
            "raw_ocr": {
                "analyzeResult": {
                    "readResults": [{
                        "lines": [
                            {"text": "TEST ID: ct-exhibit-main", "confidence": 0.99},
                            {"text": "Q1 2", "confidence": 0.98},
                            {"text": "Q2 wrong", "confidence": 0.98},
                        ]
                    }]
                }
            },
        },
    )
    normalized = ocr_response.json()
    response = client.post(
        "/api/analysis/run",
        json={
            "student_id": "s-03",
            "normalized_ocr": normalized,
            "mode": "live",
            "action": "initial",
        },
    )
    assert response.status_code == 200
    assert response.json()["problem_feedback"]


def test_ocr_normalize_pairs_confirmation_test_answer_lines_and_returns_debug_path() -> None:
    response = client.post(
        "/api/ocr/normalize",
        json={
            "student_id": "s-03",
            "source_image_id": "img-confirm-layout",
            "raw_ocr": {
                "analyzeResult": {
                    "readResults": [{
                        "lines": [
                            {"text": "TEST ID: ct-exhibit-main", "boundingBox": [100, 0, 200, 0, 200, 10, 100, 10]},
                            {"text": "Q1", "boundingBox": [10, 100, 30, 100, 30, 120, 10, 120]},
                            {"text": "x+1=2", "boundingBox": [120, 100, 220, 100, 220, 120, 120, 120]},
                            {"text": "2", "boundingBox": [320, 100, 360, 100, 360, 120, 320, 120]},
                            {"text": "CT-EXHIBIT-MAIN-Q01 / Prealgebra / answer space for OCR", "boundingBox": [10, 140, 250, 140, 250, 152, 10, 152]},
                            {"text": "Q2", "boundingBox": [10, 200, 30, 200, 30, 220, 10, 220]},
                            {"text": "tan x = 1/x", "boundingBox": [120, 200, 240, 200, 240, 220, 120, 220]},
                            {"text": "\\cot x", "boundingBox": [320, 200, 400, 200, 400, 220, 320, 220]},
                        ]
                    }]
                }
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["recognized_answer"] == "2"
    assert payload["items"][0]["work_text"] == "x+1=2"
    assert payload["items"][1]["recognized_answer"] == "\\cot x"
    assert payload["debug_artifact_path"].endswith("img-confirm-layout.json")


def test_problem_regrade_endpoint_updates_target_problem() -> None:
    ocr_response = client.post(
        "/api/ocr/normalize",
        json={
            "student_id": "s-03",
            "source_image_id": "img-confirm",
            "raw_ocr": {
                "analyzeResult": {
                    "readResults": [{
                        "lines": [
                            {"text": "TEST ID: ct-exhibit-main", "confidence": 0.99},
                            {"text": "Q1 wrong", "confidence": 0.98},
                        ]
                    }]
                }
            },
        },
    )
    normalized = ocr_response.json()
    analysis = client.post(
        "/api/analysis/run",
        json={
            "student_id": "s-03",
            "normalized_ocr": normalized,
            "mode": "live",
            "action": "initial",
        },
    ).json()
    response = client.post(
        "/api/analysis/regrade-problem",
        json={
            "student_id": "s-03",
            "normalized_ocr": normalized,
            "problem_no": "Q1",
            "student_note": "本当は 2 です",
            "mode": "live",
            "current_analysis": analysis,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["problem_feedback"]["problem_no"] == "Q1"
    assert payload["problem_feedback"]["regrade_requested"] is True


def test_problem_regrade_endpoint_rejects_invalid_problem() -> None:
    ocr_response = client.post(
        "/api/ocr/normalize",
        json={
            "student_id": "s-03",
            "source_image_id": "img-confirm",
            "raw_ocr": {
                "analyzeResult": {
                    "readResults": [{
                        "lines": [
                            {"text": "TEST ID: ct-exhibit-main", "confidence": 0.99},
                            {"text": "Q1 2", "confidence": 0.98},
                        ]
                    }]
                }
            },
        },
    )
    normalized = ocr_response.json()
    analysis = client.post(
        "/api/analysis/run",
        json={
            "student_id": "s-03",
            "normalized_ocr": normalized,
            "mode": "live",
            "action": "initial",
        },
    ).json()
    response = client.post(
        "/api/analysis/regrade-problem",
        json={
            "student_id": "s-03",
            "normalized_ocr": normalized,
            "problem_no": "Q99",
            "student_note": "違うと思います",
            "mode": "live",
            "current_analysis": analysis,
        },
    )
    assert response.status_code == 404


def test_ocr_run_merges_multiple_uploads(monkeypatch) -> None:
    first = client.post(
        "/api/uploads",
        data={"student_id": "s-03", "mode": "live"},
        files={"file": ("first.png", BytesIO(b"first"), "image/png")},
    ).json()
    second = client.post(
        "/api/uploads",
        data={"student_id": "s-03", "mode": "live"},
        files={"file": ("second.png", BytesIO(b"second"), "image/png")},
    ).json()

    calls: list[str] = []

    async def fake_extract_llm_ocr_document(**kwargs):
        calls.append(kwargs["image_path"].read_bytes().decode())
        index = len(calls)
        normalized = NormalizedOcrDocument(
            student_id="s-03",
            source_image_id=kwargs["source_image_id"],
            source_image_paths=[kwargs["source_image_relpath"]],
            page_type="worksheet",
            ocr_confidence_summary=OcrConfidenceSummary(low_confidence_count=0, notes=[]),
            items=[
                OcrItem(
                    problem_no=f"Q{index}",
                    recognized_answer=f"x={index}",
                    source_image_path=kwargs["source_image_relpath"],
                    raw_text=f"Q{index} x={index}",
                    uncertainty=[],
                )
            ],
            test_id="ct-exhibit-main",
            source_alias="qa-verify-10k-jp",
        )
        return (
            {"mode": "confirmation_test", "items": [{"problem_no": f"Q{index}"}]},
            normalized,
            {"mode": "confirmation_test", "normalized": normalized.model_dump()},
        )

    monkeypatch.setattr(routes, "extract_llm_ocr_document", fake_extract_llm_ocr_document)
    response = client.post(
        "/api/ocr/run",
        json={
            "student_id": "s-03",
            "source_image_ids": [first["source_image_id"], second["source_image_id"]],
            "mode": "live",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert calls == ["first", "second"]
    assert payload["normalized_ocr"]["test_id"] == "ct-exhibit-main"
    assert [item["problem_no"] for item in payload["normalized_ocr"]["items"]] == ["Q1", "Q2"]


def test_ocr_run_uses_llm_ocr_for_confirmation_test_image(monkeypatch) -> None:
    upload = client.post(
        "/api/uploads",
        data={"student_id": "s-03", "mode": "live"},
        files={"file": ("sheet.png", BytesIO(b"fake-image"), "image/png")},
    ).json()

    async def fake_extract_llm_ocr_document(**kwargs):
        normalized = NormalizedOcrDocument(
            student_id="s-03",
            source_image_id=kwargs["source_image_id"],
            source_image_paths=[kwargs["source_image_relpath"]],
            page_type="worksheet",
            ocr_confidence_summary=OcrConfidenceSummary(low_confidence_count=0, notes=[]),
            items=[
                OcrItem(
                    problem_no="Q1",
                    recognized_answer="2",
                    work_text="x+1=2",
                    final_answer="2",
                    answer_source="final_answer",
                    source_image_path=kwargs["source_image_relpath"],
                    work_image_path="data/ocr_debug/img-test_crops/q1-work.png",
                    final_image_path="data/ocr_debug/img-test_crops/q1-final.png",
                    raw_text="Q1 | work=x+1=2 | final=2",
                    uncertainty=[],
                )
            ],
            test_id="ct-exhibit-main",
            source_alias="qa-verify-10k-jp",
        )
        return (
            {"mode": "confirmation_test", "test_id": "ct-exhibit-main"},
            normalized,
            {"mode": "confirmation_test", "normalized": normalized.model_dump(), "mapping": [{"problem_no": "Q1"}]},
        )

    monkeypatch.setattr(routes, "extract_llm_ocr_document", fake_extract_llm_ocr_document)
    response = client.post(
        "/api/ocr/run",
        json={"student_id": "s-03", "source_image_id": upload["source_image_id"], "mode": "live"},
    )
    assert response.status_code == 200
    payload = response.json()["normalized_ocr"]
    assert payload["items"][0]["work_text"] == "x+1=2"
    assert payload["items"][0]["final_answer"] == "2"
    assert payload["items"][0]["final_image_path"].endswith("q1-final.png")


def test_ocr_run_returns_503_when_llm_ocr_is_rate_limited(monkeypatch) -> None:
    upload = client.post(
        "/api/uploads",
        data={"student_id": "s-03", "mode": "live"},
        files={"file": ("sheet.png", BytesIO(b"fake-image"), "image/png")},
    ).json()

    async def fake_extract_llm_ocr_document(**kwargs):
        request = httpx.Request("POST", "https://example.invalid")
        response = httpx.Response(429, request=request)
        raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    monkeypatch.setattr(routes, "extract_llm_ocr_document", fake_extract_llm_ocr_document)
    response = client.post(
        "/api/ocr/run",
        json={"student_id": "s-03", "source_image_id": upload["source_image_id"], "mode": "live"},
    )
    assert response.status_code == 503
    assert "temporarily busy" in response.json()["detail"]


def test_analysis_enqueue_creates_job_and_persists_test_report(monkeypatch) -> None:
    upload = client.post(
        "/api/uploads",
        data={"student_id": "s-03"},
        files={"file": ("sheet.png", BytesIO(b"fake-image"), "image/png")},
    ).json()

    async def fake_extract_llm_ocr_document(**kwargs):
        normalized = NormalizedOcrDocument(
            student_id="s-03",
            source_image_id=kwargs["source_image_id"],
            source_image_paths=[kwargs["source_image_relpath"]],
            page_type="worksheet",
            ocr_confidence_summary=OcrConfidenceSummary(low_confidence_count=1, notes=["Q1 の文字が薄い"]),
            items=[
                OcrItem(
                    problem_no="Q1",
                    recognized_answer="2",
                    source_image_path=kwargs["source_image_relpath"],
                    raw_text="Q1 2",
                    uncertainty=[],
                )
            ],
            test_id="ct-exhibit-main",
            source_alias="qa-verify-10k-jp",
        )
        return ({"mode": "confirmation_test"}, normalized, {"mode": "confirmation_test"})

    async def fake_run(*_args, **_kwargs):
        return routes.AnalysisResult.model_validate(
            {
                "weak_units": ["式・因数分解"],
                "error_patterns": ["符号ミスが散見"],
                "homework_load_fit": "appropriate",
                "analysis_rationale": ["確認テストの誤答を反映"],
                "recommended_homework": [{"problem_no": "A-01", "reason": "復習", "difficulty": "basic"}],
                "teacher_note": "短い復習を推奨",
                "fallback_used": False,
                "source_mode": "live",
                "problem_feedback": [],
            }
        )

    async def fake_refresh_summary_async(*_args, **_kwargs):
        return {"status": "ok"}

    monkeypatch.setattr(routes, "extract_llm_ocr_document", fake_extract_llm_ocr_document)
    monkeypatch.setattr(routes.analysis_service, "run", fake_run)
    monkeypatch.setattr(routes, "_refresh_summary_async", fake_refresh_summary_async)

    queued = client.post(
        "/api/analysis/enqueue",
        json={"student_id": "s-03", "source_image_id": upload["source_image_id"]},
    )
    assert queued.status_code == 200
    job_id = queued.json()["job_id"]
    assert queued.json()["status"] == "queued"

    latest = None
    for _ in range(60):
        latest = client.get(f"/api/analysis/jobs/{job_id}")
        assert latest.status_code == 200
        if latest.json()["status"] in {"succeeded", "failed"}:
            break
        time.sleep(0.1)
    assert latest is not None
    assert latest.json()["status"] == "succeeded"
    assert latest.json()["result_document_id"] is not None

    documents = client.get("/api/students/s-03/documents").json()
    test_report = next(item for item in documents if item["document_id"] == latest.json()["result_document_id"])
    assert test_report["document_type"] == "test_report"
    assert test_report["asset_paths"]
    assert test_report["payload"]["normalized_ocr"]["student_id"] == "s-03"
    assert test_report["payload"]["analysis"]["weak_units"]


def test_analysis_enqueue_marks_failed_when_background_job_errors(monkeypatch) -> None:
    upload = client.post(
        "/api/uploads",
        data={"student_id": "s-03"},
        files={"file": ("sheet.png", BytesIO(b"fake-image"), "image/png")},
    ).json()

    async def fake_extract_llm_ocr_document(**_kwargs):
        raise RuntimeError("simulated background failure")

    monkeypatch.setattr(routes, "extract_llm_ocr_document", fake_extract_llm_ocr_document)

    queued = client.post(
        "/api/analysis/enqueue",
        json={"student_id": "s-03", "source_image_id": upload["source_image_id"]},
    )
    assert queued.status_code == 200
    job_id = queued.json()["job_id"]

    latest = None
    for _ in range(30):
        latest = client.get(f"/api/analysis/jobs/{job_id}")
        assert latest.status_code == 200
        if latest.json()["status"] in {"succeeded", "failed"}:
            break
        time.sleep(0.1)
    assert latest is not None
    assert latest.json()["status"] == "failed"
    assert "simulated background failure" in latest.json()["error_detail"]
