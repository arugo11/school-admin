from __future__ import annotations

import base64
import json
import asyncio
import logging
import time
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.azure_runtime_keys import azure_cli_key
from app.core.config import settings
from app.schemas import AnalysisResult

logger = logging.getLogger("uvicorn.error")


class AzureOpenAIClient:
    @staticmethod
    def _data_url(image_bytes: bytes, mime_type: str) -> str:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    async def _post_chat(self, body: dict[str, Any]) -> dict[str, Any]:
        key = settings.azure_openai_key or azure_cli_key("sit-copilot", "sitcopilotaoai23088")
        if not key:
            raise RuntimeError("AZURE_OPENAI_KEY is not configured")
        endpoint = (
            settings.azure_openai_endpoint.rstrip("/")
            + f"/openai/deployments/{settings.azure_openai_deployment}/chat/completions"
            + f"?api-version={settings.azure_openai_api_version}"
        )
        headers = {"api-key": key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            last_error: Exception | None = None
            for attempt in range(5):
                try:
                    started = time.perf_counter()
                    response = await client.post(endpoint, headers=headers, json=body)
                    response.raise_for_status()
                    logger.info("AOAI chat success: attempt=%s duration_ms=%.1f", attempt + 1, (time.perf_counter() - started) * 1000)
                    return response.json()
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    logger.warning(
                        "AOAI chat HTTP error: attempt=%s status=%s",
                        attempt + 1,
                        exc.response.status_code,
                    )
                    if exc.response.status_code != 429 or attempt == 4:
                        raise
                    retry_after_ms = exc.response.headers.get("retry-after-ms")
                    retry_after = retry_after_ms or exc.response.headers.get("retry-after")
                    delay = 2.0 * (attempt + 1)
                    if retry_after:
                        try:
                            delay = max(delay, float(retry_after) / (1000.0 if retry_after_ms else 1.0))
                        except ValueError:
                            pass
                    logger.warning("AOAI chat retrying after %.1fs", delay)
                    await asyncio.sleep(delay)
            if last_error:
                raise last_error
        raise RuntimeError("azure-openai-request-failed")

    async def _post_json_chat_with_retry(self, *, system_prompt: str, user_content: list[dict[str, Any]], max_tokens: int) -> dict[str, Any]:
        last_error: Exception | None = None
        repair_note = ""
        for attempt in range(2):
            payload = await self._post_chat(
                {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content + ([{"type": "text", "text": repair_note}] if repair_note else [])},
                    ],
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"},
                    "max_tokens": max_tokens,
                }
            )
            content = payload["choices"][0]["message"]["content"]
            try:
                parsed = json.loads(content)
                if not isinstance(parsed, dict):
                    raise RuntimeError("llm-ocr-invalid-json-shape")
                return parsed
            except Exception as exc:
                last_error = exc
                repair_note = (
                    "前回の応答はJSONとして不正でした。"
                    "説明文は一切含めず、指定したキーだけを持つ有効なJSON objectを返してください。"
                )
        if last_error:
            raise last_error
        raise RuntimeError("llm-ocr-invalid-json")

    async def analyze(self, system_prompt: str, user_payload: dict) -> AnalysisResult:
        body = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        payload = await self._post_chat(body)
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        try:
            result = AnalysisResult.model_validate(parsed)
        except ValidationError as exc:
            raise RuntimeError(f"analysis-schema-invalid: {exc}") from exc
        return result

    async def extract_box_ocr(
        self,
        *,
        problem_no: str,
        work_image_bytes: bytes | None,
        final_image_bytes: bytes | None,
        work_mime_type: str = "image/png",
        final_mime_type: str = "image/png",
    ) -> dict[str, Any]:
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "以下は 1 問分の答案画像です。"
                    "1枚目は計算過程欄、2枚目は最終解答欄です。"
                    "JSONのみで {\"work_text\":\"...\",\"final_answer\":\"...\",\"confidence\":\"high|medium|low\",\"notes\":[...]} を返してください。"
                    f" problem_no={problem_no}。空欄は空文字。数式は見えたまま短く返してください。"
                ),
            }
        ]
        if work_image_bytes is not None:
            user_content.append({"type": "image_url", "image_url": {"url": self._data_url(work_image_bytes, work_mime_type)}})
        if final_image_bytes is not None:
            user_content.append({"type": "image_url", "image_url": {"url": self._data_url(final_image_bytes, final_mime_type)}})
        parsed = await self._post_json_chat_with_retry(
            system_prompt="あなたは数学答案のOCR補助です。推測しすぎず、見えた文字だけをJSONで返してください。",
            user_content=user_content,
            max_tokens=300,
        )
        if not isinstance(parsed, dict):
            raise RuntimeError("box-ocr-invalid")
        return {
            "work_text": str(parsed.get("work_text", "") or "").strip(),
            "final_answer": str(parsed.get("final_answer", "") or "").strip(),
            "confidence": str(parsed.get("confidence", "low") or "low"),
            "notes": parsed.get("notes", []),
        }

    async def extract_box_ocr_bulk(
        self,
        *,
        work_sheet_bytes: bytes | None,
        final_sheet_bytes: bytes | None,
        problem_nos: list[str],
        work_mime_type: str = "image/png",
        final_mime_type: str = "image/png",
    ) -> dict[str, Any]:
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "1枚目は各問題の計算過程 crop を縦に並べた画像、2枚目は各問題の最終解答 crop を縦に並べた画像です。"
                    f"対象問題は {', '.join(problem_nos)} です。"
                    "JSONのみで {\"items\":[{\"problem_no\":\"Q1\",\"work_text\":\"...\",\"final_answer\":\"...\",\"confidence\":\"high|medium|low\",\"notes\":[...]}, ...]} を返してください。"
                    "各行のラベルは画像内の Q番号です。空欄は空文字。見えた文字だけを短く返してください。"
                ),
            }
        ]
        if work_sheet_bytes is not None:
            user_content.append({"type": "image_url", "image_url": {"url": self._data_url(work_sheet_bytes, work_mime_type)}})
        if final_sheet_bytes is not None:
            user_content.append({"type": "image_url", "image_url": {"url": self._data_url(final_sheet_bytes, final_mime_type)}})
        parsed = await self._post_json_chat_with_retry(
            system_prompt="あなたは数学答案のOCR補助です。推測しすぎず、見えた文字だけを問題ごとにJSONで返してください。",
            user_content=user_content,
            max_tokens=700,
        )
        if not isinstance(parsed, dict) or not isinstance(parsed.get("items"), list):
            raise RuntimeError("bulk-box-ocr-invalid")
        return parsed

    async def detect_sheet_layout(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        mode_hint: str = "auto",
    ) -> dict[str, Any]:
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "この答案画像をOCR用に解析してください。"
                    "JSONのみで "
                    "{\"mode\":\"confirmation_test|worksheet|unknown\","
                    "\"test_id\":\"... or null\","
                    "\"visible_problem_nos\":[\"Q1\",...],"
                    "\"notes\":[...]}"
                    " を返してください。"
                    "confirmation_test なら、見えている問題だけ返してください。"
                    f" mode_hint={mode_hint}。"
                ),
            },
            {"type": "image_url", "image_url": {"url": self._data_url(image_bytes, mime_type)}},
        ]
        return await self._post_json_chat_with_retry(
            system_prompt=(
                "あなたは数学答案画像のレイアウト認識器です。"
                "画像を見て、confirmation test かどうかと、写っている問題番号だけをJSONで返してください。"
                "推測しすぎず、見えない問題は返さないでください。"
            ),
            user_content=user_content,
            max_tokens=220,
        )

    async def read_confirmation_test_image(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        test_id: str | None,
        visible_problem_nos: list[str],
    ) -> dict[str, Any]:
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "この確認テストの解答用紙画像を読んでください。"
                    "JSONのみで "
                    "{\"mode\":\"confirmation_test\","
                    "\"test_id\":\"... or null\","
                    "\"items\":[{\"problem_no\":\"Q1\",\"work_text\":\"...\",\"final_answer\":\"...\",\"recognized_answer\":\"...\",\"uncertainty\":[...],\"notes\":[...]}],"
                    "\"notes\":[...]}"
                    " を返してください。"
                    f"対象は見えている問題 {', '.join(visible_problem_nos) if visible_problem_nos else 'なし'} です。"
                    "左の計算過程欄と右の最終解答欄を分け、recognized_answer は最終解答欄を優先してください。"
                    "空欄は空文字。見えた文字だけを返してください。"
                    + (f" test_id は {test_id} を優先して確認してください。" if test_id else "")
                ),
            },
            {"type": "image_url", "image_url": {"url": self._data_url(image_bytes, mime_type)}},
        ]
        return await self._post_json_chat_with_retry(
            system_prompt=(
                "あなたは数学答案のマルチモーダルOCRです。"
                "画像を直接読んで、問題ごとの計算過程と最終解答をJSONで返してください。"
                "見えない内容は空文字にし、不確実な点は uncertainty に短く残してください。"
            ),
            user_content=user_content,
            max_tokens=2200,
        )

    async def read_worksheet_image(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
    ) -> dict[str, Any]:
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "この数学答案画像をOCRしてください。"
                    "JSONのみで "
                    "{\"mode\":\"worksheet\","
                    "\"test_id\":null,"
                    "\"items\":[{\"problem_no\":\"Q1\",\"recognized_answer\":\"...\",\"raw_text\":\"...\",\"uncertainty\":[...]}],"
                    "\"notes\":[...]}"
                    " を返してください。"
                    "問題番号が見えるものだけ返してください。見えた文字だけを短く返してください。"
                ),
            },
            {"type": "image_url", "image_url": {"url": self._data_url(image_bytes, mime_type)}},
        ]
        return await self._post_json_chat_with_retry(
            system_prompt="あなたは数学答案のOCRです。画像を直接読んで、問題番号ごとの回答をJSONで返してください。",
            user_content=user_content,
            max_tokens=1600,
        )
