#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'backend'))

from app.services.analysis import AnalysisService  # noqa: E402
from app.services.data_store import load_catalog, load_students  # noqa: E402
from app.services.ocr_normalizer import normalize_ocr_result  # noqa: E402

RAW_DIR = REPO_ROOT / 'data' / 'raw_ocr'
GOLDEN_DIR = REPO_ROOT / 'data' / 'golden' / 'analysis'
CASE_TO_STUDENT = {
    'case-s03-signs': 's-03',
    'case-s02-steps': 's-02',
    'case-s05-fractions': 's-05',
    'case-s06-careless': 's-06',
    'case-s04-function': 's-04',
}


def student_map():
    return {student.student_id: student for student in load_students()}


def compare(actual: dict, expected: dict) -> list[str]:
    diffs: list[str] = []
    for field in ('weak_units', 'error_patterns', 'homework_load_fit'):
        if actual[field] != expected[field]:
            diffs.append(f'{field} mismatch')
    actual_problem_nos = [item['problem_no'] for item in actual['recommended_homework']]
    expected_problem_nos = [item['problem_no'] for item in expected['recommended_homework']]
    if actual_problem_nos != expected_problem_nos:
        diffs.append('recommended_homework mismatch')
    return diffs


async def build_analysis(fixture_id: str) -> dict:
    student_id = CASE_TO_STUDENT[fixture_id]
    raw = json.loads((RAW_DIR / f'{fixture_id}.json').read_text())
    normalized = normalize_ocr_result(raw, student_id, f'{fixture_id}-img')
    student = student_map()[student_id]
    result = await AnalysisService().run(student, normalized, load_catalog(), mode='live')
    return result.model_dump()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--update-golden', action='store_true')
    parser.add_argument('--write-doc', default='')
    args = parser.parse_args()

    rows: list[tuple[str, str, str]] = []
    catalog_problem_nos = {problem.problem_no for problem in load_catalog()}
    for raw_path in sorted(RAW_DIR.glob('*.json')):
        fixture_id = raw_path.stem
        actual = asyncio.run(build_analysis(fixture_id))
        golden_path = GOLDEN_DIR / f'{fixture_id}.json'
        if args.update_golden or not golden_path.exists():
            golden_path.write_text(json.dumps(actual, ensure_ascii=False, indent=2))
        expected = json.loads(golden_path.read_text())
        diffs = compare(actual, expected)
        schema_ok = set(item['problem_no'] for item in actual['recommended_homework']) <= catalog_problem_nos and bool(actual['analysis_rationale'])
        status = 'pass' if (not diffs and schema_ok) else 'fail'
        note = '; '.join(diffs) if diffs else 'schema ok'
        rows.append((fixture_id, status, note))

    markdown = ['# Analysis Schema Eval', '', '| Fixture | Result | Note |', '| --- | --- | --- |']
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
