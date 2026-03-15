# MVP Plan

## Shortest Path
1. Lock data contracts and deterministic demo data.
2. Build backend happy path with schema validation and replay snapshots.
3. Build frontend flow from student selection to homework approval.
4. Add focused tests and eval scripts.
5. Add live Azure smoke scripts and runbook.

## In Scope
- Student list for 6 demo students.
- Upload / OCR review / analysis / homework approval flow.
- OCR normalization with uncertainty.
- Analysis JSON validation and homework catalog constraint.
- Teacher override actions: remove, lighten, regenerate.
- Replay mode and demo runbook.

## Out of Scope
- Audio intake.
- Parent reports.
- Long-term analytics.
- Full offline inference.
- Foundry / Marketplace / GPU VM dependencies.
- Heavy auth or production ops features.

## Acceptance Checks Per Slice
- Contracts: schema tests pass.
- Backend: mocked happy path passes.
- Frontend: main story renders and completes against mocked/backend data.
- Demo: replay mode completes without cloud access.
- Live integration: smoke scripts can reach Vision and AOAI when env is configured.
