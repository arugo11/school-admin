from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    env_path = repo_root / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


class Settings:
    def __init__(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        self.repo_root = repo_root
        self.data_dir = Path(os.getenv("APP_DATA_DIR", repo_root / "data")).resolve()
        self.frontend_dist_dir = Path(os.getenv("FRONTEND_DIST_DIR", repo_root / "frontend" / "dist")).resolve()
        self.upload_dir = self.data_dir / "uploads"
        self.ocr_debug_dir = self.data_dir / "ocr_debug"
        self.database_path = self.data_dir / "school_admin.sqlite3"
        self.azure_vision_endpoint = os.getenv("AZURE_VISION_ENDPOINT", "https://japaneast.api.cognitive.microsoft.com/")
        self.azure_vision_key = os.getenv("AZURE_VISION_KEY")
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://japaneast.api.cognitive.microsoft.com/")
        self.azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
        self.azure_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "sit-copilot-demo-chat")
        self.azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        self.azure_analysis_live_enabled = os.getenv("AZURE_ANALYSIS_LIVE_ENABLED", "false").lower() == "true"
        self.llm_ocr_provider = os.getenv("LLM_OCR_PROVIDER", "gemini")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.llm_ocr_concurrency = max(1, int(os.getenv("LLM_OCR_CONCURRENCY", "4")))
        self.llm_ocr_request_timeout_seconds = float(os.getenv("LLM_OCR_REQUEST_TIMEOUT_SECONDS", "12"))
        self.request_timeout_seconds = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
        self.vision_poll_seconds = float(os.getenv("VISION_POLL_SECONDS", "1.5"))


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.ocr_debug_dir.mkdir(parents=True, exist_ok=True)
