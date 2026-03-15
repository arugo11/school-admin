from __future__ import annotations

import json
from datetime import datetime, timezone

from app.core.database import get_connection
from app.schemas import HomeworkApproval, UploadResponse


class Repository:
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
        return approval
