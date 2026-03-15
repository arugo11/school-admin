from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.schemas import CatalogProblem, StudentProfile
from app.storage.repository import Repository


repo = Repository()


@lru_cache(maxsize=1)
def load_students() -> list[StudentProfile]:
    path = settings.data_dir / "students" / "students.json"
    rows = json.loads(path.read_text())
    repo.ensure_bootstrap(rows)
    return repo.list_students()


@lru_cache(maxsize=1)
def load_catalog() -> list[CatalogProblem]:
    path = settings.data_dir / "catalog" / "catalog.json"
    return [CatalogProblem.model_validate(item) for item in json.loads(path.read_text())]


def list_fixture_raw_paths() -> list[Path]:
    return sorted((settings.data_dir / "raw_ocr").glob("*.json"))
