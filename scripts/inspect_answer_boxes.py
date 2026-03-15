#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.services.llm_sheet_ocr import _open_image, _regions_from_visible_questions  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print('usage: inspect_answer_boxes.py <image-path> <Q1,Q2,...>')
        return 1
    image_path = Path(sys.argv[1]).resolve()
    problem_nos = [part.strip().upper() for part in sys.argv[2].split(',') if part.strip()]
    image = _open_image(image_path)
    regions = _regions_from_visible_questions(image, problem_nos)
    output_dir = ROOT / 'data' / 'box-inspection' / image_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    payload = []
    for region in regions:
        draw.rectangle(region.row_box, outline=(90, 140, 220), width=5)
        draw.rectangle(region.work_box, outline=(80, 170, 90), width=5)
        draw.rectangle(region.final_box, outline=(220, 80, 80), width=5)
        draw.text((region.row_box[0] + 12, region.row_box[1] + 12), region.problem_no, fill=(20, 20, 20))
        payload.append(
            {
                'problem_no': region.problem_no,
                'row_box': region.row_box,
                'work_box': region.work_box,
                'final_box': region.final_box,
                'notes': region.notes,
            }
        )
    overlay_path = output_dir / 'overlay.png'
    json_path = output_dir / 'regions.json'
    overlay.save(overlay_path)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(json.dumps({'overlay': str(overlay_path.relative_to(ROOT)), 'regions': str(json_path.relative_to(ROOT)), 'count': len(payload)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
