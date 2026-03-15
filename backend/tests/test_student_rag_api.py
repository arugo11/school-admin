from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_students_overview_returns_six_students_with_summary_fields() -> None:
    response = client.get("/api/students/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_students"] == 6
    assert len(payload["students"]) == 6
    assert all(item["one_line_analysis"] for item in payload["students"])
    assert all("recommended_action" in item for item in payload["students"])


def test_student_summary_always_returns_three_cited_titles() -> None:
    response = client.get("/api/students/s-03/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["student_id"] == "s-03"
    assert len(payload["cited_document_titles"]) == 3
    assert payload["current_status"]
    assert payload["risk_signals"]
    assert payload["next_best_actions"]


def test_student_documents_are_scoped_per_student() -> None:
    s03_response = client.get("/api/students/s-03/documents")
    s02_response = client.get("/api/students/s-02/documents")
    assert s03_response.status_code == 200
    assert s02_response.status_code == 200
    s03_titles = {item["title"] for item in s03_response.json()}
    s02_titles = {item["title"] for item in s02_response.json()}
    assert "2026-03-13 面談メモ" in s03_titles
    assert "2026-03-13 面談メモ" not in s02_titles


def test_post_document_refreshes_summary_and_document_list() -> None:
    response = client.post(
        "/api/students/s-03/documents",
        json={
            "document_type": "teacher_note",
            "title": "2026-03-16 講師追記",
            "body_text": "今日の授業では, 符号ミスの原因説明が少し改善した.",
            "source_system": "manual",
            "authored_by": "teacher",
            "document_date": "2026-03-16T12:00:00+00:00",
        },
    )
    assert response.status_code == 200
    summary_response = client.get("/api/students/s-03/summary")
    assert summary_response.status_code == 200
    titles = client.get("/api/students/s-03/documents").json()
    assert any(item["title"] == "2026-03-16 講師追記" for item in titles)


def test_rag_recommend_returns_problem_groups_with_citations() -> None:
    replay = client.get("/api/demo/s-03/replay").json()
    response = client.post(
        "/api/homework/rag-recommend",
        json={
            "student_id": "s-03",
            "normalized_ocr": replay["normalized_ocr"],
            "analysis": replay["analysis"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["student_id"] == "s-03"
    assert payload["recommended_problem_groups"]
    first = payload["recommended_problem_groups"][0]
    assert "group_id" in first
    assert len(first["cited_document_titles"]) == 3

