from __future__ import annotations

import json
from pathlib import Path

from app.core.database import get_connection
from app.services.data_store import load_students
from app.services.student_summary import build_fallback_summary
from app.storage.repository import Repository


def main() -> None:
    repo = Repository()
    root = Path(__file__).resolve().parents[1]
    with get_connection() as conn:
        conn.execute("DELETE FROM student_state_snapshots")
        conn.execute("INSERT INTO rag_chunks_fts(rag_chunks_fts) VALUES('delete-all')")
        conn.execute("DELETE FROM rag_chunks")
        conn.execute("DELETE FROM student_documents")
        conn.execute("DELETE FROM student_metrics")
        conn.execute("DELETE FROM school_work_progress")
        conn.execute("DELETE FROM homework_history")
        conn.execute("DELETE FROM students")
    rows = json.loads((root / "data" / "students" / "students.json").read_text())
    repo.ensure_bootstrap(rows)
    for student in load_students():
        summary = build_fallback_summary(
            student=student,
            metrics=repo.list_student_metrics(student.student_id),
            retrieved_chunks=repo.search_rag_chunks(student.student_id, " ".join(student.weakness_history), limit=8),
            documents=repo.list_student_documents(student.student_id),
        )
        repo.save_student_summary(summary, generation_mode="reset-script")
        print(f"reset {student.student_id}")


if __name__ == "__main__":
    main()
