#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'backend'))

from app.services.confirmation_tests import (  # noqa: E402
    PLAYWRIGHT_RENDERER,
    PRIMARY_SOURCE,
    build_manifest,
    build_selection_record,
    ensure_output_dir,
    filter_problem_rows,
    katex_asset_paths,
    load_with_fallback,
    render_answer_key_markdown,
    render_html,
    sanitize_test_id,
    select_balanced_problems,
    write_manifest_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate a printable confirmation test from Japanese math QA data.')
    parser.add_argument('--dataset-source', default='huggingface')
    parser.add_argument('--dataset-name', default=PRIMARY_SOURCE.name)
    parser.add_argument('--dataset-config', default=PRIMARY_SOURCE.config)
    parser.add_argument('--split', default=PRIMARY_SOURCE.split)
    parser.add_argument('--count', type=int, default=10)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--difficulty-min', type=int, default=1)
    parser.add_argument('--difficulty-max', type=int, default=3)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--with-answer-key', action='store_true')
    parser.add_argument('--test-id', required=True)
    parser.add_argument('--subject-include', action='append', default=[])
    parser.add_argument('--subject-exclude', action='append', default=[])
    parser.add_argument('--max-pages', type=int, default=3)
    parser.add_argument('--target-minutes', type=int, default=30)
    parser.add_argument('--template', default='default')
    parser.add_argument('--shuffle', action='store_true')
    parser.add_argument('--preview-only', action='store_true')
    parser.add_argument('--generated-at', default='')
    return parser.parse_args()


def paginate_problems(problems: list[Any], max_units_per_page: float = 4.2) -> list[list[Any]]:
    pages: list[list[Any]] = []
    current: list[Any] = []
    used = 0.0
    for problem in problems:
        units = max(0.95, len(problem.problem) / 180.0 + problem.level * 0.18)
        if current and used + units > max_units_per_page:
            pages.append(current)
            current = []
            used = 0.0
        current.append(problem)
        used += units
    if current:
        pages.append(current)
    return pages


def render_pdf_from_html(html_path: Path, pdf_path: Path, screenshot_path: Path | None = None) -> None:
    cmd = ['node', str(PLAYWRIGHT_RENDERER), str(html_path), str(pdf_path)]
    if screenshot_path is not None:
        cmd.append(str(screenshot_path))
    subprocess.run(cmd, check=True)


def normalize_preview_to_grayscale(image_path: Path) -> None:
    if not image_path.exists():
        return
    image = Image.open(image_path).convert('L')
    image.save(image_path)


def main() -> int:
    args = parse_args()
    if args.dataset_source != 'huggingface':
        raise SystemExit('Only --dataset-source huggingface is supported in this MVP extension.')

    output_dir = ensure_output_dir(Path(args.output_dir))
    test_id = sanitize_test_id(args.test_id)
    generated_at = args.generated_at or datetime.now(timezone.utc).isoformat()

    raw_rows, actual_source = load_with_fallback(args.dataset_name, args.dataset_config, args.split)
    filtered = filter_problem_rows(
        raw_rows,
        difficulty_min=args.difficulty_min,
        difficulty_max=args.difficulty_max,
        subject_include=args.subject_include,
        subject_exclude=args.subject_exclude,
    )
    selected = select_balanced_problems(filtered, args.count, args.seed)
    manifest = build_manifest(
        test_id=test_id,
        seed=args.seed,
        generated_at=generated_at,
        difficulty_min=args.difficulty_min,
        difficulty_max=args.difficulty_max,
        target_minutes=args.target_minutes,
        max_pages=args.max_pages,
        source=actual_source,
        rows=selected,
    )
    selection = build_selection_record(
        manifest,
        filters={
            'count': args.count,
            'difficulty_min': args.difficulty_min,
            'difficulty_max': args.difficulty_max,
            'subject_include': args.subject_include,
            'subject_exclude': args.subject_exclude,
            'max_pages': args.max_pages,
            'template': args.template,
            'shuffle': args.shuffle,
        },
    )
    write_manifest_bundle(output_dir, manifest, selection)

    question_pages = paginate_problems(manifest.problems)
    html_context = {
        'manifest': manifest,
        'question_pages': question_pages,
        'filled_answers': {},
        'katex': katex_asset_paths(),
    }
    confirmation_html = output_dir / 'preview.html'
    render_html('confirmation_test.html.j2', html_context, confirmation_html)

    answer_key_html = output_dir / 'answer_key.html'
    render_html('answer_key.html.j2', {'manifest': manifest, 'katex': katex_asset_paths()}, answer_key_html)
    render_answer_key_markdown(output_dir, manifest)

    if not args.preview_only:
        render_pdf_from_html(confirmation_html, output_dir / 'confirmation_test.pdf', output_dir / 'preview.png')
        normalize_preview_to_grayscale(output_dir / 'preview.png')
        if args.with_answer_key:
            render_pdf_from_html(answer_key_html, output_dir / 'answer_key.pdf')

    summary = {
        'test_id': manifest.test_id,
        'source_dataset': manifest.source_dataset,
        'source_config': manifest.source_config,
        'problem_count': manifest.problem_count,
        'pages_estimated': manifest.layout.estimated_question_pages + 1,
        'output_dir': str(output_dir),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
