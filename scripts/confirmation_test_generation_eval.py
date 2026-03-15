#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / 'scripts' / 'generate_confirmation_test.py'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_generate(output_dir: Path, seed: int, test_id: str) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    subprocess.run([
        sys.executable, str(GENERATOR),
        '--dataset-source', 'huggingface',
        '--dataset-name', 'team-victory/qa_verify_10k_test',
        '--split', 'train',
        '--count', '6',
        '--seed', str(seed),
        '--difficulty-min', '1',
        '--difficulty-max', '2',
        '--output-dir', str(output_dir),
        '--with-answer-key',
        '--test-id', test_id,
        '--generated-at', '2026-03-15T18:30:00+09:00',
    ], check=True, cwd=REPO_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--write-doc', default='docs/evals/confirmation_test_generation_eval.md')
    args = parser.parse_args()

    base = REPO_ROOT / 'data' / 'generated' / 'tests'
    same_a = base / 'eval-same-a'
    same_b = base / 'eval-same-b'
    diff_b = base / 'eval-different-b'
    run_generate(same_a, 111, 'ct-eval-same')
    run_generate(same_b, 111, 'ct-eval-same')
    run_generate(diff_b, 222, 'ct-eval-different')

    selected_same = sha256(same_a / 'selected_problems.json') == sha256(same_b / 'selected_problems.json')
    html_same = sha256(same_a / 'preview.html') == sha256(same_b / 'preview.html')
    pdf_same = sha256(same_a / 'confirmation_test.pdf') == sha256(same_b / 'confirmation_test.pdf')
    selected_diff = sha256(same_a / 'selected_problems.json') != sha256(diff_b / 'selected_problems.json')

    manifest = json.loads((same_a / 'manifest.json').read_text())
    files_required = ['confirmation_test.pdf', 'answer_key.pdf', 'answer_key.md', 'manifest.json', 'selected_problems.json', 'preview.html']
    files_ok = all((same_a / file_name).exists() for file_name in files_required)

    markdown = [
        '# Confirmation Test Generation Eval',
        '',
        '| Check | Result | Note |',
        '| --- | --- | --- |',
        f"| same seed selected_problems reproducible | {'pass' if selected_same else 'fail'} | seed=111 |",
        f"| same seed rendered HTML reproducible | {'pass' if html_same else 'fail'} | fixed generated_at used |",
        f"| same seed PDF binary reproducible | {'warning' if not pdf_same and html_same else ('pass' if pdf_same else 'fail')} | Chromium embeds print metadata |",
        f"| different seed changes selection | {'pass' if selected_diff else 'fail'} | 111 vs 222 |",
        f"| required artifacts exist | {'pass' if files_ok else 'fail'} | {', '.join(files_required)} |",
        f"| manifest problem_count matches | {'pass' if manifest['problem_count'] == len(manifest['problems']) else 'fail'} | count={manifest['problem_count']} |",
        '',
        'Primary dataset source used: `team-victory/qa_verify_10k_test` / `train`.',
        'Layout default for exhibit eval: 6 questions, 2 question pages + 1 answer sheet page.',
    ]
    Path(args.write_doc).write_text('\n'.join(markdown), encoding='utf-8')
    print('\n'.join(markdown))
    return 0 if all([selected_same, html_same, selected_diff, files_ok, manifest['problem_count'] == len(manifest['problems'])]) else 1


if __name__ == '__main__':
    raise SystemExit(main())
