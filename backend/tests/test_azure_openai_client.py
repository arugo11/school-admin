from __future__ import annotations

import asyncio

import httpx

from app.clients import azure_openai as module


class _FakeAsyncClient:
    def __init__(self, responses: list[httpx.Response], calls: list[int], **_kwargs) -> None:
        self._responses = responses
        self._calls = calls

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, *, headers: dict[str, str], json: dict) -> httpx.Response:
        del headers, json
        response = self._responses.pop(0)
        response.request = httpx.Request("POST", url)
        self._calls.append(response.status_code)
        return response


def test_post_chat_retries_transient_500(monkeypatch) -> None:
    calls: list[int] = []
    responses = [
        httpx.Response(500, json={"error": {"message": "transient"}}),
        httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]}),
    ]

    monkeypatch.setattr(module, "azure_cli_key", lambda *_args, **_kwargs: "test-key")
    monkeypatch.setattr(module.settings, "azure_openai_key", "test-key")
    monkeypatch.setattr(
        module.httpx,
        "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(responses, calls, **kwargs),
    )

    payload = asyncio.run(module.AzureOpenAIClient()._post_chat({"messages": []}))

    assert calls == [500, 200]
    assert payload["choices"][0]["message"]["content"] == "{}"
