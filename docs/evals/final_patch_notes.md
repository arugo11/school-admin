# Final Patch Notes

Date: 2026-03-15

## Scope
Only small final-demo safety fixes were applied during the final E2E pass.
No API contract or architecture change was introduced.

## Patch 1. Azure CLI Runtime Key Fallback
### Why
- Live browser E2E initially failed because local app runtime did not have Azure keys in process env.
- Azure smoke itself was green via Azure CLI, so the safest fix was to let the runtime reuse the same existing-resource key lookup path.

### Files
- `backend/app/core/azure_runtime_keys.py`
- `backend/app/clients/vision.py`
- `backend/app/clients/azure_openai.py`

### Result
- Live OCR and live AOAI became executable from the local app without requiring secrets to be printed or hard-coded.

## Patch 2. Stable Demo Context Callbacks
### Why
- Student detail page was re-fetching repeatedly and caused visible instability before live upload.

### File
- `frontend/src/lib/demo-context.tsx`

### Result
- Browser happy path stabilized and three consecutive live + three consecutive replay runs completed.

## Patch 3. Human-Readable Upload Error Message
### Why
- Oversized upload error box showed raw JSON, which looked unfinished in the booth UX.

### File
- `frontend/src/lib/api.ts`

### Result
- Error box now shows `Image too large. Keep it under 5MB for demo reliability.` instead of raw JSON.
- Evidence: `docs/evals/evidence/final/upload-oversized-error-final.png`

## Validation Reruns After Final Patch
- frontend `npm test`: pass
- frontend `npm run build`: pass
- live happy path x1: pass
- replay happy path x1: pass
- narrated 60s x1: pass (`47.229 s`)
- narrated 120s x1: pass (`88.623 s`)
- evidence:
  - `docs/evals/evidence/final/post-patch-happy-runs-final.json`
  - `docs/evals/evidence/final/narrated-pass-runs-final.json`
