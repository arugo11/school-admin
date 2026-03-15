from __future__ import annotations

import asyncio

import httpx

from app.core.azure_runtime_keys import azure_cli_key
from app.core.config import settings


class VisionClient:
    async def analyze(self, image_bytes: bytes, content_type: str) -> dict:
        key = settings.azure_vision_key or azure_cli_key("school-admin-precheck-rg", "schooladminocr23088")
        if not key:
            raise RuntimeError("AZURE_VISION_KEY is not configured")
        endpoint = settings.azure_vision_endpoint.rstrip("/") + "/vision/v3.2/read/analyze"
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": content_type,
        }
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(endpoint, headers=headers, content=image_bytes)
            response.raise_for_status()
            operation_location = response.headers.get("operation-location")
            if not operation_location:
                raise RuntimeError("Vision response missing operation-location")
            for _ in range(10):
                poll_response = await client.get(
                    operation_location,
                    headers={"Ocp-Apim-Subscription-Key": key},
                )
                poll_response.raise_for_status()
                payload = poll_response.json()
                status = payload.get("status", "").lower()
                if status == "succeeded":
                    return payload
                if status == "failed":
                    raise RuntimeError("Vision OCR failed")
                await asyncio.sleep(settings.vision_poll_seconds)
        raise RuntimeError("Vision OCR timed out")
