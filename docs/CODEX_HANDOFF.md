# CODEX HANDOFF

## Goal
- Continue the MVP in [SPEC.md](/home/argo/school-admin/docs/SPEC.md).
- Protect the happy path: `upload -> OCR review -> analysis -> homework approval`.
- Optimize for hackathon demo reliability, especially on iPad Safari.

## Current State
- This repo is intended to be restorable at home without relying on office-only local state.
- Secrets are intentionally not committed. Use `.env.example` as the template and recreate `.env.local`.
- The app already includes:
  - FastAPI backend
  - React/Vite frontend
  - replay mode for demo safety
  - Azure Vision Read + Azure OpenAI integration paths
  - demo/eval docs under `docs/`

## First Read
1. [docs/SPEC.md](/home/argo/school-admin/docs/SPEC.md)
2. [AGENTS.md](/home/argo/school-admin/AGENTS.md)
3. [README.md](/home/argo/school-admin/README.md)
4. [docs/DEMO_RUNBOOK.md](/home/argo/school-admin/docs/DEMO_RUNBOOK.md)
5. Latest notes under [docs/agent-notes/failure-log.md](/home/argo/school-admin/docs/agent-notes/failure-log.md)

## Run Locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
npm install
cd frontend && npm install && cd ..
cp .env.example .env.local
./scripts/start_demo.sh
```

## Important Paths
- Backend entry: [backend/app/main.py](/home/argo/school-admin/backend/app/main.py)
- Frontend entry: [frontend/src/main.tsx](/home/argo/school-admin/frontend/src/main.tsx)
- Azure config: [backend/app/core/config.py](/home/argo/school-admin/backend/app/core/config.py)
- OCR client: [backend/app/clients/vision.py](/home/argo/school-admin/backend/app/clients/vision.py)
- Analysis client: [backend/app/clients/azure_openai.py](/home/argo/school-admin/backend/app/clients/azure_openai.py)
- Replay fixtures: [data/replays](/home/argo/school-admin/data/replays)
- Demo students/catalog: [data/students](/home/argo/school-admin/data/students), [data/catalog](/home/argo/school-admin/data/catalog)

## Environment Notes
- Azure Vision endpoint default: `https://japaneast.api.cognitive.microsoft.com/`
- Azure OpenAI endpoint default: `https://japaneast.api.cognitive.microsoft.com/`
- Azure OpenAI deployment default: `sit-copilot-demo-chat`
- Required secrets are expected through env vars, not committed files.

## Validation Order
1. Run the smallest check for the changed slice first.
2. Then verify the happy path end-to-end.
3. Before handing off, ensure the worktree is clean.

Useful commands:
```bash
source .venv/bin/activate
PYTHONPATH=backend pytest backend/tests -q
cd frontend && npm test && npm run build && cd ..
PYTHONPATH=backend python scripts/e2e_demo_eval.py
PYTHONPATH=backend python scripts/azure_smoke_check.py --use-az-cli --write-doc docs/runlogs/azure_smoke_check.md
```

## Working Rules
- Prefer replay mode unless the task is explicitly about live Azure behavior.
- Keep OCR normalized before it touches the analysis/UI path.
- Validate LLM outputs before rendering or persisting.
- Keep homework suggestions at problem-number level for the MVP.
- If the same failure happens twice, update the failure log before retrying.

## Repo Hygiene
- Large local-only artifacts are intentionally excluded from git:
  - local model weights and metadata mirrors
  - OCR debug dumps
  - generated dataset exports
  - editor/runtime scratch dirs
- If a future task truly needs one of those, add it deliberately instead of broadly committing local state.

## Suggested Next Focus
- Start from the most demo-critical gap visible in the current branch.
- If unsure, prefer improving:
  1. upload/retry clarity
  2. OCR uncertainty review UX
  3. analysis output validation
  4. homework approval speed on iPad
