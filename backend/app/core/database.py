from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS uploads (
    source_image_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    source_mode TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    approved_problem_nos TEXT NOT NULL,
    removed_problem_nos TEXT NOT NULL,
    approval_mode TEXT NOT NULL,
    teacher_comment TEXT NOT NULL,
    approved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS replays (
    student_id TEXT PRIMARY KEY,
    snapshot_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    grade TEXT NOT NULL,
    class_name TEXT NOT NULL DEFAULT '',
    school_name TEXT NOT NULL DEFAULT '',
    next_regular_exam_date TEXT,
    target_level TEXT NOT NULL,
    persona_summary TEXT NOT NULL,
    recent_scores TEXT NOT NULL,
    homework_style_notes TEXT NOT NULL,
    weakness_history TEXT NOT NULL,
    preferred_difficulty TEXT NOT NULL,
    attention_level TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS student_documents (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    document_type TEXT NOT NULL,
    title TEXT NOT NULL,
    body_text TEXT NOT NULL,
    source_system TEXT NOT NULL,
    authored_by TEXT NOT NULL,
    document_date TEXT NOT NULL,
    asset_paths_json TEXT NOT NULL DEFAULT '[]',
    payload_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS student_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    metric_value REAL NOT NULL,
    metric_date TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS school_work_progress (
    progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    subject_name TEXT NOT NULL,
    workbook_name TEXT NOT NULL,
    completion_rate INTEGER NOT NULL,
    completed_pages INTEGER NOT NULL,
    target_pages INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS homework_history (
    homework_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    assigned_date TEXT NOT NULL,
    approved_problem_groups TEXT NOT NULL,
    expected_load TEXT NOT NULL,
    completion_status TEXT NOT NULL,
    teacher_comment TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    student_id TEXT NOT NULL,
    title TEXT NOT NULL,
    document_type TEXT NOT NULL,
    document_date TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_type TEXT NOT NULL,
    chunk_order INTEGER NOT NULL,
    chunk_metadata_json TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_vector_json TEXT NOT NULL,
    embedded_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
    chunk_text,
    title,
    document_type,
    content='',
    tokenize='unicode61'
);

CREATE TABLE IF NOT EXISTS student_state_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    current_status TEXT NOT NULL,
    risk_signals TEXT NOT NULL,
    next_best_actions TEXT NOT NULL,
    recommended_response TEXT NOT NULL,
    one_line_analysis TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    cited_document_titles TEXT NOT NULL,
    source_rankings TEXT NOT NULL DEFAULT '[]',
    generated_at TEXT NOT NULL,
    generation_mode TEXT NOT NULL,
    fallback_used INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS processing_jobs (
    job_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    source_image_ids_json TEXT NOT NULL,
    status TEXT NOT NULL,
    progress_message TEXT NOT NULL DEFAULT '',
    error_detail TEXT,
    result_document_id INTEGER,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);
"""


def get_connection() -> sqlite3.Connection:
    path: Path = settings.database_path
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(students)").fetchall()}
    if "class_name" not in columns:
        conn.execute("ALTER TABLE students ADD COLUMN class_name TEXT NOT NULL DEFAULT ''")
    if "school_name" not in columns:
        conn.execute("ALTER TABLE students ADD COLUMN school_name TEXT NOT NULL DEFAULT ''")
    if "next_regular_exam_date" not in columns:
        conn.execute("ALTER TABLE students ADD COLUMN next_regular_exam_date TEXT")
    snapshot_columns = {row["name"] for row in conn.execute("PRAGMA table_info(student_state_snapshots)").fetchall()}
    if "source_rankings" not in snapshot_columns:
        conn.execute("ALTER TABLE student_state_snapshots ADD COLUMN source_rankings TEXT NOT NULL DEFAULT '[]'")
    document_columns = {row["name"] for row in conn.execute("PRAGMA table_info(student_documents)").fetchall()}
    if "asset_paths_json" not in document_columns:
        conn.execute("ALTER TABLE student_documents ADD COLUMN asset_paths_json TEXT NOT NULL DEFAULT '[]'")
    if "payload_json" not in document_columns:
        conn.execute("ALTER TABLE student_documents ADD COLUMN payload_json TEXT")
    return conn
