# Confirmation Test Runbook

## Purpose
Generate a visitor-facing confirmation test, print it, let a visitor answer on the OCR-friendly answer sheet, then run the existing flow:
`upload -> OCR review -> analysis -> homework approval`.

## Dataset
- Primary dataset
  - `team-victory/qa_verify_10k_test`
  - split: `train`
- Why it fits this demo
  - Japanese middle-school math problems
  - explicit `unit` and `difficulty`
  - stable `expected_answer`
  - easier to turn into short confirmation tests than the previous multilingual MATH set

## Official Test Sets
- Exhibit main
  - `test_id`: `ct-exhibit-main`
  - seed: `101`
  - output: `data/generated/tests/exhibit-main`
- Exhibit backup
  - `test_id`: `ct-exhibit-backup`
  - seed: `202`
  - output: `data/generated/tests/exhibit-backup`

## Regeneration Commands
```bash
source .venv/bin/activate
python scripts/generate_confirmation_test.py \
  --dataset-source huggingface \
  --dataset-name team-victory/qa_verify_10k_test \
  --split train \
  --count 6 \
  --seed 101 \
  --difficulty-min 1 \
  --difficulty-max 2 \
  --output-dir data/generated/tests/exhibit-main \
  --with-answer-key \
  --test-id ct-exhibit-main
```

```bash
source .venv/bin/activate
python scripts/generate_confirmation_test.py \
  --dataset-source huggingface \
  --dataset-name team-victory/qa_verify_10k_test \
  --split train \
  --count 6 \
  --seed 202 \
  --difficulty-min 1 \
  --difficulty-max 2 \
  --output-dir data/generated/tests/exhibit-backup \
  --with-answer-key \
  --test-id ct-exhibit-backup
```

## Files Produced Per Set
- `confirmation_test.pdf`
- `answer_key.pdf`
- `answer_key.md`
- `manifest.json`
- `selected_problems.json`
- `preview.html`
- `preview.png`

## Recommended Demo Operation
1. Print `confirmation_test.pdf`.
2. Ask the visitor to solve on the final `解答用紙` page.
3. Use the left `計算過程` box for scratch work and the right `最終解答` box for the final answer.
4. Photograph only the answer-sheet page once.
5. Upload in the existing MVP UI.
6. In OCR review, confirm `test_id` and `Q1..Q6` mappings.
7. Continue to analysis and homework approval.

## Why This Layout Works
- Question pages keep math readable with KaTeX.
- The final answer sheet separates `計算過程` and `最終解答`.
- OCR first detects each question row, then crops the answer boxes before reading them.
- `test_id` is printed on the answer sheet, so analysis can look up `manifest.json`.
- `catalog_problem_no` is stable and traceable back to the source row.

## Validation Commands
```bash
source .venv/bin/activate
python scripts/confirmation_test_generation_eval.py --write-doc docs/evals/confirmation_test_generation_eval.md
python scripts/confirmation_test_ocr_eval.py --test-dir data/generated/tests/exhibit-main --use-az-cli --write-doc docs/evals/confirmation_test_ocr_eval.md
```

## Demo-Day Fallback
- If the main printed set is damaged, switch to `ct-exhibit-backup`.
- If live OCR is unstable, keep using the printed test but switch the app to Replay mode for the explanation after showing the answer sheet.
- If the visitor handwriting is too hard to OCR quickly, use one of the generated typed sample answer-sheet PDFs in `data/generated/tests/exhibit-main/` for backup explanation.
