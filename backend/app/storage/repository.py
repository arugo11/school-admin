from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.database import get_connection
from app.schemas import (
    HomeworkApproval,
    ProcessingJob,
    RagChunkSearchResult,
    SchoolWorkProgressItem,
    SchoolWorkProgressUpdateRequest,
    SummarySourceRanking,
    StudentDocumentCreateRequest,
    StudentDocumentResponse,
    StudentHomeworkHistoryItem,
    StudentMetric,
    StudentOverviewItem,
    StudentProfile,
    StudentStateSummary,
    UploadResponse,
)
from app.services.rag import build_embedding, chunk_document, cosine_similarity, deserialize_embedding, recency_boost, serialize_embedding
from app.services.student_seed import build_seed_documents, build_seed_homework, build_seed_metrics


class Repository:
    def ensure_bootstrap(self, student_rows: list[dict[str, Any]]) -> None:
        with get_connection() as conn:
            existing = conn.execute("SELECT COUNT(*) AS count FROM students").fetchone()["count"]
            if existing:
                for row in student_rows:
                    conn.execute(
                        """
                        UPDATE students
                        SET class_name = ?,
                            school_name = CASE WHEN school_name = '' THEN ? ELSE school_name END,
                            next_regular_exam_date = COALESCE(next_regular_exam_date, ?),
                            updated_at = ?
                        WHERE student_id = ?
                        """,
                        (
                            row.get("class_name", ""),
                            row.get("school_name", ""),
                            row.get("next_regular_exam_date"),
                            datetime.now(timezone.utc).isoformat(),
                            row["student_id"],
                        ),
                    )
                    progress_count = conn.execute(
                        "SELECT COUNT(*) AS count FROM school_work_progress WHERE student_id = ?",
                        (row["student_id"],),
                    ).fetchone()["count"]
                    if progress_count == 0:
                        for progress in row.get("school_work_progress", []):
                            conn.execute(
                                """
                                INSERT INTO school_work_progress (
                                    student_id, subject_name, workbook_name, completion_rate,
                                    completed_pages, target_pages, note, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    row["student_id"],
                                    progress["subject_name"],
                                    progress["workbook_name"],
                                    progress["completion_rate"],
                                    progress["completed_pages"],
                                    progress["target_pages"],
                                    progress.get("note", ""),
                                    progress.get("updated_at", datetime.now(timezone.utc).isoformat()),
                                ),
                            )
                return
            now = datetime.now(timezone.utc).isoformat()
            for row in student_rows:
                conn.execute(
                    """
                    INSERT INTO students (
                        student_id, display_name, grade, class_name, school_name, next_regular_exam_date, target_level, persona_summary,
                        recent_scores, homework_style_notes, weakness_history,
                        preferred_difficulty, attention_level, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["student_id"],
                        row["display_name"],
                        row["grade"],
                        row.get("class_name", ""),
                        row.get("school_name", ""),
                        row.get("next_regular_exam_date"),
                        row["target_level"],
                        row["persona_summary"],
                        json.dumps(row["recent_scores"], ensure_ascii=False),
                        row["homework_style_notes"],
                        json.dumps(row["weakness_history"], ensure_ascii=False),
                        row["preferred_difficulty"],
                        row["attention_level"],
                        now,
                        now,
                    ),
                )
                for progress in row.get("school_work_progress", []):
                    conn.execute(
                        """
                        INSERT INTO school_work_progress (
                            student_id, subject_name, workbook_name, completion_rate,
                            completed_pages, target_pages, note, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["student_id"],
                            progress["subject_name"],
                            progress["workbook_name"],
                            progress["completion_rate"],
                            progress["completed_pages"],
                            progress["target_pages"],
                            progress.get("note", ""),
                            progress.get("updated_at", now),
                        ),
                    )
                for metric in build_seed_metrics(row["student_id"]):
                    conn.execute(
                        """
                        INSERT INTO student_metrics (student_id, metric_type, metric_value, metric_date, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            metric["student_id"],
                            metric["metric_type"],
                            metric["metric_value"],
                            metric["metric_date"],
                            now,
                        ),
                    )
                for item in build_seed_homework(row["student_id"]):
                    conn.execute(
                        """
                        INSERT INTO homework_history (student_id, assigned_date, approved_problem_groups, expected_load, completion_status, teacher_comment, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item["student_id"],
                            item["assigned_date"],
                            item["approved_problem_groups"],
                            item["expected_load"],
                            item["completion_status"],
                            item["teacher_comment"],
                            item["created_at"],
                        ),
                    )
                for document in build_seed_documents(row["student_id"]):
                    created = conn.execute(
                        """
                        INSERT INTO student_documents (
                            student_id, document_type, title, body_text, source_system, authored_by, document_date,
                            asset_paths_json, payload_json, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            document["student_id"],
                            document["document_type"],
                            document["title"],
                            document["body_text"],
                            document["source_system"],
                            document["authored_by"],
                            document["document_date"],
                            json.dumps(document.get("asset_paths", []), ensure_ascii=False),
                            json.dumps(document.get("payload"), ensure_ascii=False) if document.get("payload") is not None else None,
                            now,
                            now,
                        ),
                    )
                    self._index_document(conn, created.lastrowid, row["student_id"], document["document_type"], document["title"], document["body_text"], document["document_date"])

    def save_upload(self, student_id: str, upload: UploadResponse) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO uploads (source_image_id, student_id, filename, stored_path, source_mode, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    upload.source_image_id,
                    student_id,
                    upload.filename,
                    upload.stored_path,
                    upload.source_mode,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_students(self) -> list[StudentProfile]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.*,
                       (
                           SELECT metric_value FROM student_metrics
                           WHERE student_id = s.student_id AND metric_type = 'homework_completion_rate'
                           ORDER BY metric_date DESC LIMIT 1
                       ) AS homework_completion_rate,
                       (
                           SELECT generated_at FROM student_state_snapshots
                           WHERE student_id = s.student_id
                           ORDER BY generated_at DESC LIMIT 1
                       ) AS latest_summary_generated_at,
                       (
                           SELECT one_line_analysis FROM student_state_snapshots
                           WHERE student_id = s.student_id
                           ORDER BY generated_at DESC LIMIT 1
                       ) AS one_line_analysis,
                       (
                           SELECT recommended_action FROM student_state_snapshots
                           WHERE student_id = s.student_id
                           ORDER BY generated_at DESC LIMIT 1
                       ) AS recommended_action
                FROM students s
                ORDER BY s.student_id
                """
            ).fetchall()
        return [self._row_to_student(row) for row in rows]

    def get_student(self, student_id: str) -> StudentProfile | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT s.*,
                       (
                           SELECT metric_value FROM student_metrics
                           WHERE student_id = s.student_id AND metric_type = 'homework_completion_rate'
                           ORDER BY metric_date DESC LIMIT 1
                       ) AS homework_completion_rate,
                       (
                           SELECT generated_at FROM student_state_snapshots
                           WHERE student_id = s.student_id
                           ORDER BY generated_at DESC LIMIT 1
                       ) AS latest_summary_generated_at,
                       (
                           SELECT one_line_analysis FROM student_state_snapshots
                           WHERE student_id = s.student_id
                           ORDER BY generated_at DESC LIMIT 1
                       ) AS one_line_analysis,
                       (
                           SELECT recommended_action FROM student_state_snapshots
                           WHERE student_id = s.student_id
                           ORDER BY generated_at DESC LIMIT 1
                       ) AS recommended_action
                FROM students s
                WHERE s.student_id = ?
                """,
                (student_id,),
            ).fetchone()
        return self._row_to_student(row) if row else None

    def list_student_metrics(self, student_id: str) -> list[StudentMetric]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT metric_type, metric_value, metric_date FROM student_metrics WHERE student_id = ? ORDER BY metric_date DESC",
                (student_id,),
            ).fetchall()
        return [StudentMetric(metric_type=row["metric_type"], metric_value=row["metric_value"], metric_date=row["metric_date"]) for row in rows]

    def list_student_documents(self, student_id: str) -> list[StudentDocumentResponse]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM student_documents
                WHERE student_id = ?
                ORDER BY document_date DESC, document_id DESC
                """,
                (student_id,),
            ).fetchall()
        return [self._row_to_document(row) for row in rows]

    def add_student_document(self, student_id: str, payload: StudentDocumentCreateRequest) -> StudentDocumentResponse:
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO student_documents (
                    student_id, document_type, title, body_text, source_system, authored_by, document_date,
                    asset_paths_json, payload_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_id,
                    payload.document_type,
                    payload.title,
                    payload.body_text,
                    payload.source_system,
                    payload.authored_by,
                    payload.document_date.isoformat(),
                    json.dumps(payload.asset_paths, ensure_ascii=False),
                    json.dumps(payload.payload, ensure_ascii=False) if payload.payload is not None else None,
                    now,
                    now,
                ),
            )
            self._index_document(conn, cursor.lastrowid, student_id, payload.document_type, payload.title, payload.body_text, payload.document_date.isoformat())
            row = conn.execute("SELECT * FROM student_documents WHERE document_id = ?", (cursor.lastrowid,)).fetchone()
        return self._row_to_document(row)

    def get_student_document(self, student_id: str, document_id: int) -> StudentDocumentResponse | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM student_documents
                WHERE student_id = ? AND document_id = ?
                """,
                (student_id, document_id),
            ).fetchone()
        if not row:
            return None
        return self._row_to_document(row)

    def create_processing_job(self, job: ProcessingJob) -> ProcessingJob:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO processing_jobs (
                    job_id, student_id, source_image_ids_json, status, job_type, current_stage,
                    progress_message, notification_message, error_detail,
                    result_document_id, created_at, started_at, finished_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.student_id,
                    json.dumps(job.source_image_ids, ensure_ascii=False),
                    job.status,
                    job.job_type,
                    job.current_stage,
                    job.progress_message,
                    job.notification_message,
                    job.error_detail,
                    job.result_document_id,
                    job.created_at.isoformat(),
                    job.started_at.isoformat() if job.started_at else None,
                    job.finished_at.isoformat() if job.finished_at else None,
                ),
            )
        return job

    def get_processing_job(self, job_id: str) -> ProcessingJob | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM processing_jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return self._row_to_processing_job(row)

    def list_processing_jobs(self, student_id: str, *, scope: str = "recent", limit: int = 10) -> list[ProcessingJob]:
        with get_connection() as conn:
            if scope == "active":
                rows = conn.execute(
                    """
                    SELECT * FROM processing_jobs
                    WHERE student_id = ? AND status IN ('queued', 'running')
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (student_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM processing_jobs
                    WHERE student_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (student_id, limit),
                ).fetchall()
        return [self._row_to_processing_job(row) for row in rows]

    def update_processing_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        current_stage: str | None = None,
        progress_message: str | None = None,
        notification_message: str | None = None,
        error_detail: str | None = None,
        result_document_id: int | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
    ) -> ProcessingJob | None:
        assignments: list[str] = []
        params: list[Any] = []
        if status is not None:
            assignments.append("status = ?")
            params.append(status)
        if current_stage is not None:
            assignments.append("current_stage = ?")
            params.append(current_stage)
        if progress_message is not None:
            assignments.append("progress_message = ?")
            params.append(progress_message)
        if notification_message is not None:
            assignments.append("notification_message = ?")
            params.append(notification_message)
        if error_detail is not None:
            assignments.append("error_detail = ?")
            params.append(error_detail)
        if result_document_id is not None:
            assignments.append("result_document_id = ?")
            params.append(result_document_id)
        if started_at is not None:
            assignments.append("started_at = ?")
            params.append(started_at)
        if finished_at is not None:
            assignments.append("finished_at = ?")
            params.append(finished_at)
        if not assignments:
            return self.get_processing_job(job_id)
        params.append(job_id)
        with get_connection() as conn:
            conn.execute(f"UPDATE processing_jobs SET {', '.join(assignments)} WHERE job_id = ?", params)
            row = conn.execute("SELECT * FROM processing_jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return self._row_to_processing_job(row)

    def list_homework_history(self, student_id: str) -> list[StudentHomeworkHistoryItem]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM homework_history WHERE student_id = ? ORDER BY assigned_date DESC, homework_id DESC",
                (student_id,),
            ).fetchall()
        return [
            StudentHomeworkHistoryItem(
                homework_id=row["homework_id"],
                student_id=row["student_id"],
                assigned_date=row["assigned_date"],
                approved_problem_groups=json.loads(row["approved_problem_groups"]),
                expected_load=row["expected_load"],
                completion_status=row["completion_status"],
                teacher_comment=row["teacher_comment"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def list_school_work_progress(self, student_id: str) -> list[SchoolWorkProgressItem]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM school_work_progress
                WHERE student_id = ?
                ORDER BY subject_name, progress_id
                """,
                (student_id,),
            ).fetchall()
        return [
            SchoolWorkProgressItem(
                progress_id=row["progress_id"],
                student_id=row["student_id"],
                subject_name=row["subject_name"],
                workbook_name=row["workbook_name"],
                completion_rate=row["completion_rate"],
                completed_pages=row["completed_pages"],
                target_pages=row["target_pages"],
                note=row["note"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def upsert_school_work_progress(self, student_id: str, payload: SchoolWorkProgressUpdateRequest) -> SchoolWorkProgressItem:
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            existing = conn.execute(
                """
                SELECT progress_id FROM school_work_progress
                WHERE student_id = ? AND subject_name = ? AND workbook_name = ?
                ORDER BY progress_id DESC LIMIT 1
                """,
                (student_id, payload.subject_name, payload.workbook_name),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE school_work_progress
                    SET completion_rate = ?, completed_pages = ?, target_pages = ?, note = ?, updated_at = ?
                    WHERE progress_id = ?
                    """,
                    (
                        payload.completion_rate,
                        payload.completed_pages,
                        payload.target_pages,
                        payload.note,
                        now,
                        existing["progress_id"],
                    ),
                )
                row = conn.execute("SELECT * FROM school_work_progress WHERE progress_id = ?", (existing["progress_id"],)).fetchone()
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO school_work_progress (
                        student_id, subject_name, workbook_name, completion_rate,
                        completed_pages, target_pages, note, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student_id,
                        payload.subject_name,
                        payload.workbook_name,
                        payload.completion_rate,
                        payload.completed_pages,
                        payload.target_pages,
                        payload.note,
                        now,
                    ),
                )
                row = conn.execute("SELECT * FROM school_work_progress WHERE progress_id = ?", (cursor.lastrowid,)).fetchone()
        return SchoolWorkProgressItem(
            progress_id=row["progress_id"],
            student_id=row["student_id"],
            subject_name=row["subject_name"],
            workbook_name=row["workbook_name"],
            completion_rate=row["completion_rate"],
            completed_pages=row["completed_pages"],
            target_pages=row["target_pages"],
            note=row["note"],
            updated_at=row["updated_at"],
        )

    def save_student_summary(self, summary: StudentStateSummary, generation_mode: str = "manual") -> StudentStateSummary:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO student_state_snapshots (
                    student_id, current_status, risk_signals, next_best_actions, recommended_response,
                    one_line_analysis, recommended_action, cited_document_titles, source_rankings, generated_at, generation_mode, fallback_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.student_id,
                    summary.current_status,
                    json.dumps(summary.risk_signals, ensure_ascii=False),
                    json.dumps(summary.next_best_actions, ensure_ascii=False),
                    summary.recommended_response,
                    summary.one_line_analysis,
                    summary.recommended_action,
                    json.dumps(summary.cited_document_titles, ensure_ascii=False),
                    json.dumps([item.model_dump() for item in summary.source_rankings], ensure_ascii=False),
                    summary.generated_at.isoformat(),
                    generation_mode,
                    1 if summary.fallback_used else 0,
                ),
            )
        return summary

    def get_latest_student_summary(self, student_id: str) -> StudentStateSummary | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM student_state_snapshots
                WHERE student_id = ?
                ORDER BY generated_at DESC, snapshot_id DESC
                LIMIT 1
                """,
                (student_id,),
            ).fetchone()
        if not row:
            return None
        return StudentStateSummary(
            student_id=row["student_id"],
            current_status=row["current_status"],
            risk_signals=json.loads(row["risk_signals"]),
            next_best_actions=json.loads(row["next_best_actions"]),
            recommended_response=row["recommended_response"],
            one_line_analysis=row["one_line_analysis"],
            recommended_action=row["recommended_action"],
            cited_document_titles=json.loads(row["cited_document_titles"]),
            source_rankings=[SummarySourceRanking.model_validate(item) for item in json.loads(row["source_rankings"])],
            current_status_sources=[f"{item['rank']}位 {item['title']}" for item in json.loads(row["source_rankings"]) if "current_status" in item["used_for"]][:3],
            risk_signal_sources=[f"{item['rank']}位 {item['title']}" for item in json.loads(row["source_rankings"]) if "risk_signals" in item["used_for"]][:3],
            next_best_action_sources=[f"{item['rank']}位 {item['title']}" for item in json.loads(row["source_rankings"]) if "next_best_actions" in item["used_for"]][:3],
            recommended_response_sources=[f"{item['rank']}位 {item['title']}" for item in json.loads(row["source_rankings"]) if "recommended_response" in item["used_for"]][:3],
            generated_at=row["generated_at"],
            fallback_used=bool(row["fallback_used"]),
        )

    def search_rag_chunks(self, student_id: str, query: str, limit: int = 8, document_types: list[str] | None = None) -> list[RagChunkSearchResult]:
        embedding = build_embedding(query)
        document_type_payload = json.dumps(document_types or [])
        with get_connection() as conn:
            if document_types:
                rows = conn.execute(
                    """
                    SELECT rc.chunk_id, rc.document_id, rc.student_id, rc.title, rc.document_type, rc.document_date, rc.chunk_text,
                           rc.embedding_vector_json,
                           COALESCE((
                               SELECT bm25(rag_chunks_fts) FROM rag_chunks_fts WHERE rowid = rc.chunk_id
                           ), 0.0) AS bm25_score
                    FROM rag_chunks rc
                    WHERE rc.student_id = ?
                      AND rc.document_date >= datetime('now', '-30 day')
                      AND rc.document_type IN (SELECT value FROM json_each(?))
                    ORDER BY rc.document_date DESC, rc.chunk_id DESC
                    """,
                    (student_id, document_type_payload),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT rc.chunk_id, rc.document_id, rc.student_id, rc.title, rc.document_type, rc.document_date, rc.chunk_text,
                           rc.embedding_vector_json,
                           COALESCE((
                               SELECT bm25(rag_chunks_fts) FROM rag_chunks_fts WHERE rowid = rc.chunk_id
                           ), 0.0) AS bm25_score
                    FROM rag_chunks rc
                    WHERE rc.student_id = ?
                      AND rc.document_date >= datetime('now', '-30 day')
                    ORDER BY rc.document_date DESC, rc.chunk_id DESC
                    """,
                    (student_id,),
                ).fetchall()
        scored = []
        for row in rows:
            vector = deserialize_embedding(row["embedding_vector_json"])
            type_boost = {
                "test_report": 0.45,
                "homework_history": 0.35,
                "counseling_memo": 0.3,
                "teacher_note": 0.25,
                "mock_exam": 0.15,
                "score_trend": 0.1,
                "attendance": 0.05,
            }.get(row["document_type"], 0.0)
            score = cosine_similarity(embedding, vector) + recency_boost(datetime.fromisoformat(row["document_date"])) + type_boost - float(row["bm25_score"])
            if query and query.lower() in row["chunk_text"].lower():
                score += 0.5
            scored.append(
                RagChunkSearchResult(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    student_id=row["student_id"],
                    title=row["title"],
                    document_type=row["document_type"],
                    document_date=row["document_date"],
                    chunk_text=row["chunk_text"],
                    score=score,
                )
            )
        scored.sort(key=lambda item: (-item.score, item.document_date), reverse=False)
        return scored[:limit]

    def save_approval(self, approval: HomeworkApproval) -> HomeworkApproval:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO approvals (student_id, approved_problem_nos, removed_problem_nos, approval_mode, teacher_comment, approved_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    approval.student_id,
                    json.dumps(approval.approved_problem_nos, ensure_ascii=False),
                    json.dumps(approval.removed_problem_nos, ensure_ascii=False),
                    approval.approval_mode,
                    approval.teacher_comment,
                    approval.approved_at.isoformat(),
                ),
            )
            conn.execute(
                """
                INSERT INTO homework_history (student_id, assigned_date, approved_problem_groups, expected_load, completion_status, teacher_comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval.student_id,
                    approval.approved_at.isoformat(),
                    json.dumps(approval.approved_problem_nos, ensure_ascii=False),
                    "appropriate",
                    "approved",
                    approval.teacher_comment,
                    approval.approved_at.isoformat(),
                ),
            )
        return approval

    def build_overview_items(self) -> list[StudentOverviewItem]:
        return [
            StudentOverviewItem(
                student_id=student.student_id,
                display_name=student.display_name,
                grade=student.grade,
                class_name=student.class_name,
                school_name=student.school_name,
                next_regular_exam_date=student.next_regular_exam_date,
                days_until_regular_exam=student.days_until_regular_exam,
                target_level=student.target_level,
                attention_level=student.attention_level,
                homework_completion_rate=int(student.homework_completion_rate or 0),
                one_line_analysis=student.one_line_analysis or student.persona_summary,
                recommended_action=student.recommended_action or (student.weakness_history[0] if student.weakness_history else "確認"),
            )
            for student in self.list_students()
        ]

    def _index_document(self, conn, document_id: int, student_id: str, document_type: str, title: str, body_text: str, document_date: str) -> None:
        conn.execute("DELETE FROM rag_chunks_fts WHERE rowid IN (SELECT chunk_id FROM rag_chunks WHERE document_id = ?)", (document_id,))
        conn.execute("DELETE FROM rag_chunks WHERE document_id = ?", (document_id,))
        chunks = chunk_document(document_type, body_text)
        embedded_at = datetime.now(timezone.utc).isoformat()
        for index, (chunk_type, chunk_text) in enumerate(chunks):
            vector = serialize_embedding(build_embedding(f"{title}\n{chunk_text}"))
            cursor = conn.execute(
                """
                INSERT INTO rag_chunks (
                    document_id, student_id, title, document_type, document_date,
                    chunk_text, chunk_type, chunk_order, chunk_metadata_json,
                    embedding_model, embedding_vector_json, embedded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    student_id,
                    title,
                    document_type,
                    document_date,
                    chunk_text,
                    chunk_type,
                    index,
                    json.dumps({"title": title, "chunk_type": chunk_type}, ensure_ascii=False),
                    "local-hash-v1",
                    vector,
                    embedded_at,
                ),
            )
            conn.execute(
                "INSERT INTO rag_chunks_fts(rowid, chunk_text, title, document_type) VALUES (?, ?, ?, ?)",
                (cursor.lastrowid, chunk_text, title, document_type),
            )

    def _row_to_student(self, row) -> StudentProfile:
        return StudentProfile(
            student_id=row["student_id"],
            display_name=row["display_name"],
            grade=row["grade"],
            class_name=row["class_name"],
            school_name=row["school_name"],
            next_regular_exam_date=row["next_regular_exam_date"],
            days_until_regular_exam=self._days_until_exam(row["next_regular_exam_date"]),
            target_level=row["target_level"],
            persona_summary=row["persona_summary"],
            recent_scores=json.loads(row["recent_scores"]),
            homework_style_notes=row["homework_style_notes"],
            weakness_history=json.loads(row["weakness_history"]),
            preferred_difficulty=row["preferred_difficulty"],
            attention_level=row["attention_level"],
            homework_completion_rate=int(row["homework_completion_rate"]) if row["homework_completion_rate"] is not None else None,
            one_line_analysis=row["one_line_analysis"],
            recommended_action=row["recommended_action"],
            latest_summary_generated_at=row["latest_summary_generated_at"],
        )

    def _days_until_exam(self, exam_date: str | None) -> int | None:
        if not exam_date:
            return None
        exam = datetime.fromisoformat(exam_date)
        today = datetime.now(timezone.utc).date()
        return (exam.date() - today).days

    def _row_to_document(self, row) -> StudentDocumentResponse:
        return StudentDocumentResponse(
            document_id=row["document_id"],
            student_id=row["student_id"],
            document_type=row["document_type"],
            title=row["title"],
            body_text=row["body_text"],
            source_system=row["source_system"],
            authored_by=row["authored_by"],
            document_date=row["document_date"],
            asset_paths=json.loads(row["asset_paths_json"]) if row["asset_paths_json"] else [],
            payload=json.loads(row["payload_json"]) if row["payload_json"] else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_processing_job(self, row) -> ProcessingJob:
        return ProcessingJob(
            job_id=row["job_id"],
            student_id=row["student_id"],
            source_image_ids=json.loads(row["source_image_ids_json"]) if row["source_image_ids_json"] else [],
            status=row["status"],
            job_type=row["job_type"] or "confirmation_test_analysis",
            current_stage=row["current_stage"] or "queued",
            progress_message=row["progress_message"] or "",
            notification_message=row["notification_message"],
            error_detail=row["error_detail"],
            result_document_id=row["result_document_id"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )
