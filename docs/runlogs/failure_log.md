# Failure Log

## 2026-03-15 Confirmation Test Generation Eval
- Failed symptom: same-seed PDF binary hash changed across two runs.
- Evidence: `selected_problems.json` matched, but Chromium-produced PDF hashes differed.
- Root-cause hypothesis: PDF output included per-run print metadata.
- Next changed approach: validate same-seed reproducibility with `selected_problems.json` and `preview.html`, and keep PDF binary comparison as warning only.

## 2026-03-16 Worktree backend validation bootstrap
- Failed symptom: focused backend validation and summary refresh script both failed immediately with `/bin/bash: .venv/bin/activate: No such file or directory`.
- Evidence: new worktree `/home/argo/student-rag-management-worktree` does not contain the original repo-local virtualenv.
- Root-cause hypothesis: validation commands assumed the venv lived inside every worktree, but only `/home/argo/school-admin/.venv` exists.
- Next changed approach: reuse the original repo venv explicitly via `/home/argo/school-admin/.venv/bin/activate` for all Python validation in this worktree.

## 2026-03-16 Worktree frontend validation bootstrap
- Failed symptom: `npm test` and `npm run build` failed with `vitest: not found` and `tsc: not found`.
- Evidence: the new worktree does not have `frontend/node_modules`, so project-local executables were unavailable.
- Root-cause hypothesis: git worktree does not share nested dependency directories from the original checkout.
- Next changed approach: run `npm install` inside `frontend/` in the worktree, then rerun frontend validation.

## 2026-03-16 Student summary live generation throttle
- Failed symptom: bulk summary regeneration hit `AOAI chat HTTP error ... 429` twice during `scripts/reset_student_demo_data.py`.
- Evidence: the reset run logged retry attempt 1 and 2 with 30s backoff against the existing chat deployment.
- Root-cause hypothesis: generating six summaries in one burst exceeded the shared demo deployment throughput.
- Next changed approach: keep summary generation on the live LLM path with fallback, but avoid repeated bulk refreshes during iteration and rely on per-student refresh for validation.
