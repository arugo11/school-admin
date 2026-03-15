#!/usr/bin/env python3
from __future__ import annotations

import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'backend'))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


client = TestClient(app)


def run_story(mode: str) -> float:
    started = time.perf_counter()
    students = client.get('/api/students').json()
    assert len(students) == 6
    student = next(item for item in students if item['student_id'] == 's-03')
    replay = client.get(f"/api/demo/{student['student_id']}/replay").json()
    normalized = replay['normalized_ocr']
    analysis = client.post('/api/analysis/run', json={
        'student_id': student['student_id'],
        'normalized_ocr': normalized,
        'mode': mode,
        'action': 'initial',
    }).json()
    problems = [item['problem_no'] for item in analysis['recommended_homework']]
    approved = client.post('/api/homework/approve', json={
        'student_id': student['student_id'],
        'approved_problem_nos': problems[:-1],
        'removed_problem_nos': problems[-1:],
        'approval_mode': f'{mode}-story-pass',
        'teacher_comment': 'story-pass',
        'approved_at': datetime.now(timezone.utc).isoformat(),
    })
    assert approved.status_code == 200
    return time.perf_counter() - started


def main() -> int:
    replay_runs = [run_story('replay') for _ in range(3)]
    live_runs = [run_story('live') for _ in range(3)]
    markdown = [
        '# E2E Demo Eval',
        '',
        '| Mode | Runs | Median | Max | Result |',
        '| --- | --- | --- | --- | --- |',
        f"| replay | 3 | {statistics.median(replay_runs):.2f}s | {max(replay_runs):.2f}s | pass |",
        f"| live-fallback | 3 | {statistics.median(live_runs):.2f}s | {max(live_runs):.2f}s | pass |",
        '',
        'Story pass checklist:',
        '- 6人一覧を取得',
        '- 主役生徒 s-03 を選択',
        '- replay seeded OCR を取得',
        '- analysis を表示',
        '- 問題を1問外して承認',
        '- 3回連続成功',
        '',
        'Manual narrated 2-minute UI pass still needs demo-day confirmation in browser.'
    ]
    report = '\n'.join(markdown)
    target = REPO_ROOT / 'docs' / 'evals' / 'e2e_demo_eval.md'
    target.write_text(report)
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
