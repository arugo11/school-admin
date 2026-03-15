# SKILLS_NOTES.md

## Existing skill worth using now

### 1. `create-plan`
Use before large or risky changes.
Why:
- This project has a narrow demo story and strong scope constraints.
- A planning skill helps produce a short execution plan before touching code.
- The OpenAI skills catalog explicitly shows `create-plan` as an installable experimental skill.

Suggested use:
- architecture changes,
- refactors crossing multiple files,
- end-to-end integration tasks.

## Project-specific custom skills worth creating next

### 2. `azure-smoke-check`
Purpose:
- verify env vars,
- verify AOAI and Vision endpoints,
- run minimal non-destructive OCR / LLM smoke tests,
- print a short pass/fail report.

Why this project needs it:
- Azure config is one of the highest-risk integration points.
- It prevents losing time on repeated auth / endpoint mistakes.

### 3. `ocr-golden-eval`
Purpose:
- run OCR against a fixed fixture set,
- compare normalized JSON against golden outputs,
- highlight regressions in problem numbering, confidence, and extraction gaps.

Why this project needs it:
- OCR quality is the main upstream source of downstream analysis errors.
- It creates a stable evaluation loop.

### 4. `analysis-schema-check`
Purpose:
- validate LLM output against the agreed JSON schema,
- reject malformed or incomplete outputs,
- summarize common failure patterns.

Why this project needs it:
- Prevents fragile prompt-only integrations.
- Reduces repeated failures caused by shape drift.

### 5. `demo-gate`
Purpose:
- run the minimum acceptance flow for the hackathon demo,
- upload fixture -> OCR review -> analysis -> homework approval,
- fail if the main story breaks.

Why this project needs it:
- The demo moment is the product.
- This keeps iteration aligned with judging criteria.

### 6. `systematic-debugging`
Purpose:
- force a root-cause-first debugging workflow,
- require evidence before retries,
- update the project failure log.

Why this project needs it:
- The biggest practical risk is repeating the same failed attempt.

## What not to do with skills
- Do not create many overlapping skills.
- Do not hide core project rules inside multiple places.
- Keep AGENTS.md as the persistent project contract.
- Use skills only for reusable workflows, not as a replacement for the project spec.
