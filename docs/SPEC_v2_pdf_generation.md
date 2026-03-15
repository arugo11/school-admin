# SPEC.md

## 1. 文書の目的

本書は, 既存 MVP に対して, 展示会用の本格的な確認テスト PDF 自動生成機能を追加するための拡張仕様書である.
既存システムの主経路である `upload -> OCR review -> analysis -> homework approval` は維持しつつ, デモ当日に来場者へ配布する確認テストを自動生成できるようにする.

本拡張の目的は次の3点である.

1. 来場者参加型デモで使う, 問題数の多い確認テストを安定して量産できるようにすること.
2. 問題の出典, 難易度, 問題番号, 正答を機械可読な形で保持し, OCR / 分析 / 宿題提案の downstream と整合させること.
3. Codex が自律的に実装, 評価, 修正のループを回せるように, PDF 生成機能の要件, 成功条件, 評価方法を明文化すること.

## 2. 背景

展示デモでは, 来場者に短すぎる3問ではなく, もう少し本格的な確認テストを解いてもらい, その場で撮影, OCR, 分析, 宿題提案まで体験してもらう方がデモ体験の得点に効く.
一方で, 問題が増えるほど, 出題品質, 版面品質, OCR しやすい解答欄設計, 正答管理, 再生成性が重要になる.

そのため, 本システムには次の追加機能が必要である.

- Hugging Face 上の日本語 MATH-500 系データから問題を選ぶ
- 確認テスト PDF を自動生成する
- 解答欄が大きく, OCR しやすい紙面を出力する
- 解答例 / 正答キー / manifest JSON を同時生成する
- テストごとに stable な `test_id` を持ち, 後続処理と紐付ける

## 3. データソース方針

### 3.1 主データソース

主データソースは Hugging Face の日本語 MATH-500 系データとする.
最優先候補は, 日本語 config が明示されている多言語 MATH-500 系データである.

### 3.2 取り扱い方針

データソース名は内部では `math-500-jp` を論理名として扱ってよい.
ただし, 実際の取得元は設定ファイルまたは CLI 引数で切り替え可能にする.

最低限, 次の2段階フォールバックを持つこと.

1. primary: `appier-ai-research/Multilingual-MATH-500` の `Japanese` subset
2. fallback: `jacobmorrison/MATH-500-japanese`

### 3.3 出典追跡

各問題について, 少なくとも次を保持すること.

- `source_dataset`
- `source_config`
- `source_split`
- `source_unique_id`
- `source_subject`
- `source_level`
- `source_problem`
- `source_answer`

## 4. 拡張スコープ

### 4.1 追加する機能

今回追加する必須機能は以下である.

- 日本語 MATH-500 系データの取得
- 問題選択ロジック
- 確認テスト PDF 自動生成
- 解答キー PDF または answer sheet 生成
- manifest JSON 生成
- 既存 catalog / analysis pipeline との対応関係生成
- OCR しやすい解答欄レイアウト
- デモ用に複数 seed での再生成

### 4.2 今回やらないこと

- 数学教師向けの高度な手動編集 GUI
- 問題文の自動書き換えや自動翻案
- 大規模なカリキュラム最適化
- MATH-500 全問をそのまま教室教材化すること
- 学習指導要領との厳密マッピング

## 5. デモでの使い方

### 5.1 目的

展示デモでは, 来場者が確認テストの一部または全部を解き, それを iPad で撮影して分析に流す.
確認テストは次の条件を満たす必要がある.

- 見た目が「塾の確認テスト」らしい
- 1ページまたは 2ページで回せる
- 解答欄が十分大きい
- 問題番号が OCR しやすく明確
- テスト ID が紙面に載る
- 正答と出題メタデータが manifest で機械可読

### 5.2 推奨デフォルト

デモ用デフォルトは以下とする.

- 問題数: 8〜12問
- ページ数: 2ページ以内を第一候補
- 難易度帯: 易しめ〜中程度中心
- 単元の偏りを避ける
- 各問題に十分な記述欄を用意する

## 6. 生成物

PDF 生成スクリプトは, 1回の実行で最低限以下を生成すること.

1. `confirmation_test.pdf`
2. `answer_key.pdf` または `answer_key.md`
3. `manifest.json`
4. `selected_problems.json`
5. 必要なら `preview.png` または `preview.html`

### 6.1 confirmation_test.pdf の必須要素

- タイトル, 例: `確認テスト`
- `test_id`
- 作成日時
- ページ番号
- 受験者記入欄, 例: 名前, 学年, 時間
- 各問題の問題番号
- 問題文
- 十分な解答スペース
- OCR 用の視認しやすい解答欄
- 下部余白に撮影ガイド, 任意

### 6.2 answer_key の必須要素

- `test_id`
- 問題番号ごとの正答
- 出典 ID
- 単元, 難易度, メモ, 任意

### 6.3 manifest.json の必須要素

```json
{
  "test_id": "ct-20260315-001",
  "source_alias": "math-500-jp",
  "source_dataset": "appier-ai-research/Multilingual-MATH-500",
  "source_config": "Japanese",
  "generated_at": "ISO-8601",
  "generator_version": "string",
  "seed": 42,
  "problem_count": 10,
  "layout": {
    "page_size": "A4",
    "columns": 1
  },
  "problems": [
    {
      "display_no": 1,
      "problem_id": "...",
      "subject": "...",
      "level": 2,
      "answer": "...",
      "estimated_minutes": 3,
      "catalog_problem_no": "CT-001-Q01"
    }
  ]
}
```

## 7. 実装要件

### 7.1 追加スクリプト

最低限, 次の CLI を実装すること.

```bash
python scripts/generate_confirmation_test.py \
  --dataset-source huggingface \
  --dataset-name appier-ai-research/Multilingual-MATH-500 \
  --dataset-config Japanese \
  --split test \
  --count 10 \
  --seed 42 \
  --difficulty-min 1 \
  --difficulty-max 3 \
  --output-dir data/generated/tests/demo-001 \
  --with-answer-key
```

### 7.2 推奨オプション

- `--count`
- `--seed`
- `--difficulty-min`
- `--difficulty-max`
- `--subject-include`
- `--subject-exclude`
- `--max-pages`
- `--target-minutes`
- `--template`
- `--with-answer-key`
- `--test-id`
- `--shuffle`
- `--preview-only`

### 7.3 スクリプトの責務

- Hugging Face データ取得
- 問題候補のフィルタ
- 問題の選抜
- ページレイアウト決定
- PDF 出力
- answer key 出力
- manifest 出力
- 失敗時の原因メッセージ出力

## 8. レンダリング要件

### 8.1 数式レンダリング

問題文には LaTeX 由来の数式が含まれる可能性が高い.
そのため, PDF 生成は plain text 埋め込みではなく, 数式の可読性を保てる方法で行うこと.

実装方針は次の優先順を推奨する.

1. HTML + KaTeX + Playwright PDF
2. Typst が安定利用可能なら Typst
3. 上記が難しい場合, 最低限の数式可読性を確保できる代替手段

重要なのは, 数式が崩れず, 紙として配れる品質であること.

### 8.2 OCR フレンドリー設計

- 問題番号は太字かつ明確に分離
- 解答欄は十分に広い
- 問題文と解答欄の境界を明確にする
- 行間と余白を確保する
- 1ページあたりの詰め込みすぎを避ける
- 手書き回答が重ならないようにする

## 9. 既存システムとの統合

### 9.1 catalog 連携

生成した確認テストの各問題には, 既存 catalog とは別系統でもよいので stable な `catalog_problem_no` を振ること.
後段の OCR / analysis では, 少なくとも `test_id + display_no` から manifest の問題メタデータへ戻れること.

### 9.2 OCR 連携

OCR 側は, 少なくとも以下を認識できる構造を想定する.

- `test_id`
- `display_no`
- answer region
- 任意で page number

### 9.3 analysis 連携

分析時には manifest から次を参照できること.

- 問題の正答
- 難易度
- 単元
- 出題順
- 推定所要時間

## 10. ディレクトリ要件

推奨構成は以下とする.

```text
scripts/
  generate_confirmation_test.py
  preview_confirmation_test.py  # 任意

backend/
  ... 既存コード

data/
  source/
    math500jp/
  generated/
    tests/
      demo-001/
        confirmation_test.pdf
        answer_key.pdf
        manifest.json
        selected_problems.json

templates/
  confirmation_test/
    base.html
    answer_key.html
    styles.css

frontend/
  ... 既存コード

docs/
  runlogs/
  evals/
  CONFIRMATION_TEST_RUNBOOK.md
```

## 11. 評価要件

Codex は, 実装しただけで終わらず, 以下を満たすまで評価と修正を回すこと.

### 11.1 生成品質

- 同じ seed で同じ PDF が再生成される
- 問題数と manifest が一致する
- answer key の正答件数が一致する
- 問題番号の重複がない
- `test_id` が一意である

### 11.2 版面品質

- A4 で印刷可能
- 問題文がページ外にはみ出さない
- 数式が視認可能
- 解答欄が十分大きい
- ページ番号が付与される

### 11.3 OCR 適性

- 生成した確認テストを自分で印刷または模擬筆記し, 再撮影したときに OCR 経路が破綻しない
- 少なくとも 3 種類以上の実筆記サンプルで upload -> OCR review が成立する
- 問題番号認識と回答欄対応が破綻しにくい

### 11.4 統合品質

- 生成したテストで, upload -> OCR review -> analysis -> homework approval が動く
- `manifest.json` から analysis に必要な正答メタデータが参照できる
- 既存 replay path を壊さない

### 11.5 デモ品質

- 展示用 1セット, バックアップ用 1セット以上を別 seed で生成できる
- 来場者に配布する紙面として違和感が少ない
- 問題数を増やしても, 司会つきで 2〜4 分程度の体験に収まる構成が取れる

## 12. 失敗ループ防止ルール

Codex は次を守ること.

- 同じ PDF レンダリング手法で 2 回続けて詰まったら, 3 回目の前にレンダリング手法を切り替える
- 数式崩れを CSS 微調整だけで延々追わない
- データ取得失敗時は dataset source fallback を試す
- 版面過密は問題数を減らすかページ数を増やして解決する
- OCR 不安定を LLM 側で無理に吸収し続けない. まず紙面設計を見直す
- 実印刷 / 実撮影評価をせずに「大丈夫そう」で終わらない

## 13. 実装順序

1. 既存 repo と現実装を scan する
2. データソース取得の疎通を確認する
3. selected_problems.json と manifest.json の生成を先に作る
4. HTML または Typst テンプレートで PDF を生成する
5. answer key を生成する
6. 固定 seed での再現性テストを入れる
7. 生成 PDF を既存 OCR パイプラインで流してみる
8. 版面と answer region を調整する
9. runbook と eval docs を整備する

## 14. 追加成果物

最低限, 次の成果物を追加すること.

- `scripts/generate_confirmation_test.py`
- `templates/confirmation_test/*`
- `docs/CONFIRMATION_TEST_RUNBOOK.md`
- `docs/evals/confirmation_test_generation_eval.md`
- `docs/evals/confirmation_test_ocr_eval.md`
- `data/generated/tests/demo-001/*`
- `.env.example` の必要更新, もしあれば

## 15. Codex への重要指示

- 既存 MVP を壊さずに拡張する
- まず manifest と selected problems を正しく作る
- PDF は見た目より, 数式可読性と OCR しやすさを優先する
- 問題選定ロジックは deterministic にする
- 再現性, 印刷可能性, OCR 適性の3点を重視する
- Hugging Face CLI とローカル RTX5090 は使ってよいが, 本線は既存 Azure デモを壊さないこと

