# Decision Log

## 2026-03-15
- Chose `minimal fresh implementation` after deeper scan found no reusable app code.
- Selected backend stack: `FastAPI + Pydantic + SQLite/files` to keep schema validation and local persistence simple.
- Selected frontend stack: `Vite + React + TypeScript` for a fast local iPad-friendly UI.
- Added `live` and `replay` modes as first-class paths so the demo can continue if Azure calls degrade.
- Treat OCR-derived `teacher_marks` and `rewrite_detected` as best-effort heuristics only.
- Added confirmation-test generation as an extension layer rather than changing the existing MVP path.
- Adopted primary dataset source: `appier-ai-research/Multilingual-MATH-500` with config `Japanese`.
- Kept fallback dataset source ready: `jacobmorrison/MATH-500-japanese`.
- Chose `HTML + KaTeX + Playwright` with system `google-chrome` for printable math PDF rendering.
- Split the generated paper into question pages plus a final OCR-friendly answer-sheet page.
- Used `test_id` printed on paper and extracted by OCR so analysis can look up `manifest.json`.

## 2026-03-16
- Added `azure_local_live_env.sh` so local live mode can be recreated from Azure CLI without hand-copying keys.
- Added a browser E2E script for the real happy path using `data/test/confirmation_test-3.jpg`.
- Switched the public deploy target from `static website + container app` to `single Azure Container App` because `az storage` and new managed-environment creation were blocked in this subscription.
- Reused the existing `sit-copilot-env` Container Apps environment after hitting the regional environment quota in Japan East.
- Served the built React app from FastAPI in the container image and moved frontend build assets to `/app-assets` to avoid conflicting with backend `/assets`.
- Added a DB-backed student management layer on top of the existing SQLite store and kept `uploads` / `approvals` / `replays` compatible.
- Chose `SQLite + FTS5 + local hash embeddings` for MVP RAG because only the chat deployment `sit-copilot-demo-chat` exists in Azure OpenAI and no embedding deployment was available.
- Promoted `/students` into the primary dashboard with overview cards plus right-pane detail, while keeping the existing upload -> OCR -> analysis -> homework approval flow intact.
- Stored seeded student documents, metrics, homework history, RAG chunks, and state snapshots in DB so student context no longer depends on raw text files.
- Used deterministic fallback summary / recommendation generation as the default path, with AOAI kept for smoke-tested live connectivity rather than making the demo depend on a second unstable prompt path.
