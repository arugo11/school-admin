# Azure Web Deploy Runlog

Date: 2026-03-16 JST

## Summary
- Local live env was generated with `./scripts/azure_local_live_env.sh`.
- Local browser E2E passed with `node scripts/e2e_browser_live.mjs`.
- Public deploy was completed with `./scripts/azure_deploy_web.sh`.
- Public browser E2E passed against:
  - `https://school-admin-demo-api.grayground-578aed68.japaneast.azurecontainerapps.io`

## Azure Resources Used
- Resource group: `school-admin-demo-rg`
- Container app: `school-admin-demo-api`
- Registry: `schooladmindemoacr23088`
- Managed environment: reused existing `sit-copilot-env`
- Azure Vision OCR: `schooladminocr23088`
- Azure OpenAI: `sitcopilotaoai23088`

## Validation Evidence
- Public health check:
  - `GET /api/health` -> `{"status":"ok"}`
- Public students API:
  - `GET /api/students` -> `6` students
- Public browser E2E:
  - command:
    `E2E_BASE_URL=https://school-admin-demo-api.grayground-578aed68.japaneast.azurecontainerapps.io E2E_ROUTE_TIMEOUT_MS=420000 node scripts/e2e_browser_live.mjs`
  - result:
    `{"status":"pass","baseUrl":"https://school-admin-demo-api.grayground-578aed68.japaneast.azurecontainerapps.io","fixturePath":"/home/argo/school-admin/data/test/confirmation_test-3.jpg"}`

## Notes
- `az storage` and new Container Apps Environment creation were blocked by subscription / regional limits, so the final public deploy was simplified to a single Azure Container App that serves both the frontend and backend.
- Azure OpenAI returned intermittent `429` during OCR / analysis, but the app-level retry logic still allowed both local and public live E2E to complete successfully.
