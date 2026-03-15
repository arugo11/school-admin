#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from datasets import load_dataset


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / 'data' / 'generated' / 'datasets'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Export a Hugging Face dataset split to a local CSV file.')
    parser.add_argument('--dataset-name', required=True)
    parser.add_argument('--dataset-config', default=None)
    parser.add_argument('--split', default='train')
    parser.add_argument('--output', default='')
    parser.add_argument('--limit', type=int, default=0, help='Optional max row count. 0 exports the full split.')
    parser.add_argument('--only-valid', action='store_true', help='If the dataset has an is_valid column, export only valid rows.')
    return parser.parse_args()


def default_output_path(dataset_name: str, split: str) -> Path:
    safe_name = dataset_name.replace('/', '__')
    return DEFAULT_OUTPUT_ROOT / safe_name / f'{split}.csv'


def serialize_value(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float, str)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def main() -> int:
    args = parse_args()
    output_path = Path(args.output) if args.output else default_output_path(args.dataset_name, args.split)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(args.dataset_name, args.dataset_config, split=args.split)
    column_names = list(dataset.column_names)

    rows_written = 0
    with output_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=column_names)
        writer.writeheader()
        for row in dataset:
            if args.only_valid and 'is_valid' in row and not bool(row['is_valid']):
                continue
            writer.writerow({column: serialize_value(row.get(column)) for column in column_names})
            rows_written += 1
            if args.limit and rows_written >= args.limit:
                break

    summary = {
        'dataset_name': args.dataset_name,
        'dataset_config': args.dataset_config,
        'split': args.split,
        'rows_written': rows_written,
        'output': str(output_path),
        'only_valid': args.only_valid,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())