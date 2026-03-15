# Student RAG Retrieval Eval

Date: 2026-03-16

## Scope
- Backend endpoint: `GET /api/students/{student_id}/documents`
- Backend search path: `Repository.search_rag_chunks`
- Validation source: `backend/tests/test_student_rag_api.py`, manual API inspection via `TestClient`

## Checks
- `student_id` filter:
  - `s-03` documents include `2026-03-13 面談メモ`
  - `s-02` documents do not include that title
  - Result: pass
- Recent window:
  - Search query is limited to `document_date >= now - 30 days`
  - Seeded retrieval for `s-03` returned only March 2026 documents
  - Result: pass
- Document type ranking sanity:
  - After ranking adjustment, `s-03` summary cited `確認テスト報告` and `宿題実施履歴` ahead of `attendance`
  - Result: pass
- Cross-student contamination:
  - New API test confirmed separate document sets per student
  - Result: pass
- Cited title naturalness:
  - `s-03` cited titles: `2026-03-03 確認テスト報告`, `2026-03-10 確認テスト報告`, `2026-03-05 宿題実施履歴`
  - Result: pass

## Summary
- Retrieval behavior is acceptable for MVP demo use.
- Main limitation: embedding is deterministic local hash embedding, so semantic recall is intentionally conservative.
