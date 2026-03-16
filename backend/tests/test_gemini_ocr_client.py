from __future__ import annotations

import asyncio

import httpx

from app.clients import gemini_ocr as module


class _FakeAsyncClient:
    def __init__(self, responses: list[httpx.Response], **_kwargs) -> None:
        self._responses = responses

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, *, headers: dict[str, str], json: dict) -> httpx.Response:
        del headers, json
        response = self._responses.pop(0)
        response.request = httpx.Request("POST", url)
        return response


def test_extract_box_ocr_parses_gemini_json(monkeypatch) -> None:
    monkeypatch.setattr(module.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(
        module.httpx,
        "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(
            [
                httpx.Response(
                    200,
                    json={
                        "candidates": [
                            {
                                "content": {
                                    "parts": [
                                        {
                                            "text": '{"problem_no":"Q1","work_text":"x+1=2","final_answer":"2","confidence":"high","notes":[]}'
                                        }
                                    ]
                                }
                            }
                        ]
                    },
                )
            ],
            **kwargs,
        ),
    )

    payload = asyncio.run(
        module.GeminiOcrClient().extract_box_ocr(
            problem_no="Q1",
            work_image_bytes=b"work",
            final_image_bytes=b"final",
        )
    )

    assert payload["problem_no"] == "Q1"
    assert payload["work_text"] == "x+1=2"
    assert payload["final_answer"] == "2"
