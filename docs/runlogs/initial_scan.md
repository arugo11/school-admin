# Initial Scan

Date: 2026-03-15

## Repo As-Is
- Repo contains project guidance and investigation docs only.
- Confirmed files at scan time: `AGENTS.md`, `docs/SPEC.md`, Azure investigation notes, editor settings.
- No existing frontend app, backend app, sample assets, package manifest, or test suite were found during the deeper scan.
- Git exists and is initialized, but there are no commits yet.

## Environment Snapshot
- Python: `3.12.3`
- Node: `18.19.0`
- npm: `9.2.0`
- `pnpm`, `uv`, and `playwright` were not installed.
- Azure CLI is available and logged into `Azure for Students`.
- No Azure-related environment variables were set in the current shell.

## Risks Identified Early
- Live Azure integration needs secret-safe setup before use.
- OCR on Japanese handwritten math must be treated as text extraction plus teacher review, not as perfect semantic understanding.
- Demo reliability needs a replay mode because cloud dependencies may be unstable during judging.

## Decision Trigger
- Because no reusable app code was found, proceed with a minimal fresh implementation focused on the happy path and replay safety.
