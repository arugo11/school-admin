from __future__ import annotations

from app.services.data_store import load_students
from app.services.student_summary import build_fallback_summary
from app.storage.repository import Repository


def main() -> None:
    repo = Repository()
    for student in load_students():
        summary = build_fallback_summary(
            student,
            repo.list_student_metrics(student.student_id),
            repo.search_rag_chunks(student.student_id, " ".join(student.weakness_history), limit=8),
            repo.list_student_documents(student.student_id),
        )
        repo.save_student_summary(summary, generation_mode="daily-script")
        print(f"refreshed {student.student_id}")


if __name__ == "__main__":
    main()
