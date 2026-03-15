# School Admin MVP

iPad-first demo web app for cram-school math worksheet intake:
`student dashboard -> upload -> OCR review -> analysis -> homework approval`.

## Stack
- Backend: FastAPI + Pydantic + SQLite/files
- Frontend: Vite + React + TypeScript
- Live OCR: Azure Vision Read `schooladminocr23088`
- Live Analysis: Azure OpenAI `sitcopilotaoai23088` / `sit-copilot-demo-chat`
- Replay safety path: seeded success snapshots under `data/replays/`

## Quick Start
1. Create backend venv and install deps.
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```
2. Install frontend deps.
```bash
cd frontend && npm install && cd ..
```
3. Copy env template and fill keys if you want live Azure mode.
```bash
cp .env.example .env.local
```
Or generate live env from Azure CLI.
```bash
./scripts/azure_local_live_env.sh
```
4. Start backend.
```bash
source .venv/bin/activate
PYTHONPATH=backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```
5. Start frontend.
```bash
cd frontend
VITE_API_BASE=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 4173
```
6. Open `http://127.0.0.1:4173`.

Or start both together.
```bash
./scripts/start_demo.sh
```

Stop both.
```bash
./scripts/stop_demo.sh
```

## Demo Modes
- `Replay mode`: uses `data/replays/s-03.json` and never depends on Azure during the flow.
- `Live mode`: uploads the worksheet, calls Azure Vision Read, then Azure OpenAI or safe fallback analysis.

## Student RAG Dashboard
- `/students` now shows classroom overview, 6 student panels, and a right-side detail pane.
- Student context is stored in SQLite tables:
  - `students`
  - `student_documents`
  - `student_metrics`
  - `homework_history`
  - `rag_chunks`
  - `student_state_snapshots`
- RAG uses DB-backed documents plus local hash embeddings and SQLite FTS5.
- Refresh all student summaries with:
```bash
source /home/argo/school-admin/.venv/bin/activate
PYTHONPATH=backend python scripts/refresh_student_summaries.py
```

## Validation Commands
```bash
source .venv/bin/activate
PYTHONPATH=backend pytest backend/tests -q
cd frontend && npm test && npm run build && cd ..
PYTHONPATH=backend python scripts/ocr_golden_eval.py --write-doc docs/evals/ocr_golden_eval.md
PYTHONPATH=backend python scripts/analysis_schema_eval.py --write-doc docs/evals/analysis_schema_eval.md
PYTHONPATH=backend python scripts/e2e_demo_eval.py
PYTHONPATH=backend python scripts/latency_eval.py
PYTHONPATH=backend python scripts/failure_injection_eval.py
PYTHONPATH=backend python scripts/azure_smoke_check.py --use-az-cli --write-doc docs/runlogs/azure_smoke_check.md
```

## Azure Deploy
Deploy the web app with Azure CLI.
```bash
./scripts/azure_deploy_web.sh
```
The script prints a public URL backed by Azure Container Apps.

## GitHub Actions
`main` への push で GitHub Actions の CI/CD が動きます。

CI:
- backend test: `pytest backend/tests -q`
- frontend test: `npm test`
- frontend build: `npm run build`

CD:
- Azure login
- `./scripts/azure_deploy_web.sh`
- public health check
- public browser E2E

Required repository secrets:
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

The Azure principal needs permission to:
- push images to `schooladmindemoacr23088`
- update `school-admin-demo-api`
- read keys for `schooladminocr23088` and `sitcopilotaoai23088`

Run browser E2E locally or against the deployed URL.
```bash
node scripts/e2e_browser_live.mjs
E2E_BASE_URL=https://your-public-url node scripts/e2e_browser_live.mjs
```

## Key Paths
- Backend entry: `backend/app/main.py`
- Frontend entry: `frontend/src/main.tsx`
- Demo data: `data/`
- Runbook: `docs/DEMO_RUNBOOK.md`
- Demo story: `docs/demo_story.md`

## Confirmation Test Generation
Generate printable visitor tests from the Japanese QA verify dataset.
```bash
source .venv/bin/activate
python scripts/generate_confirmation_test.py \
  --dataset-source huggingface \
  --dataset-name team-victory/qa_verify_10k_test \
  --split train \
  --count 6 \
  --seed 101 \
  --difficulty-min 1 \
  --difficulty-max 2 \
  --output-dir data/generated/tests/exhibit-main \
  --with-answer-key \
  --test-id ct-exhibit-main
```
See `docs/CONFIRMATION_TEST_RUNBOOK.md` for the exhibit/main + backup sets.

## Dataset Export
Export a Hugging Face dataset split to a local CSV so you can inspect it directly.
```bash
source .venv/bin/activate
python scripts/export_hf_dataset_csv.py \
  --dataset-name team-victory/qa_verify_10k_test \
  --split train \
  --output data/generated/datasets/team-victory__qa_verify_10k_test/train.csv
```
