#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / '.demo-runtime' / 'backend.log'

SUCCESS_RE = re.compile(r'AOAI chat success: attempt=(\d+) duration_ms=([0-9.]+)')
RETRY_RE = re.compile(r'AOAI chat retrying after ([0-9.]+)s')
OCR_STAGE_RE = re.compile(r'OCR stage timing: source_image_id=(\S+) layout_ms=([0-9.]+|None) reading_ms=([0-9.]+|None) total_ms=([0-9.]+|None)')
ANALYSIS_RE = re.compile(r'Analysis timing: student_id=(\S+) mode=(\S+) elapsed_ms=([0-9.]+)')


def main() -> int:
    text = LOG_PATH.read_text(errors='ignore') if LOG_PATH.exists() else ''
    successes = [{'attempt': int(m.group(1)), 'duration_ms': float(m.group(2))} for m in SUCCESS_RE.finditer(text)]
    retries = [float(m.group(1)) for m in RETRY_RE.finditer(text)]
    ocr_stages = []
    for m in OCR_STAGE_RE.finditer(text):
        def parse(value: str):
            return None if value == 'None' else float(value)
        ocr_stages.append({'source_image_id': m.group(1), 'layout_ms': parse(m.group(2)), 'reading_ms': parse(m.group(3)), 'total_ms': parse(m.group(4))})
    analyses = [{'student_id': m.group(1), 'mode': m.group(2), 'elapsed_ms': float(m.group(3))} for m in ANALYSIS_RE.finditer(text)]
    payload = {
        'log_path': str(LOG_PATH.relative_to(ROOT)),
        'aoai_chat_success_count': len(successes),
        'aoai_chat_successes': successes[-10:],
        'retry_count': len(retries),
        'retry_seconds': retries[-10:],
        'ocr_stage_timings': ocr_stages[-10:],
        'analysis_timings': analyses[-10:],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
