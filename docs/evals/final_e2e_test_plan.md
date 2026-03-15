# Final E2E Test Plan

Date: 2026-03-15

## Goal
Ship a decision-grade final validation for the exhibit demo before the user touches it.
This pass evaluates not only functional correctness, but also whether the demo is emotionally convincing, easy to operate, and resilient enough for live exhibition use.

## Current Baseline
- Existing MVP flow exists: `upload -> OCR review -> analysis -> homework approval`
- Live path exists via Azure Vision Read and Azure OpenAI
- Replay path exists and must remain usable
- Confirmation-test generation exists and must be validated as an exhibit-ready input path

## Known Unknowns To Resolve In This Pass
- Fresh Azure smoke has not yet been rerun for this final gate
- Browser-level live/replay flow timing is not yet documented in final form
- Confirmation-test OCR eval has used generated answer-sheet samples; handwritten realism still needs explicit judgment
- Final judge-facing story quality has not yet been scored in one place

## Cases To Execute
### Smoke
- Backend startup
- Frontend startup
- Azure Vision live smoke
- Azure OpenAI live smoke
- Replay endpoint reachability
- Env availability summary without secrets

### Objective E2E
- Live happy path x3 consecutive
- Replay happy path x3 consecutive
- Realistic exhibit path with generated confirmation test x1
- Failure/fallback matrix:
  - oversized image
  - malformed OCR result
  - OpenAI fallback
  - degraded live OCR / unavailable live path handling
  - network-instability operational fallback to replay

### Subjective Review
- Judge persona
- Cram-school teacher persona
- Visitor/student persona
- Product designer persona
- Visitor-participation assessment for confirmation test difficulty and pacing

### Narrated Pass
- 60-second hook
- 120-second full story
- Record measured time, friction, clarity in first 20 seconds, and ending quality

## Evidence To Capture
- command/log snippets for smoke and failure handling
- timing table for live/replay/narrated runs
- API response summaries for success/fallback cases
- browser screenshots for key states where practical
- explicit pass/fail per case

## Allowed Fixes
Only if a clear demo blocker is found:
- wording clarity
- mode/fallback visibility
- OCR review readability
- analysis density
- approval-screen closure
- confirmation-test question count/layout if exhibit pacing is poor

## Not Allowed
- refactors
- architecture changes
- new infra
- schema redesign unless current behavior blocks the demo

## Stop Conditions
- If live and replay both pass and no blocking issue is found, finalize docs and recommend user testing.
- If a small fix is necessary, apply exactly that fix and rerun:
  - 1 live path
  - 1 replay path
  - 1 narrated 60s pass
  - 1 narrated 120s pass
- If a deeper issue appears, document it as blocking instead of escalating into large changes.
