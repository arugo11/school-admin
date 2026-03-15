#!/usr/bin/env python3
from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'backend'))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def measure() -> tuple[float, float]:
    replay = client.get('/api/demo/s-03/replay').json()
    start = time.perf_counter()
    client.post('/api/ocr/normalize', json={
        'student_id': 's-03',
        'source_image_id': 'latency-1',
        'raw_ocr': {
            'analyzeResult': {
                'readResults': [{'lines': [{'text': 'Q1 x=4 ○', 'confidence': 0.95}, {'text': 'Q2 x=-3 △', 'confidence': 0.62}]}]
            }
        }
    })
    ocr_elapsed = time.perf_counter() - start
    analysis_start = time.perf_counter()
    client.post('/api/analysis/run', json={
        'student_id': 's-03',
        'normalized_ocr': replay['normalized_ocr'],
        'mode': 'live',
        'action': 'initial',
    })
    analysis_elapsed = time.perf_counter() - analysis_start
    return ocr_elapsed, analysis_elapsed


def p95(values: list[float]) -> float:
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(0.95 * (len(ordered) - 1))))
    return ordered[index]


def main() -> int:
    ocr_times, analysis_times = zip(*(measure() for _ in range(5)))
    total = [left + right for left, right in zip(ocr_times, analysis_times)]
    markdown = [
        '# Latency Eval',
        '',
        '| Stage | p50 | p95 |',
        '| --- | --- | --- |',
        f'| OCR normalize | {statistics.median(ocr_times):.3f}s | {p95(list(ocr_times)):.3f}s |',
        f'| Analysis | {statistics.median(analysis_times):.3f}s | {p95(list(analysis_times)):.3f}s |',
        f'| Total | {statistics.median(total):.3f}s | {p95(total):.3f}s |',
        '',
        'This is local app-path latency. Live Azure latency is tracked separately by smoke checks and should be rehearsed before the demo.'
    ]
    report = '\n'.join(markdown)
    target = REPO_ROOT / 'docs' / 'evals' / 'latency_eval.md'
    target.write_text(report)
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
