#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_PDF = REPO_ROOT / 'data' / 'fixtures' / 'ocr-smoke-sample.pdf'


def _run_az(*args: str) -> str:
    result = subprocess.run(['az', *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _load_env(use_az_cli: bool) -> dict[str, str | None]:
    env = {
        'AZURE_VISION_ENDPOINT': os.getenv('AZURE_VISION_ENDPOINT', 'https://japaneast.api.cognitive.microsoft.com/'),
        'AZURE_VISION_KEY': os.getenv('AZURE_VISION_KEY'),
        'AZURE_OPENAI_ENDPOINT': os.getenv('AZURE_OPENAI_ENDPOINT', 'https://japaneast.api.cognitive.microsoft.com/'),
        'AZURE_OPENAI_KEY': os.getenv('AZURE_OPENAI_KEY'),
        'AZURE_OPENAI_DEPLOYMENT': os.getenv('AZURE_OPENAI_DEPLOYMENT', 'sit-copilot-demo-chat'),
        'AZURE_OPENAI_API_VERSION': os.getenv('AZURE_OPENAI_API_VERSION', '2024-10-21'),
    }
    if use_az_cli:
        env['AZURE_VISION_KEY'] = env['AZURE_VISION_KEY'] or _run_az('cognitiveservices', 'account', 'keys', 'list', '-g', 'school-admin-precheck-rg', '-n', 'schooladminocr23088', '--query', 'key1', '-o', 'tsv')
        env['AZURE_OPENAI_KEY'] = env['AZURE_OPENAI_KEY'] or _run_az('cognitiveservices', 'account', 'keys', 'list', '-g', 'sit-copilot', '-n', 'sitcopilotaoai23088', '--query', 'key1', '-o', 'tsv')
    return env


def run_vision(env: dict[str, str | None]) -> tuple[str, float, str]:
    if not env['AZURE_VISION_KEY']:
        return 'fail', 0.0, 'missing AZURE_VISION_KEY'
    endpoint = env['AZURE_VISION_ENDPOINT'].rstrip('/') + '/vision/v3.2/read/analyze'
    started = time.perf_counter()
    with httpx.Client(timeout=20) as client:
        response = client.post(
            endpoint,
            headers={
                'Ocp-Apim-Subscription-Key': env['AZURE_VISION_KEY'],
                'Content-Type': 'application/pdf',
            },
            content=SMOKE_PDF.read_bytes(),
        )
        response.raise_for_status()
        op = response.headers.get('operation-location')
        if not op:
            raise RuntimeError('missing operation-location header')
        for _ in range(10):
            poll = client.get(op, headers={'Ocp-Apim-Subscription-Key': env['AZURE_VISION_KEY']})
            poll.raise_for_status()
            payload = poll.json()
            if payload.get('status', '').lower() == 'succeeded':
                lines = []
                for page in payload.get('analyzeResult', {}).get('readResults', []):
                    lines.extend(line.get('text', '') for line in page.get('lines', []))
                elapsed = time.perf_counter() - started
                return 'pass', elapsed, f"lines={len(lines)}"
            if payload.get('status', '').lower() == 'failed':
                raise RuntimeError('Vision OCR failed')
            time.sleep(1.2)
    raise RuntimeError('Vision OCR timed out')


def run_openai(env: dict[str, str | None]) -> tuple[str, float, str]:
    if not env['AZURE_OPENAI_KEY']:
        return 'fail', 0.0, 'missing AZURE_OPENAI_KEY'
    endpoint = (
        env['AZURE_OPENAI_ENDPOINT'].rstrip('/')
        + f"/openai/deployments/{env['AZURE_OPENAI_DEPLOYMENT']}/chat/completions?api-version={env['AZURE_OPENAI_API_VERSION']}"
    )
    started = time.perf_counter()
    with httpx.Client(timeout=20) as client:
        response = client.post(
            endpoint,
            headers={'api-key': env['AZURE_OPENAI_KEY'], 'Content-Type': 'application/json'},
            json={
                'messages': [
                    {'role': 'system', 'content': 'Return JSON only.'},
                    {'role': 'user', 'content': '{"ping":"return ok"}'},
                ],
                'temperature': 0,
                'response_format': {'type': 'json_object'},
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = payload['choices'][0]['message']['content']
    elapsed = time.perf_counter() - started
    return 'pass', elapsed, content[:80]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--use-az-cli', action='store_true')
    parser.add_argument('--write-doc', default='')
    args = parser.parse_args()

    env = _load_env(args.use_az_cli)
    rows: list[tuple[str, str, float, str]] = []

    try:
        status, elapsed, note = run_vision(env)
    except Exception as exc:  # noqa: BLE001
        status, elapsed, note = 'fail', 0.0, str(exc)
    rows.append(('Vision Read OCR', status, elapsed, note))

    try:
        status, elapsed, note = run_openai(env)
    except Exception as exc:  # noqa: BLE001
        status, elapsed, note = 'fail', 0.0, str(exc)
    rows.append(('Azure OpenAI', status, elapsed, note))

    markdown = ['# Azure Smoke Check', '', f'Date: {time.strftime("%Y-%m-%d %H:%M:%S")}', '', '| Check | Status | Latency | Note |', '| --- | --- | --- | --- |']
    for name, status, elapsed, note in rows:
        markdown.append(f'| {name} | {status} | {elapsed:.2f}s | {note} |')
    markdown.append('')
    markdown.append('Secrets were loaded from environment or Azure CLI and were not printed.')
    report = '\n'.join(markdown)

    if args.write_doc:
        Path(args.write_doc).write_text(report)
    print(report)
    return 0 if all(status == 'pass' for _, status, _, _ in rows) else 1


if __name__ == '__main__':
    sys.exit(main())
