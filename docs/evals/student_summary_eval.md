# Student Summary Eval

Date: 2026-03-16

## Validation
- Command: `PYTHONPATH=backend pytest backend/tests/test_student_rag_api.py -q`
- Manual refresh: `PYTHONPATH=backend python scripts/refresh_student_summaries.py`

## Results
- 6人分の summary 生成: pass
- 必須フィールド:
  - `current_status`
  - `risk_signals`
  - `next_best_actions`
  - `recommended_response`
  - `one_line_analysis`
  - `recommended_action`
  - `cited_document_titles`
  - Result: pass
- `cited_document_titles` 3件固定:
  - API test で確認
  - Result: pass
- 主役生徒 `s-03`:
  - current status: `一次方程式の整理は概ね良いが, マイナスの扱いで失点.`
  - risk signals: `符号処理が直近も継続課題` など
  - next action: `授業冒頭で符号処理を短く確認`
  - Result: pass

## Notes
- summary は deterministic fallback を正式経路として実装しているため, schema 準拠率は実質 100%。
- live AOAI を使わなくてもデモで崩れにくい。
