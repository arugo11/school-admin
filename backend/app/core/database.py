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
    generated_at TEXT NOT NULL,
    generation_mode TEXT NOT NULL,
    fallback_used INTEGER NOT NULL DEFAULT 0
);
"""


def get_connection() -> sqlite3.Connection:
    path: Path = settings.database_path
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
