# AOAI OCR Latency Experiment

Date: 2026-03-15

## Goal
Measure where the current live OCR path is losing throughput, using the current multimodal Azure OpenAI OCR implementation.

## Setup
- Backend: live OCR path via Azure OpenAI multimodal input
- Test image: `data/test/confirmation_test-3.jpg`
- Helper scripts:
  - `scripts/report_aoai_timings.py`
  - `/tmp/measure_aoai_direct.py` during this run

## Observed Results

### 1. Upload stage
- Measured from direct client probe.
- Result: `upload_status=200`, `0.006s`
- Interpretation: upload is not the bottleneck.

### 2. AOAI layout/read stages
Direct AOAI timing probe on `confirmation_test-3.jpg` did not complete successfully because the very first multimodal layout call exhausted its retry budget.

Observed sequence:
- attempt 1: `429`
- retry wait: `30s`
- attempt 2: `429`
- retry wait: `30s`
- attempt 3: `429`
- retry wait: `30s`
- attempt 4: `429`
- retry wait: `30s`
- attempt 5: `429`
- final result: failure before layout JSON was returned

So the layout pass alone consumed about `120s+` in retry waiting, before any downstream reading pass or analysis could start.

### 3. Backend log summary
From `scripts/report_aoai_timings.py` after this run:

```json
{
  "aoai_chat_success_count": 5,
  "aoai_chat_successes": [
    {"attempt": 4, "duration_ms": 3524.7},
    {"attempt": 3, "duration_ms": 4079.8},
    {"attempt": 3, "duration_ms": 3348.3},
    {"attempt": 3, "duration_ms": 2987.7},
    {"attempt": 3, "duration_ms": 4385.9}
  ],
  "retry_count": 10,
  "retry_seconds": [30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0],
  "ocr_stage_timings": [
    {"source_image_id": "img-98357e6effa4", "layout_ms": 96940.0, "reading_ms": 64994.5, "total_ms": 162190.2},
    {"source_image_id": "img-82f30c3f2683", "layout_ms": 64545.6, "reading_ms": 63618.1, "total_ms": 128279.8}
  ]
}
```

Interpretation:
- When Azure OpenAI accepts the request, actual service time is roughly `3.0s - 4.4s`.
- But one live OCR image still ballooned to:
  - `layout 96.9s + reading 65.0s = total 162.2s`
  - `layout 64.5s + reading 63.6s = total 128.3s`
- The real throughput collapse is caused by retry windows, not by model compute alone.

## Breakdown Conclusion
Current throughput bottleneck order:
1. Azure OpenAI `429` rate limiting
2. OCR architecture making multiple AOAI calls per live run (`layout` then `reading`, plus later `analysis`)
3. Large multimodal payload size
4. Multi-image uploads compounding the call count

Not primary bottlenecks:
- local upload
- bbox detection / cropping
- SQLite / file persistence
- frontend rendering

## Recommendation
- Short term: keep OCR status explicit and fail fast to a readable retry state instead of leaving users on a long spinner.
- Medium term: reduce cloud OCR call count or move OCR off AOAI.
- Best next experiment: compare a local OCR backend that avoids AOAI throttling entirely.
