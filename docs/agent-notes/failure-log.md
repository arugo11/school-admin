# Agent Failure Log

## 2026-03-15 Confirmation Test Generation Eval
- What failed: `scripts/confirmation_test_generation_eval.py` marked same-seed PDF reproducibility as fail.
- Evidence: `selected_problems.json` matched, but `confirmation_test.pdf` binary hashes differed across two same-seed runs.
- Current root-cause hypothesis: Chromium PDF output includes run-specific metadata, so raw binary hash is too strict for "same content" validation.
- Next changed approach: compare deterministic `preview.html` / selected problems instead of raw PDF bytes, and document the PDF metadata caveat in the eval note.

## 2026-03-15 Final E2E Smoke Command
- What failed: two shell probes for env/replay state failed immediately with `/bin/bash: python: command not found`.
- Evidence: local shell returned exit code 127 twice when using bare `python`.
- Current root-cause hypothesis: this environment exposes `python3` and the project venv, but not a system `python` shim.
- Next changed approach: switch smoke helper commands to `python3` or activate `.venv` before invoking Python-based checks.

## 2026-03-15 Final E2E Error Message Patch
- What failed: the upload error box still showed raw JSON after the first frontend parsing patch.
- Evidence: browser check on `upload-oversized-error-postpatch.png` still rendered `{\"detail\":\"Image too large. Keep it under 5MB for demo reliability.\"}`.
- Current root-cause hypothesis: the new code throws inside the `try` block, then its own `catch` falls back to the original raw text path.
- Next changed approach: parse JSON into a temporary variable first, then throw once outside the parsing `try/catch`.

## 2026-03-15 Confirmation Test OCR Normalization
- What failed: confirmation test answer sheets were analyzed as if all answers were unreadable.
- Evidence: raw Vision OCR for `sample-correct.png` and `sample-correct.pdf` contained answers like `2`, `\\cot x`, `6`, `-2 + 7i`, `4`, `40_9`, but normalized output still set every `recognized_answer` to `unknown`.
- Current root-cause hypothesis: the normalizer only handles `Q1 answer` on a single OCR line, while the confirmation test answer sheet produces separate lines for the question label and the answer.
- Next changed approach: add confirmation-test-aware grouping that pairs a `Qn` line with its nearby answer line(s), and emit OCR debug artifacts so we can verify the mapping.

## 2026-03-15 qa_verify_10k_test generation filter
- What failed: confirmation test regeneration from `team-victory/qa_verify_10k_test` returned `available=0` twice for exhibit-main and exhibit-backup.
- Evidence: `scripts/generate_confirmation_test.py` raised `ValueError: Not enough problems after filtering: requested=6, available=0` on both seeds.
- Current root-cause hypothesis: dataset rows use `difficulty` instead of `level`, so normalization defaulted all rows to level 3 and the requested difficulty range filtered everything out.
- Next changed approach: map dataset `difficulty` into the normalized `level` field and rerun generation before any further retries.

## 2026-03-15 Confirmation Test Box OCR Row Detection
- What failed: confirmation-test answer-sheet crops missed `Q5`, and a later patch shrank all row crops to ~8px height so every answer became unreadable.
- Evidence: `data/ocr_debug/img-3acedfe73c35.json` had no `Q5` mapping; `data/ocr_debug/img-c647f2bbb3d2.json` showed `row_box` heights collapsing because help lines were treated as question labels.
- Current root-cause hypothesis: relying on `Qn` label OCR is too brittle for this sheet, and `_label_lines` was accidentally parsing `CT-...-Qxx` help text as the same label signal.
- Next changed approach: anchor confirmation-test rows on the printed `CT-...-Qxx` help lines, infer missing label rows from their vertical spacing, and explicitly exclude help lines from label detection.

## 2026-03-15 LLM OCR live probe latency / 429
- What failed: live multimodal OCR probes against `data/test/confirmation_test-3.jpg` stalled for a long time and previously hit `429 Too Many Requests` before returning a usable OCR result.
- Evidence: first probe raised `httpx.HTTPStatusError: 429`; later probes stayed in the OCR call for tens of seconds even after image downscaling and a lighter layout pass.
- Current root-cause hypothesis: the multimodal request payload is still too large and repeated probes amplified AOAI throttling.
- Next changed approach: reduce multimodal payload further by shrinking contact sheets / max tokens, add OCR timing visibility, and rerun a single clean probe only.

## 2026-03-15 LLM OCR live E2E 429 during final verification
- What failed: Live E2E on `confirmation_test-3.jpg` / `confirmation_test-4.jpg` intermittently stalled or returned `500` because the underlying AOAI multimodal OCR call exhausted its retry budget on `429 Too Many Requests`.
- Evidence: `.demo-runtime/backend.log` showed repeated `AOAI chat HTTP error ... 429` lines and `POST /api/ocr/run` returning `500` after attempt 5; at the same time, background pytest and probe processes were still active.
- Current root-cause hypothesis: verification traffic itself was amplifying throttling, so sequential OCR requests were competing with stale live tests instead of measuring the real single-user path.
- Next changed approach: stop all background OCR/probe processes, wait for the throttle window to clear, then rerun one image at a time with no competing AOAI traffic and record the resulting artifacts.

## 2026-03-15 DeepSeek-OCR local inference on RTX 5070 Ti
- What failed: direct local DeepSeek-OCR inference did not complete successfully on the first two implementation attempts.
- Evidence: full-precision load hit CUDA OOM during `.to(torch.bfloat16)`; 8bit quantized run progressed further but failed inside bitsandbytes with `RuntimeError: Only two or three dimensional matrices are supported for argument A` during the vision branch.
- Current root-cause hypothesis: the model can fit only with offload/quantization on this GPU, but the current bitsandbytes path is incompatible with DeepSeek-OCR's vision encoder execution.
- Next changed approach: try a CPU-offload / mixed placement run to evaluate stability and latency without relying on the broken 8bit path.
