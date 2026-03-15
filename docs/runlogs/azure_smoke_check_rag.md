# Azure Smoke Check RAG

## 2026-03-16 Pre-Implementation

- Subscription: `Azure for Students / 4c170a0d-3e6d-42a0-b941-533e4f44e729`
- Resource presence:
  - `sitcopilotaoai23088`
  - `schooladminocr23088`
- Deployment presence:
  - `sit-copilot-demo-chat`
- Notes:
  - Embedding deployment was not found.
  - RAG implementation uses local derived vectors plus SQLite FTS to avoid adding paid Azure resources.

## 2026-03-16 Post-Implementation

| Check | Status | Latency | Note |
| --- | --- | --- | --- |
| Vision Read OCR | pass | 1.67s | `lines=2` |
| Azure OpenAI | pass | 0.96s | `{"ping":"return ok"}` |

- Command: `PYTHONPATH=backend python scripts/azure_smoke_check.py --use-az-cli`
- Notes:
  - AOAI / OCR の既存接続は維持された。
  - 新機能の RAG はローカル派生ベクトルで実装し, 既存 Azure 資産は要約・OCR の疎通確認に限定した。
