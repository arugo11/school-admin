#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'backend'))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.confirmation_tests import katex_asset_paths, load_manifest_from_dir, render_html  # noqa: E402

RENDERER = REPO_ROOT / 'scripts' / 'render_html_to_pdf.mjs'
client = TestClient(app)


def _run_az(*args: str) -> str:
    result = subprocess.run(['az', *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def resolve_keys(use_az_cli: bool) -> tuple[str, str]:
    endpoint = os.getenv('AZURE_VISION_ENDPOINT', 'https://japaneast.api.cognitive.microsoft.com/')
    key = os.getenv('AZURE_VISION_KEY')
    if not key and use_az_cli:
        key = _run_az('cognitiveservices', 'account', 'keys', 'list', '-g', 'school-admin-precheck-rg', '-n', 'schooladminocr23088', '--query', 'key1', '-o', 'tsv')
    if not key:
        raise RuntimeError('AZURE_VISION_KEY is not configured')
    return endpoint, key


def render_pdf(html_path: Path, pdf_path: Path, screenshot_path: Path) -> None:
    subprocess.run(['node', str(RENDERER), str(html_path), str(pdf_path), str(screenshot_path)], check=True, cwd=REPO_ROOT)


def render_filled_answer_sheet(test_dir: Path, manifest: Any, sample_name: str, filled_answers: dict[int, Any]) -> Path:
    html_path = test_dir / f'{sample_name}.html'
    pdf_path = test_dir / f'{sample_name}.pdf'
    png_path = test_dir / f'{sample_name}.png'
    render_html(
        'confirmation_test.html.j2',
        {
            'manifest': manifest,
            'question_pages': [],
            'filled_answers': filled_answers,
            'katex': katex_asset_paths(),
        },
        html_path,
    )
    render_pdf(html_path, pdf_path, png_path)
    return pdf_path


def build_samples(manifest: Any) -> list[tuple[str, dict[int, str]]]:
    answers = {problem.display_no: {"work": f"計算 {problem.answer}", "final": problem.answer} for problem in manifest.problems}
    mixed = {
        display_no: {"work": f"試行 {value['final']}", "final": (value["final"] if display_no % 2 else "0")}
        for display_no, value in answers.items()
    }
    partial = {
        display_no: {"work": f"途中 {value['final']}", "final": (value["final"] if display_no <= 3 else "")}
        for display_no, value in answers.items()
    }
    return [('sample-correct', answers), ('sample-mixed', mixed), ('sample-partial', partial)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--test-dir', required=True)
    parser.add_argument('--use-az-cli', action='store_true')
    parser.add_argument('--write-doc', default='docs/evals/confirmation_test_ocr_eval.md')
    args = parser.parse_args()

    test_dir = Path(args.test_dir)
    manifest = load_manifest_from_dir(test_dir)
    endpoint, key = resolve_keys(args.use_az_cli)
    settings.azure_vision_endpoint = endpoint
    settings.azure_vision_key = key

    rows: list[tuple[str, str, str]] = []
    expected = {f'Q{problem.display_no}' for problem in manifest.problems}

    for sample_name, filled_answers in build_samples(manifest):
        pdf_path = render_filled_answer_sheet(test_dir, manifest, sample_name, filled_answers)
        upload_response = client.post(
            '/api/uploads',
            data={'student_id': 's-03', 'mode': 'live'},
            files={'file': (pdf_path.name, pdf_path.read_bytes(), 'application/pdf')},
        )
        upload_payload = upload_response.json()
        ocr_response = client.post(
            '/api/ocr/run',
            json={'student_id': 's-03', 'source_image_id': upload_payload['source_image_id'], 'mode': 'live'},
        )
        normalized = ocr_response.json()['normalized_ocr']
        analysis_response = client.post(
            '/api/analysis/run',
            json={
                'student_id': 's-03',
                'normalized_ocr': normalized,
                'mode': 'live',
                'action': 'initial',
            },
        )
        approval_response = client.post(
            '/api/homework/approve',
            json={
                'student_id': 's-03',
                'approved_problem_nos': [item['problem_no'] for item in analysis_response.json()['recommended_homework'][:2]],
                'removed_problem_nos': [item['problem_no'] for item in analysis_response.json()['recommended_homework'][2:3]],
                'approval_mode': f'{sample_name}-eval',
                'teacher_comment': 'confirmation-test-eval',
                'approved_at': datetime.now(timezone.utc).isoformat(),
            },
        )
        mapped = {item['problem_no'] for item in normalized['items']}
        result = 'pass' if normalized.get('test_id') == manifest.test_id and upload_response.status_code == 200 and ocr_response.status_code == 200 and len(mapped & expected) >= min(3, len(expected)) and analysis_response.status_code == 200 and approval_response.status_code == 200 else 'fail'
        note = f"test_id={normalized.get('test_id')}, mapped={len(mapped & expected)}/{len(expected)}, upload={upload_response.status_code}, ocr={ocr_response.status_code}, homework={len(analysis_response.json()['recommended_homework'])}"
        rows.append((sample_name, result, note))

    markdown = ['# Confirmation Test OCR Eval', '', '| Sample | Result | Note |', '| --- | --- | --- |']
    markdown.extend(f'| {sample} | {result} | {note} |' for sample, result, note in rows)
    markdown.append('')
    markdown.append('All samples used the generated answer-sheet-only PDF and the existing /uploads -> /ocr/run -> /analysis/run -> /homework/approve API path.')
    Path(args.write_doc).write_text('\n'.join(markdown), encoding='utf-8')
    print('\n'.join(markdown))
    return 0 if all(result == 'pass' for _, result, _ in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
