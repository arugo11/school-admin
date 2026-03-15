# Student Dashboard UI Eval

Date: 2026-03-16

## Checked Points
- `/students` 上部に教室全体サマリを表示: pass
- 6人分カードに以下を表示:
  - 生徒名
  - 学年
  - 宿題達成率
  - 一言AI分析
  - 推奨対応
  - Result: pass
- 右ペイン詳細:
  - 現在の状態
  - 危険信号
  - 次に打つべき手
  - 推奨対応
  - 根拠文書タイトル3件
  - ドキュメント一覧
  - 宿題履歴
  - 講師メモ追加
  - Result: pass
- 既存 happy path 導線:
  - 各カードから `この生徒で答案確認へ`
  - 既存 upload flow へ遷移可能
  - Result: pass

## Validation
- `cd frontend && npm test`
- `cd frontend && npm run build`

## Notes
- 右ペイン方式により, 一覧を主役に保ったまま詳細を見せられる。
- モバイル幅では1カラムへ落ちるため, iPad Safari のデモ導線を維持しやすい。
