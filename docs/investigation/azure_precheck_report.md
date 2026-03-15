# Azure 事前調査レポート

更新日時: 2026-03-15 16:56 JST

## 結論サマリ

### 事実
- 現在の既定サブスクリプションは `Azure for Students` で、`Enabled` 状態。
- 既存の Azure OpenAI リソース `sitcopilotaoai23088` が `japaneast` に存在し、`gpt-4o-mini` デプロイ `sit-copilot-demo-chat` を実呼び出しできた。
- 調査用に `school-admin-precheck-rg` と `ComputerVision F0` リソース `schooladminocr23088` を `japaneast` に作成でき、Read OCR API の最小疎通にも成功した。
- `Microsoft.MachineLearningServices` と `Microsoft.SaaS` は現サブスクリプションで `NotRegistered`。既存の AI Foundry / Azure ML workspace / hub / project は確認できなかった。

### 推測
- MVP デモの最安全構成は、`Azure Vision Read OCR + 既存 Azure OpenAI(gpt-4o-mini) + 教室内ローカル Web/API` である。
- Azure AI Foundry serverless model は、公式ドキュメント上で「有効な支払い方法付きサブスクリプション」が前提かつパートナー/コミュニティモデルは Azure Marketplace 同意が必要なため、Azure for Students 単独では詰まる可能性が高い。

### 未確認
- Azure for Students で新規の Azure OpenAI リソースを追加作成できるか。
- Azure AI Foundry の hub/project を新規作成できるか。
- 実際の日本語手書き数学答案に対する OCR 精度。

## 現在の Azure 環境

### 事実
- ログイン済みユーザー: `al23088@sic.shibaura-it.ac.jp`
- 既定 subscription 名: `Azure for Students`
- subscription ID: `4c170a0d-3e6d-42a0-b941-533e4f44e729`
- tenant: `SIT` / `shibaura3.onmicrosoft.com`
- 利用可能な有効 subscription は 1 件のみ。

### Azure for Students 判定

### 事実
- `az account show` の `name` が `Azure for Students`。

### 推測
- 少なくとも現在使われている subscription は Azure for Students と判断してよい。
- ただし offer ID や請求属性までは CLI で追加確認していないため、厳密な契約メタデータは未確認。

## 利用可能そうなリソース

### 再利用できそう
- `sitcopilotaoai23088` (`Microsoft.CognitiveServices/accounts`, kind=`OpenAI`, `japaneast`)
  - 理由: 既存デプロイ `sit-copilot-demo-chat` が応答したため、LLM 基盤として最も安全。
- `sit-copilot` resource group
  - 理由: 既に OpenAI を含む関連リソース群があり、LLM 再利用先として現実的。
- `school-admin-precheck-rg`
  - 理由: 今回新規作成できた専用 RG。調査用/デモ用最小構成を分離して置ける。
- `schooladminocr23088` (`ComputerVision`, `F0`, `japaneast`)
  - 理由: 実作成済みで Read OCR 疎通済み。MVP の OCR 第一候補としてそのまま再利用可能。

### 使わない方がよい
- `ai_appi-sitc-02210594_d4843bb6-e2ea-4f80-af57-e7fa2f5c9a1b_managed`
  - 理由: managed RG であり、用途不明かつ既存管理対象。触らない方が安全。
- `sit-copilot-api`, `sit-copilot-env`, `sit-copilot-students`, `sitcopilotstudentsacr`, `sitcopilotpg23088`, `sitcopilotsearch23088`
  - 理由: 既存アプリ基盤らしき構成で、今回の MVP 調査とは責務が異なる。巻き込み変更のリスクがある。

## 利用不可 / 高リスクな選択肢

### 事実
- `Microsoft.MachineLearningServices` は `NotRegistered`。
- `Microsoft.SaaS` は `NotRegistered`。
- 既存の ML workspace / Foundry hub / project は確認できなかった。
- Foundry serverless の公式ドキュメントには「有効な支払い方法のある Azure subscription が必要」「Free または trial subscription は不可」「Partners and Community models は Azure Marketplace へのサブスクライブが必要」とある。

### 推測
- Azure for Students で Foundry serverless を新規採用する案は、Marketplace と支払い条件の両面で高リスク。
- Marketplace 同意が必要なモデルは、Cohere 系などの `Models from Partners and Community`。今回の方針では避けるべき。
- Foundry を使うなら、Marketplace 不要の `Models Sold Directly by Azure` に限定して検討するのが安全。

## OCR 候補の評価

### 第一候補: Azure Vision Read OCR

### 事実
- `ComputerVision F0` を `japaneast` に作成できた。
- `vision/v3.2/read/analyze` で PDF 入力の Read OCR 疎通に成功した。
- 公式ドキュメント上、Read 3.2 は手書き対応で、日本語手書きもサポート対象に含まれる。
- コンテナ版 Read 3.2 も存在する。

### 推測
- 「答案を撮るだけで弱点分析」MVP の OCR 第一候補に据えてよい。
- ただし適しているのは主に「文字列抽出」であり、以下は弱い可能性が高い。
  - 数式の意味理解
  - 丸付け記号、取り消し線、解き直し痕跡の厳密解釈
  - 手書きレイアウトの教育評価向け構造化
- よって MVP では「OCR は文字列候補抽出」「最終判断は講師承認 UI」で設計するのが安全。

### クラウド API とコンテナ版の違い

### 事実
- クラウド API はすぐ使え、今回実疎通済み。
- コンテナ版は Docker と AVX2 が必要で、通常運用でも Azure への billing 接続が必要。
- 切断環境での実行には申請と commitment plan が必要。
- コンテナは課金情報送信のため Azure と通信するが、ドキュメントでは画像やテキストなどの顧客データは Microsoft に送信しないと明記されている。

### 推測
- 今回のデモではクラウド API を採用し、審査向け説明では「将来は OCR コンテナに差し替え可能」と述べるのが一貫している。

## LLM 候補の評価

### 第一候補: 既存 Azure OpenAI `gpt-4o-mini`

### 事実
- 既存 resource と deployment があり、API 応答を確認済み。
- Marketplace 同意は不要。
- GPU VM は不要。
- 教員承認付きの宿題提案・弱点分析用途には十分軽量。

### 推測
- 日本語数学の短い分析・宿題候補生成には最も安全。
- SPEC.md では「本線」として扱ってよい。

### 代替候補: Azure AI Foundry serverless

候補比較:

| 候補 | 根拠カテゴリ | Marketplace 要否 | serverless | API | 日本語観点 | 評価 |
| --- | --- | --- | --- | --- | --- | --- |
| `gpt-4o-mini` on Azure OpenAI | 既存実資産 | 不要 | Foundry ではなく AOAI | Chat Completions / Responses | 実務上無難 | 最優先 |
| `Mistral-Large-3` | Models sold directly by Azure | 不要 | 可 | Azure AI Model Inference API | docs 上 `ja` 対応あり | Foundry が使えるなら有力 |
| `model-router` | Models sold directly by Azure | 不要 | 可 | Azure AI Model Inference API | ルーティング挙動が読みにくい | デモ初期採用は慎重 |
| `DeepSeek-V3.1` | Models sold directly by Azure | 不要 | 可 | Azure AI Model Inference API | docs 上言語は `en`/`zh` 記載 | 日本語用途では優先度低 |

### 事実
- 公式ドキュメント上、`Mistral-Large-3` は `ja` を含む複数言語対応。
- 公式ドキュメント上、`DeepSeek-V3.1` は `en` と `zh` の記載。

### 推測
- Foundry を本線にするより、既存 Azure OpenAI を本線、Foundry は将来拡張または保険に留める方が安全。

## 推奨アーキテクチャ

`iPad Safari -> 教室内 localhost Web アプリ -> ローカル API サーバー -> Azure Vision Read OCR -> OCR 正規化/構造化 -> Azure OpenAI(gpt-4o-mini) -> 講師承認 UI -> 宿題提案返却`

### メリット
- GPU VM 不要。
- 既存 AOAI と新規作成済み Vision F0 で最短構成を組める。
- ローカル UI と API を教室内に置くことで「edge に寄せた設計」の説明がしやすい。
- OCR/LLM をクラウドに逃がすので、MVP の実装難度とデモ成功率が下がる。

### リスク
- Wi-Fi 品質に依存。
- OCR の誤認識が downstream の分析品質を左右する。
- 数式・丸付け・訂正痕跡は OCR だけでは不十分。
- 既存 OpenAI リソースを共用する場合、他用途とレート制限が競合する可能性がある。

### デモ説明ポイント
- 「端末で撮影、教室内ローカル UI で確認、解析は Azure、最終判断は講師」が分かりやすい。
- 将来は OCR コンテナやローカル推論への差し替えで edge 化できる設計、と説明可能。

## 作成すべき Azure リソース一覧

### そのまま使う
- `schooladminocr23088` (`ComputerVision`, `F0`, `school-admin-precheck-rg`)
- `sitcopilotaoai23088` + `sit-copilot-demo-chat`

### 必要なら作る
- デモ用専用 RG
  - ただし `school-admin-precheck-rg` を流用するなら新規不要。
- `Key Vault`
  - 秘密情報をローカル環境変数に直置きしない方針にする場合のみ。
- `Storage`
  - 画像保存や監査ログを Azure 側に残す要件が出た場合のみ。

## 作成しない方がよいリソース一覧

- GPU VM
  - 理由: 今回の要件では不要。コストと運用負担が高い。
- Azure AI Foundry hub/project の新規作成
  - 理由: Student 制約、`Microsoft.MachineLearningServices` 未登録、Marketplace 条件の不確実性が大きい。
- Marketplace 同意が必要な partner/community model
  - 理由: 方針違反になりやすく、審査・再現性・費用面でも不利。
- PostgreSQL / Search / ACR / Container Apps の新規追加
  - 理由: MVP 調査段階では過剰。

## コスト / 制約 / リスク

### 事実
- Vision `ComputerVision` は `F0` が利用可能で実作成済み。
- Azure OpenAI は既存リソースを再利用できる。

### 推測
- Student クレジットで今回の MVP デモは十分賄える可能性が高い。
- コスト主要因は Azure OpenAI のトークン消費と、もし Vision を `S1` に上げる場合の OCR リクエスト量。
- コストを抑えるには以下が有効。
  - OCR は必要ページのみ送る
  - 画像を前処理して不要背景を減らす
  - LLM には OCR 全文を丸投げせず、問題番号単位で構造化してから送る
  - デモでは短い出力と少ない再試行にする

### 本番デモ運用の注意
- 教室 Wi-Fi 不調に備えて OCR/LLM リクエストのタイムアウトと再送方針を決める。
- 画像サイズを制御してアップロード遅延を避ける。
- 講師承認 UI を必須にして OCR/LLM 誤りを吸収する。
- 既存 AOAI のレート制限競合を避けるため、デモ時間帯に他ワークロードを止めるか確認する。

## ローカルエッジらしさの説明材料

### 本来ローカルに寄せられる部分
- 画像アップロード UI
- OCR 前処理
- OCR コンテナ化
- OCR 後の構造化
- 将来のローカル小型モデル推論
- 教室内キャッシュと教室内完結データフロー

### 今回クラウドに逃がす部分
- OCR 実行本体
- LLM 推論本体

### 説明の仕方
- 今回は「デモ成功率優先」で Azure 推論を採用。
- ただし I/O 境界はローカル API に閉じており、将来的には OCR コンテナやローカル LLM に差し替えやすい。
- 教室内 UI と講師承認フローはローカル中心で、完全クラウド依存の UX ではない。

## SPEC.md 作成前に確定すべきこと

- 既存 AOAI `sitcopilotaoai23088` を本デモで共用してよいか。
- OCR に投げる答案フォーマットをどこまで標準化できるか。
- MVP で扱う数学単元と問題番号体系。
- 宿題提案の粒度を「問題番号のみ」に固定してよいか。
- OCR 誤認識時に講師がどこまで手修正するか。
- デモ時のネットワーク前提と fallback 手順。

## 次に着手すべき実装順

1. OCR 入力対象のサンプル答案を確定する。
2. OCR 出力を「問題番号・回答・判定メモ」に正規化する中間 JSON 仕様を決める。
3. その JSON を入力にした LLM プロンプト設計を決める。
4. 講師承認 UI の最低限の操作フローを決める。
5. その後にのみ SPEC.md を確定する。

## 参考ソース

- Azure Foundry serverless deployment: https://learn.microsoft.com/en-us/azure/foundry-classic/how-to/deploy-models-serverless
- Models sold directly by Azure: https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure
- Azure AI Model Inference API: https://learn.microsoft.com/en-us/azure/ai-foundry/model-inference/reference/reference-model-inference-api
- Azure Vision OCR overview: https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/overview-ocr
- Azure Vision language support: https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/language-support
- Azure Vision Read container: https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/computer-vision-how-to-install-containers
