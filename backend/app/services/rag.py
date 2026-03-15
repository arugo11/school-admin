from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Iterable


EMBEDDING_DIM = 32
EMBEDDING_MODEL = "local-hash-v1"


def tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^\w一-龠ぁ-んァ-ヶ]+", text.lower()) if token]


def build_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    counts = Counter(tokenize(text))
    if not counts:
        return [0.0] * dim
    vector = [0.0] * dim
    for token, count in counts.items():
        digest = sha256(token.encode("utf-8")).digest()
        index = digest[0] % dim
        sign = 1.0 if digest[1] % 2 == 0 else -1.0
        vector[index] += sign * float(count)
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return [0.0] * dim
    return [value / norm for value in vector]


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    left_list = list(left)
    right_list = list(right)
    return sum(l * r for l, r in zip(left_list, right_list, strict=False))


def chunk_document(document_type: str, body_text: str) -> list[tuple[str, str]]:
    pieces = [part.strip() for part in re.split(r"[。\n]+", body_text) if part.strip()]
    if document_type == "test_report" and len(pieces) > 1:
        labels = ["weakness", "mistake_pattern", "teacher_view"]
        return [(labels[min(index, len(labels) - 1)], piece) for index, piece in enumerate(pieces)]
    if document_type in {"counseling_memo", "teacher_note", "mock_exam", "score_trend"}:
        return [(document_type, body_text.strip())]
    if document_type == "attendance":
        return [("attendance_summary", piece) for piece in pieces[:2]] or [("attendance_summary", body_text.strip())]
    if document_type == "homework_history":
        return [("homework_event", piece) for piece in pieces] or [("homework_event", body_text.strip())]
    return [(document_type, body_text.strip())]


def serialize_embedding(vector: list[float]) -> str:
    return json.dumps(vector)


def deserialize_embedding(raw: str) -> list[float]:
    return [float(value) for value in json.loads(raw)]


def recency_boost(document_date: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    days = max((now - document_date).days, 0)
    return max(0.0, 1.0 - (days / 30.0))


def within_recent_window(document_date: datetime, days: int = 30, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return document_date >= now - timedelta(days=days)
