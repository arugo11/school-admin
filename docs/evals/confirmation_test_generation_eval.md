# Confirmation Test Generation Eval

| Check | Result | Note |
| --- | --- | --- |
| same seed selected_problems reproducible | pass | seed=111 |
| same seed rendered HTML reproducible | pass | fixed generated_at used |
| same seed PDF binary reproducible | warning | Chromium embeds print metadata |
| different seed changes selection | pass | 111 vs 222 |
| required artifacts exist | pass | confirmation_test.pdf, answer_key.pdf, answer_key.md, manifest.json, selected_problems.json, preview.html |
| manifest problem_count matches | pass | count=6 |

Primary dataset source used: `team-victory/qa_verify_10k_test` / `train`.
Layout default for exhibit eval: 6 questions, 2 question pages + 1 answer sheet page.