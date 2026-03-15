# Demo Runbook

## Goal
Show the full story in under 2 minutes:
6 students -> main student -> worksheet upload -> OCR review -> analysis -> remove one problem or lighten -> approve.

## Preflight
1. Confirm backend and frontend dependencies are installed.
2. If using live mode, confirm Azure smoke passes:
```bash
source .venv/bin/activate
PYTHONPATH=backend python scripts/azure_smoke_check.py --use-az-cli --write-doc docs/runlogs/azure_smoke_check.md
```
3. If port `8000` is busy, run backend on `8001` and start frontend with `VITE_API_BASE=http://127.0.0.1:8001`.
4. Keep `frontend/public/demo-fixtures/s03-signs.svg` ready as the main worksheet image.

## Recommended Startup
```bash
./scripts/azure_local_live_env.sh
./scripts/start_demo.sh
```

Or run the servers manually.
```bash
source .venv/bin/activate
PYTHONPATH=backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```
```bash
cd frontend
VITE_API_BASE=http://127.0.0.1:8000 npm run dev -- --host 0.0.0.0 --port 4173
```

## Public Deploy
Deploy the same flow to Azure Container Apps.
```bash
./scripts/azure_deploy_web.sh
```

Current deployed URL:
`https://school-admin-demo-api.grayground-578aed68.japaneast.azurecontainerapps.io`

Public browser E2E:
```bash
E2E_BASE_URL=https://school-admin-demo-api.grayground-578aed68.japaneast.azurecontainerapps.io \
E2E_ROUTE_TIMEOUT_MS=420000 \
node scripts/e2e_browser_live.mjs
```

## Primary Demo Flow
1. Open `/students` and point out the 6-student spread.
2. Tap `Yuna Kobayashi` as the spotlight case.
3. Start in `Live mode` if Azure smoke is green.
4. Upload a worksheet photo.
5. On `OCR review`, highlight the uncertainty chips rather than claiming perfect OCR.
6. Continue to `Analysis` and read the short rationale.
7. In `Homework review`, remove one problem or tap `1クリックで軽くする`.
8. Approve and land on the completion screen.

## Fallback Flow
### Cached success replay mode
Use this if OCR, network, or AOAI is unstable.
1. From student detail, choose `Replay で開始`.
2. On upload page, use `seeded snapshot を使う`.
3. Continue through OCR review, analysis, and approval exactly as in the main flow.
4. Say explicitly that replay mode is a seeded success path kept for demo resilience.

### Failure-specific fallback notes
- Vision OCR timeout/failure:
  - Switch to Replay mode and continue.
  - Explain that OCR is treated as text extraction plus teacher confirmation.
- OpenAI output instability:
  - The backend falls back to deterministic catalog-constrained recommendations.
  - Continue with approval and mention teacher override.
- Network instability:
  - Use Replay mode immediately.

## Demo-Day Recommended Script
1. “授業前20分で6人分の個別宿題を考えるのは大変です。”
2. “今日は一番悩ましい Yuna を見ます。”
3. “答案を撮ると、OCR は完璧扱いせず、要確認箇所を出します。”
4. “その上で、弱点と今夜の宿題候補を problem number で返します。”
5. “最後は講師が1問外すか軽くして承認します。”

## Last-Minute Checks
- `docs/evals/ocr_golden_eval.md`
- `docs/evals/analysis_schema_eval.md`
- `docs/evals/e2e_demo_eval.md`
- `docs/evals/latency_eval.md`
- `docs/evals/failure_injection_eval.md`
- `docs/runlogs/azure_smoke_check.md`
- `docs/runlogs/azure_web_deploy_20260316.md`
