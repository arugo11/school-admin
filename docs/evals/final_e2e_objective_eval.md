# Final E2E Objective Eval

Date: 2026-03-15

## Execution Environment
- Backend: FastAPI on `127.0.0.1:8010`
- Frontend: Vite dev server on `127.0.0.1:4174`
- Browser automation: Playwright with system Chrome (`/usr/bin/google-chrome`)
- Live OCR: Azure Vision Read `schooladminocr23088`
- Live LLM: Azure OpenAI `sitcopilotaoai23088` / deployment `sit-copilot-demo-chat`
- Primary confirmation test set: `ct-exhibit-main`

## Live / Replay Summary
| Case Group | Result | Evidence |
| --- | --- | --- |
| live happy path x3 consecutive | pass | `docs/evals/evidence/final/browser-flow-runs.json` |
| replay happy path x3 consecutive | pass | `docs/evals/evidence/final/browser-flow-runs.json` |
| realistic exhibit path | pass | `docs/evals/confirmation_test_generation_eval.md`, `docs/evals/confirmation_test_ocr_eval.md` |
| failure / fallback matrix | pass-with-warnings | fresh injected results below + `docs/evals/evidence/final/upload-oversized-error-final.png` |
| blocking issue present? | no | after final small patches |

## Case A. Live Happy Path
Three consecutive browser runs passed on the full path:
`students -> spotlight student -> upload -> OCR review -> analysis -> homework review -> approve -> dashboard`

| Run | Result | Total |
| --- | --- | --- |
| live-1 | pass | 3945 ms |
| live-2 | pass | 3883 ms |
| live-3 | pass | 4049 ms |

Fresh post-patch safety rerun:
- live rerun: pass, `6844 ms`
- evidence: `docs/evals/evidence/final/post-patch-happy-runs-final.json`

Observed checkpoints in all three runs:
- students
- student-detail
- upload
- ocr-review
- analysis
- homework-review
- demo-dashboard

## Case B. Replay Happy Path
Three consecutive browser runs passed on the same visible story with seeded snapshot replay.

| Run | Result | Total |
| --- | --- | --- |
| replay-1 | pass | 883 ms |
| replay-2 | pass | 866 ms |
| replay-3 | pass | 850 ms |

Fresh post-patch safety rerun:
- replay rerun: pass, `370 ms`
- evidence: `docs/evals/evidence/final/post-patch-happy-runs-final.json`

Replay affordance remained understandable:
- student detail offers `Replay で開始`
- upload screen offers `seeded snapshot を使う`
- completion screen clearly shows `Replay Mode`

## Case C. Realistic Exhibit Path
### Confirmation Test Generation
Fresh regeneration passed for a new safety set:
- `test_id=ct-exhibit-main-finalcheck`
- source dataset: `appier-ai-research/Multilingual-MATH-500` / `Japanese` / `test`
- problem count: `6`
- estimated pages: `3`
- output: `data/generated/tests/exhibit-main-finalcheck`

### A4 / Layout / Traceability Check
- manifest includes stable `test_id`, dataset provenance, problem IDs, `catalog_problem_no`, answer key, and source unique IDs.
- `ct-exhibit-main` manifest sample confirms `problem_count=6` and stable problem mapping.
- generated files exist: `confirmation_test.pdf`, `answer_key.pdf`, `answer_key.md`, `manifest.json`, `selected_problems.json`, `preview.html`, `preview.png`

### OCR -> Analysis -> Approval Integration
Fresh confirmation-test OCR eval passed:

| Sample | Result | Note |
| --- | --- | --- |
| sample-correct | pass | `test_id=ct-exhibit-main`, `mapped=6/6`, `homework=4` |
| sample-mixed | pass | `test_id=ct-exhibit-main`, `mapped=6/6`, `homework=3` |
| sample-partial | pass | `test_id=ct-exhibit-main`, `mapped=6/6`, `homework=3` |

Conclusion:
- generated confirmation test is traceable by `test_id`
- OCR survives into normalized JSON
- analysis can use manifest context
- approval still completes on the existing path

## Case D. Failure / Fallback Matrix
Fresh failure injection results:

| Case | Result | Evidence |
| --- | --- | --- |
| oversized image | pass | API returned `400`; UI showed friendly message and replay banner |
| malformed OCR result | pass | `/api/ocr/normalize` returned `200`, preserved uncertainty, `test_id=ct-exhibit-main` |
| OpenAI failure fallback | pass | forced OpenAI exception produced `fallback_used=true` with catalog-constrained homework |
| live OCR failure simulation | warning | forced Vision exception returned `500`; operator must switch to replay |
| network instability operational fallback | pass | replay path remained reachable and completed x3 |

Fresh failure details:
- oversized image:
  - status `400`
  - message: `Image too large. Keep it under 5MB for demo reliability.`
  - UI evidence: `docs/evals/evidence/final/upload-oversized-error-final.png`
- malformed OCR:
  - status `200`
  - `low_confidence_count=1`
  - first answer preserved as `???`
  - `test_id=ct-exhibit-main`
- OpenAI failure fallback:
  - status `200`
  - `fallback_used=true`
  - `source_mode=live`
  - safe homework: `A-02, A-05, A-07`
- live OCR failure simulation:
  - status `500`
  - replay immediately after still returned `200` and `source_mode=replay`

## Latency Snapshot
### Browser E2E
- live x3: `3945 / 3883 / 4049 ms`
- replay x3: `883 / 866 / 850 ms`
- post-patch live rerun: `6844 ms`
- post-patch replay rerun: `370 ms`

### Live OCR + AOAI Smoke
- Vision smoke: `5.21 s`
- AOAI smoke: `0.58 s`

### Narrated Rehearsal Timing
- 60-second replay script: `47.229 s`
- 120-second live script: `88.623 s`

## Blocking Issue Status
- No blocking issue remains after final minimal patches.
- The demo is operationally safe if run with this rule:
  - use live mode only after smoke passes
  - switch to replay immediately on OCR/AOAI trouble

## Residual Objective Risks
- live Vision failure still bubbles up as a backend `500`; the UX fallback is operational rather than seamless auto-recovery.
- OCR review on typed/generated samples can look sparse, so the emotional peak depends more on analysis + approval than on the OCR screen itself.
- same-day AOAI rate limiting was observed once, so replay remains essential.
