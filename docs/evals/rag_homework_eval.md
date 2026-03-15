# RAG Homework Eval

Date: 2026-03-16

## Validation Source
- Endpoint: `POST /api/homework/rag-recommend`
- Fixture student: `s-03`
- Input: replay analysis + normalized OCR

## Result
- Response status: pass
- Output shape:
  - `student_id`
  - `recommended_problem_groups[]`
  - `fallback_used`
  - Result: pass
- Granularity:
  - `A-03`, `A-06`, `A-04` の大問IDで返却
  - Result: pass
- 学力帯制約:
  - `s-03` は `standard`
  - advanced を出さず, `standard` 中心で返却
  - Result: pass
- 文脈反映:
  - `一次方程式` と `符号処理` に寄せた提案へ変化
  - recent homework を見て exact repeat の減点を実施
  - Result: pass
- Fallback:
  - recommendation schema に `fallback_used` を保持
  - Result: pass

## Notes
- 現プリント単体の既存提案より, 生徒の直近履歴を根拠に説明しやすい。
- MVPでは deterministic rule + RAG context を優先し, 過度な prompt 依存を避けた。
