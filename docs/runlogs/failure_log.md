# Failure Log

## 2026-03-15 Confirmation Test Generation Eval
- Failed symptom: same-seed PDF binary hash changed across two runs.
- Evidence: `selected_problems.json` matched, but Chromium-produced PDF hashes differed.
- Root-cause hypothesis: PDF output included per-run print metadata.
- Next changed approach: validate same-seed reproducibility with `selected_problems.json` and `preview.html`, and keep PDF binary comparison as warning only.
