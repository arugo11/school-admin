#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'backend'))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.analysis import AnalysisService  # noqa: E402
from app.services.data_store import load_catalog, load_students  # noqa: E402
from app.services.ocr_normalizer import normalize_ocr_result  # noqa: E402

client = TestClient(app)


def main() -> int:
    rows: list[tuple[str, str, str]] = []

    too_large = client.post(
        '/api/uploads',
        data={'student_id': 's-03', 'mode': 'live'},
        files={'file': ('large.png', b'0' * (5 * 1024 * 1024 + 1), 'image/png')},
    )
    rows.append(('oversized image', 'pass' if too_large.status_code == 400 else 'fail', too_large.text[:80]))

    raw = {
        'analyzeResult': {
            'readResults': [{'lines': [{'text': 'Q1 ???', 'confidence': 0.52}]}]
        }
    }
    normalized = client.post('/api/ocr/normalize', json={'student_id': 's-03', 'source_image_id': 'fi-1', 'raw_ocr': raw})
    rows.append(('malformed OCR payload', 'pass' if normalized.status_code == 200 else 'fail', normalized.text[:80]))

    replay = client.get('/api/demo/s-03/replay').json()
    analysis = client.post('/api/analysis/run', json={
        'student_id': 's-03',
        'normalized_ocr': replay['normalized_ocr'],
        'mode': 'live',
        'action': 'initial',
    }).json()
    rows.append(('OpenAI unavailable fallback', 'pass' if analysis['fallback_used'] else 'fail', analysis['teacher_note']))

    rows.append(('Vision failure UX path', 'warning', 'Live OCR still depends on env; UI exposes replay fallback banner and seeded path.'))
    rows.append(('network timeout UX path', 'warning', 'Documented in runbook with switch to replay mode.'))

    markdown = ['# Failure Injection Eval', '', '| Case | Result | Note |', '| --- | --- | --- |']
    markdown.extend(f'| {case} | {result} | {note} |' for case, result, note in rows)
    report = '\n'.join(markdown)
    target = REPO_ROOT / 'docs' / 'evals' / 'failure_injection_eval.md'
    target.write_text(report)
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
