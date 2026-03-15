# Final Smoke Check

Date: 2026-03-15

## Environment Summary
- Repo: `/home/argo/school-admin`
- Backend URL: `http://127.0.0.1:8010`
- Frontend URL: `http://127.0.0.1:4174`
- Python: `3.12.3`
- Node: `/usr/bin/node`
- Azure CLI: `/usr/bin/az`
- Platform: `Linux-6.17.0-14-generic-x86_64-with-glibc2.39`

## Startup Result
| Check | Result | Note |
| --- | --- | --- |
| backend startup | pass | `GET /api/health` returned `{"status":"ok"}` |
| frontend startup | pass | Vite dev server reachable on `:4174` |
| replay endpoint | pass | `/api/demo/s-03/replay` returned `source_mode=replay` and seeded homework list |

## Azure Live Smoke
| Check | Status | Latency | Note |
| --- | --- | --- | --- |
| Vision Read OCR | pass | 5.21s | `lines=2` on smoke PDF |
| Azure OpenAI | pass | 0.58s | returned `{"ping":"return ok"}` |

## Env Availability Summary
- Shell environment itself does not export Azure secrets by default.
- Fresh smoke succeeded through Azure CLI-backed secret resolution.
- Runtime app path now also has Azure CLI fallback for the existing OCR and AOAI resources, which improves demo safety when `.env.local` is absent.
- No secrets were printed during this pass.

## Replay Result
- `GET /api/demo/s-03/replay` returned:
  - `student_id=s-03`
  - `source_mode=replay`
  - `analysis.source_mode=replay`
  - `recommended_homework=[A-02, A-04, A-07]`

## Immediate Blockers
- No startup blocker found.
- No live Azure blocker found in the fresh smoke pass.

## Same-Day Operational Warning
- Earlier in the same final-E2E session, Azure OpenAI returned one transient `429 Too Many Requests` before succeeding on retry.
- This is not a current blocker, but it is a demo-day risk signal.
- Operational implication: start in live mode only after smoke is green, and switch to replay immediately if AOAI stalls.
