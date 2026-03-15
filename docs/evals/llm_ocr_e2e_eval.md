# LLM OCR E2E Eval

Date: 2026-03-15

## Scope
- Replace live OCR path so `/api/ocr/run` uses multimodal Azure OpenAI image interpretation instead of Azure Vision Read.
- Keep downstream flow unchanged: `upload -> OCR review -> analysis -> homework approval`.
- Re-check live behavior on:
  - `data/test/confirmation_test-3.jpg`
  - `data/test/confirmation_test-4.jpg`

## Architecture Change
- Live OCR entrypoint now calls `extract_llm_ocr_document(...)` from `backend/app/services/llm_sheet_ocr.py`.
- The service performs two LLM-backed steps:
  1. layout pass on the full image
  2. reading pass on cropped `計算過程` / `最終解答` regions
- No Azure Vision fallback remains in the live OCR happy path.
- `raw_ocr` returned by `/api/ocr/run` is now an LLM OCR payload/debug object, not Vision output.

## Code Paths
- `backend/app/api/routes.py`
- `backend/app/clients/azure_openai.py`
- `backend/app/services/llm_sheet_ocr.py`
- `backend/tests/test_api.py`

## Focused Validation
- `pytest backend/tests/test_api.py::test_ocr_run_uses_llm_ocr_for_confirmation_test_image backend/tests/test_api.py::test_ocr_run_returns_503_when_llm_ocr_is_rate_limited -q`
- Result: `2 passed`

## Live OCR Evidence

### 1. `confirmation_test-3.jpg`
- Upload + live OCR succeeded.
- OCR artifact:
  - `data/ocr_debug/img-bda15b3a2450.json`
- Backend log evidence:
  - `OCR debug saved: source_image_id=img-bda15b3a2450 test_id=ct-exhibit-main items=4`
- Extracted items:
  - `Q1 final_answer=2`
  - `Q2 final_answer=2`
  - `Q3 final_answer=1/\\sqrt2`
  - `Q4 final_answer=X`
- Extracted `work_text` is present for Q1-Q3.

### 2. `confirmation_test-3.jpg` + `confirmation_test-4.jpg`
- The full confirmation test was captured as two images and merged through the live LLM OCR route.
- OCR artifact:
  - `data/ocr_debug/batch-img-32a2b77f42c3-2.json`
- Backend log evidence:
  - `OCR debug saved: source_image_id=batch-img-32a2b77f42c3-2 test_id=ct-exhibit-main items=6`
- Extracted items show both images contributed:
  - `Q1-Q4` from `data/uploads/img-32a2b77f42c3.jpg`
  - `Q5-Q6` from `data/uploads/img-037afb74b8bb.jpg`
- Key extracted final answers:
  - `Q1 2`
  - `Q2 2`
  - `Q3 \\sqrt2`
  - `Q4 X`
  - `Q5 1/10`
  - `Q6 0`

## Downstream E2E Evidence
- Analysis and approval succeeded from the merged live OCR document.
- Backend log evidence:
  - `POST /api/analysis/run HTTP/1.1" 200 OK`
  - `POST /api/homework/approve HTTP/1.1" 200 OK`
- This confirms the new LLM OCR payload remained compatible with analysis and approval.

## Known Limits Observed
- Azure OpenAI multimodal requests were intermittently rate-limited with `429 Too Many Requests`.
- To reduce demo breakage:
  - OCR image payload size was reduced
  - `/api/ocr/run` now converts OCR-side `429` exhaustion into a user-readable `503` with retry guidance
- Residual risk:
  - repeated back-to-back live OCR probes can still be slowed by AOAI throttling
  - this is now surfaced clearly instead of failing as an opaque `500`

## Judgment
- Live OCR path replacement: pass
- Confirmation-test extraction from image input: pass
- `data/test` image verification: pass
  - `confirmation_test-3.jpg` verified directly
  - `confirmation_test-4.jpg` verified as part of the two-image full-sheet live OCR run
- Analysis compatibility after OCR swap: pass
- Approval compatibility after OCR swap: pass
