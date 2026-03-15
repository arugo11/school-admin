# AGENTS.md

## Goal
Build and refine the MVP in `SPEC.md` for the hackathon demo: an iPad-first web app that captures student math worksheets, runs OCR, produces weakness analysis and problem-number homework suggestions, and lets a teacher review and approve the result.

## Read First
- Read `SPEC.md` before changing anything.
- Treat `SPEC.md` as the source of truth for scope, architecture, acceptance criteria, and demo priorities.
- Prefer the smallest change that moves the happy path forward.

## Non-Negotiable Scope
- Keep the MVP centered on: upload -> OCR review -> analysis -> homework approval.
- Use the existing Azure OpenAI deployment and the existing Vision Read OCR resource unless the user explicitly asks to change infra.
- Do not expand scope to audio intake, parent reports, long-term analytics, fully local inference, GPU VM workflows, or Azure Foundry / Marketplace dependencies.

## Project Priorities
1. Demo reliability over architectural ambition.
2. A clean happy path before edge-case polish.
3. Small, reviewable diffs over repo-wide rewrites.
4. Structured outputs and validation over clever prompting.
5. Teacher override over full autonomy.

## Working Style
- Start with a short plan when the task is non-trivial.
- Work in small increments.
- After each increment, run the narrowest useful validation first, then broader checks.
- Prefer deterministic fixtures and mocks for routine iteration.
- Use live Azure calls only for explicit smoke tests or when the task is specifically about integration behavior.
- Keep secrets out of code and out of logs.

## Same-Failure Prevention Protocol
Do not repeat the same failed loop.

- Never rerun the same failing command or workflow more than **2 times** without changing something material.
- A material change means at least one of:
  - code change,
  - prompt change,
  - fixture/input change,
  - added logging/inspection,
  - narrowed hypothesis,
  - fallback to a simpler design.
- If the same failure appears twice, stop and write down:
  - what failed,
  - the evidence,
  - the current root-cause hypothesis,
  - the next changed approach.
- Store this in `docs/agent-notes/failure-log.md`. Create the file if it does not exist.
- Before retrying, read the latest relevant entry in `docs/agent-notes/failure-log.md`.
- If 3 distinct hypotheses fail, stop escalating complexity. Re-scope to the simplest approach that still satisfies `SPEC.md`.

## Required Execution Loop
For any meaningful implementation task, follow this order:
1. Read the relevant parts of `SPEC.md` and the touched files.
2. Define the acceptance check for this slice.
3. Implement the smallest viable change.
4. Run focused validation.
5. Fix failures.
6. Re-run validation.
7. Update docs only after the code path is stable.

## Output and Data Contracts
- Keep OCR output normalized before it reaches the LLM.
- Prefer explicit JSON schemas and post-parse validation.
- Do not send raw OCR blobs directly into downstream UX without normalization.
- Treat low-confidence OCR as first-class data and surface it in the teacher review UI.
- LLM output must be validated before UI rendering or persistence.
- Homework suggestions must stay at problem-number level for the MVP.

## Azure / Infra Guardrails
- Reuse existing resources whenever possible.
- Avoid creating new paid resources unless the user explicitly approves it.
- Do not introduce Azure Foundry, Marketplace models, GPU VMs, or unrelated services as a hidden dependency.
- If an Azure call fails, first verify env vars, endpoint shape, auth, payload schema, and region assumptions before changing architecture.
- Keep a local fallback path for the demo UX whenever possible, even if the fallback is a graceful error state plus retry.

## Testing and Validation
- Every code change should be accompanied by the smallest sensible validation.
- Prefer adding or updating tests close to the changed behavior.
- Maintain at least one golden-path fixture for:
  - worksheet upload,
  - OCR normalization,
  - LLM analysis result,
  - homework approval.
- Before declaring a task done, verify the happy path from upload to teacher approval.
- If a check is flaky, do not ignore it silently. Record the flake and isolate the cause.

## UI / Demo Rules
- Optimize for iPad Safari usability.
- Keep the demo flow obvious in under 10 seconds.
- Show uncertainty instead of hiding it.
- Teacher review must stay fast and lightweight.
- Prefer visible progress / retry states over blank waiting.

## When to Simplify
Simplify instead of escalating when:
- OCR structure is noisy,
- prompt behavior is unstable,
- end-to-end latency grows,
- the same bug keeps returning,
- the implementation drifts away from the demo story.

In those cases, reduce scope, harden interfaces, and preserve the main demo moment.

## Definition of Done
A task is done only when all of the following are true:
- it still fits `SPEC.md`,
- the changed path has been validated,
- no known repeated-failure loop is left undocumented,
- the worktree is clean,
- the result improves demo reliability, clarity, or evaluation score.

## Optional Agent / Skill Usage
- Prefer the main agent for tightly coupled work that shares context across planning, implementation, and testing.
- Use a focused reviewer/debugger agent only for self-contained analysis tasks.
- If skills are available, use them for repeatable workflows such as planning, debugging, or review, but do not offload core project judgment to a generic skill without checking `SPEC.md`.
