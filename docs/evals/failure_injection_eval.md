# Failure Injection Eval

| Case | Result | Note |
| --- | --- | --- |
| oversized image | pass | {"detail":"Image too large. Keep it under 5MB for demo reliability."} |
| malformed OCR payload | pass | {"student_id":"s-03","source_image_id":"fi-1","page_type":"worksheet","ocr_confi |
| OpenAI unavailable fallback | pass | ライブ分析が不安定な場合でも、このセットなら講師がその場で説明しやすい。 |
| Vision failure UX path | warning | Live OCR still depends on env; UI exposes replay fallback banner and seeded path. |
| network timeout UX path | warning | Documented in runbook with switch to replay mode. |