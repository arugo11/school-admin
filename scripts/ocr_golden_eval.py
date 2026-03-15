#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'backend'))

from app.services.ocr_normalizer import normalize_ocr_result  # noqa: E402

RAW_DIR = REPO_ROOT / 'data' / 'raw_ocr'
GOLDEN_DIR = REPO_ROOT / 'data' / 'golden' / 'ocr'

CASE_TO_STUDENT = {
    'case-s03-signs': 's-03',
    'case-s02-steps': 's-02',
    'case-s05-fractions': 's-05',
    'case-s06-careless': 's-06',
    'case-s04-function': 's-04',
}


def compare(actual: dict, expected: dict) -> list[str]:
    diffs: list[str] = []
    if actual['ocr_confidence_summary'] != expected['ocr_confidence_summary']:
        diffs.append('ocr_confidence_summary mismatch')
    for idx, item in enumerate(actual['items']):
        if idx >= len(expected['items']):
            diffs.append(f'item count mismatch at {idx}')
            continue
        for field in ('problem_no', 'recognized_answer', 'teacher_marks', 'rewrite_detected', 'uncertainty'):
            if item[field] != expected['items'][idx][field]:
                diffs.append(f'item {idx} field {field} mismatch')
    return diffs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--update-golden', action='store_true')
    parser.add_argument('--write-doc', default='')
    args = parser.parse_args()

    rows: list[tuple[str, str, str]] = []
    for raw_path in sorted(RAW_DIR.glob('*.json')):
        fixture_id = raw_path.stem
        student_id = CASE_TO_STUDENT[fixture_id]
        actual = normalize_ocr_result(json.loads(raw_path.read_text()), student_id, f'{fixture_id}-img').model_dump()
        golden_path = GOLDEN_DIR / f'{fixture_id}.json'
        if args.update_golden or not golden_path.exists():
            golden_path.write_text(json.dumps(actual, ensure_ascii=False, indent=2))
        expected = json.loads(golden_path.read_text())
        diffs = compare(actual, expected)
        rows.append((fixture_id, 'pass' if not diffs else 'fail', '; '.join(diffs) or 'matches golden'))

    markdown = ['# OCR Golden Eval', '', '| Fixture | Result | Note |', '| --- | --- | --- |']
    markdown.extend(f'| {fixture} | {result} | {note} |' for fixture, result, note in rows)
    markdown.append('')
    markdown.append(f'Schema success rate: {sum(result == "pass" for _, result, _ in rows)}/{len(rows)}')
    report = '\n'.join(markdown)
    if args.write_doc:
        Path(args.write_doc).write_text(report)
    print(report)
    return 0 if all(result == 'pass' for _, result, _ in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
