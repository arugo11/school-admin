from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")


class GeminiOcrClient:
    def __init__(self) -> None:
        self._endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"

    @staticmethod
    def _inline_data(image_bytes: bytes, mime_type: str) -> dict[str, str]:
        return {
            "mime_type": mime_type,
            "data": base64.b64encode(image_bytes).decode("ascii"),
        }

    async def extract_box_ocr(
        self,
        *,
        problem_no: str,
        work_image_bytes: bytes | None,
        final_image_bytes: bytes | None,
        work_mime_type: str = "image/png",
        final_mime_type: str = "image/png",
    ) -> dict[str, Any]:
        api_key = settings.gemini_api_key
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        parts: list[dict[str, Any]] = [
            {
                "text": (
                    "あなたは数学答案のOCR補助です。"
                    "1問分の画像を読み、見えた文字だけを返してください。"
                    "JSONのみで "
                    "{\"problem_no\":\"Q1\",\"work_text\":\"...\",\"final_answer\":\"...\",\"confidence\":\"high|medium|low\",\"notes\":[...]}"
                    f" を返してください。problem_no={problem_no}。"
                    "推測しすぎず、空欄は空文字にしてください。"
                )
            }
        ]
        if work_image_bytes is not None:
            parts.append({"inline_data": self._inline_data(work_image_bytes, work_mime_type)})
        if final_image_bytes is not None:
            parts.append({"inline_data": self._inline_data(final_image_bytes, final_mime_type)})

        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
        async with httpx.AsyncClient(timeout=settings.llm_ocr_request_timeout_seconds) as client:
            last_error: Exception | None = None
            for attempt in range(3):
                try:
                    response = await client.post(self._endpoint, headers=headers, json=body)
                    response.raise_for_status()
                    payload = response.json()
                    text = self._extract_text(payload)
                    parsed = json.loads(text)
                    if not isinstance(parsed, dict):
                        raise RuntimeError("gemini-ocr-invalid-json-shape")
                    return {
                        "problem_no": str(parsed.get("problem_no", problem_no) or problem_no).strip().upper(),
                        "work_text": str(parsed.get("work_text", "") or "").strip(),
                        "final_answer": str(parsed.get("final_answer", "") or "").strip(),
                        "confidence": str(parsed.get("confidence", "low") or "low").strip().lower(),
                        "notes": [str(note) for note in parsed.get("notes", [])],
                    }
                except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError, RuntimeError) as exc:
                    last_error = exc
                    logger.warning("Gemini OCR error: attempt=%s type=%s", attempt + 1, exc.__class__.__name__)
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.4 * (attempt + 1))
            if last_error:
                raise last_error
        raise RuntimeError("gemini-ocr-request-failed")

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        candidates = payload.get("candidates") or []
        if not candidates:
            raise RuntimeError("gemini-ocr-empty-candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(str(part.get("text", "")) for part in parts)
        if not text.strip():
            raise RuntimeError("gemini-ocr-empty-text")
        return text
