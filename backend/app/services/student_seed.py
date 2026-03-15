from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


NOW = datetime(2026, 3, 16, 12, 0, tzinfo=timezone.utc)


def _dt(days_ago: int) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


STUDENT_DETAILS = {
    "s-01": {
        "summary": "努力量は安定しているが, 正答率の伸びが鈍い.",
        "documents": [
            ("test_report", "2026-03-10 確認テスト報告", "分配法則では手順は合っているが, 符号反転ミスが2問続いた. 基礎計算は維持."),
            ("homework_history", "2026-03-12 宿題実施履歴", "提出は完了. ただし解き直し欄が薄く, 類題で同じミスが再発."),
            ("counseling_memo", "2026-03-13 面談メモ", "本人は量を増やしているが, どこで間違えたかを言語化できていない."),
            ("teacher_note", "2026-03-15 講師メモ", "努力は高い. 量を増やすより, 毎回1問だけ原因説明を入れたい."),
            ("mock_exam", "2026-02-28 模試結果", "偏差値は横ばい. 基礎計算は平均以上, 方程式応用で失点."),
            ("score_trend", "2026-03 成績推移", "確認テスト 63 -> 64 -> 64. 宿題提出率は高いが得点上昇は限定的."),
            ("attendance", "2026-03 出欠サマリ", "出席は安定. 遅刻なし."),
        ],
        "metrics": [("homework_completion_rate", 92), ("recent_test_score", 64), ("absence_count", 0), ("weak_unit_count", 2)],
        "homework": [(["A-03", "A-04"], "appropriate", "completed", "分配法則を中心に復習"), (["A-05", "A-07"], "light", "completed", "見直し重視へ調整")],
    },
    "s-02": {
        "summary": "宿題未達が多く, 量より達成可能性の再設計が必要.",
        "documents": [
            ("test_report", "2026-03-09 確認テスト報告", "移項で符号ミス, 途中式の省略が多い. 基礎計算も不安定."),
            ("homework_history", "2026-03-11 宿題実施履歴", "3問中1問のみ実施. 未提出理由は時間切れ."),
            ("teacher_note", "2026-03-14 講師メモ", "短い宿題で成功体験を積ませたい."),
            ("counseling_memo", "2026-03-08 面談メモ", "家庭学習時間が短く, 宿題開始が遅い."),
            ("score_trend", "2026-03 成績推移", "52 -> 55 -> 58 と微増."),
            ("attendance", "2026-03 出欠サマリ", "出席は安定."),
            ("mock_exam", "2026-03-01 模試結果", "基礎計算の得点率が低い."),
        ],
        "metrics": [("homework_completion_rate", 38), ("recent_test_score", 58), ("absence_count", 0), ("weak_unit_count", 3)],
        "homework": [(["A-01", "A-02"], "light", "partial", "量を半分にした"), (["A-05"], "light", "missed", "未達が続く")],
    },
    "s-03": {
        "summary": "努力しているが, 分配法則と符号処理の定着不足で伸び悩み.",
        "documents": [
            ("test_report", "2026-03-10 確認テスト報告", "分配法則の符号処理で同系統の誤答が反復. 解き直しはあるが浅い."),
            ("test_report", "2026-03-03 確認テスト報告", "一次方程式の整理は概ね良いが, マイナスの扱いで失点."),
            ("homework_history", "2026-03-12 宿題実施履歴", "提出は完了. ただし類題A-04で同じミスを再発."),
            ("homework_history", "2026-03-05 宿題実施履歴", "A-03は自力完了, A-04は講師補助あり."),
            ("counseling_memo", "2026-03-13 面談メモ", "本人は頑張っているが, 何を直せばよいか分からず不安."),
            ("teacher_note", "2026-03-14 講師メモ", "量よりも符号ミスの原因説明を優先したい."),
            ("mock_exam", "2026-02-27 模試結果", "基礎は平均並み, 方程式応用で減点."),
            ("score_trend", "2026-03 成績推移", "61 -> 64 -> 63. 伸び切らない."),
            ("attendance", "2026-03 出欠サマリ", "出席は安定, 授業態度は前向き."),
        ],
        "metrics": [("homework_completion_rate", 84), ("recent_test_score", 63), ("absence_count", 0), ("weak_unit_count", 2)],
        "homework": [(["A-03", "A-04"], "appropriate", "completed", "努力量は十分"), (["A-05", "A-07"], "light", "completed", "見直しの質は要改善")],
    },
    "s-04": {
        "summary": "模試は高いが, 直近確認テストで基礎の取りこぼしが出た.",
        "documents": [
            ("test_report", "2026-03-10 確認テスト報告", "関数の読み取りは良いが, 単純計算の見直し不足で失点."),
            ("mock_exam", "2026-03-02 模試結果", "上位帯を維持. 関数は高得点."),
            ("teacher_note", "2026-03-12 講師メモ", "応用は解けるが, 基礎を雑に処理する傾向."),
            ("score_trend", "2026-03 成績推移", "89 -> 92 -> 90."),
            ("attendance", "2026-03 出欠サマリ", "出席安定."),
            ("homework_history", "2026-03-11 宿題実施履歴", "応用問題は完了. 基礎見直し課題は省略."),
        ],
        "metrics": [("homework_completion_rate", 76), ("recent_test_score", 90), ("absence_count", 0), ("weak_unit_count", 1)],
        "homework": [(["C-01", "A-07"], "appropriate", "completed", "見直し課題を混ぜる"), (["C-02"], "appropriate", "completed", "応用は維持")],
    },
    "s-05": {
        "summary": "出欠と宿題の両方が不安定で, 学習リズムの再建が先.",
        "documents": [
            ("attendance", "2026-03 出欠サマリ", "この2週間で欠席2回, 遅刻1回."),
            ("homework_history", "2026-03-12 宿題実施履歴", "未提出. 前回も一部未達."),
            ("counseling_memo", "2026-03-07 面談メモ", "家庭都合で学習時間が取りづらい."),
            ("test_report", "2026-03-09 確認テスト報告", "分数計算の約分で失点が続く."),
            ("score_trend", "2026-03 成績推移", "45 -> 49 -> 50."),
            ("teacher_note", "2026-03-14 講師メモ", "まずは出席時に短い成功体験を作る."),
        ],
        "metrics": [("homework_completion_rate", 24), ("recent_test_score", 50), ("absence_count", 2), ("weak_unit_count", 3)],
        "homework": [(["B-01"], "light", "missed", "未提出"), (["B-01", "A-07"], "light", "partial", "量を絞って再提案")],
    },
    "s-06": {
        "summary": "基礎は良いが, 応用で止まりやすく段階的な負荷調整が必要.",
        "documents": [
            ("test_report", "2026-03-11 確認テスト報告", "基礎計算は安定. 関数の変域で手が止まる."),
            ("mock_exam", "2026-03-01 模試結果", "基礎は良好, 応用は半分程度."),
            ("teacher_note", "2026-03-13 講師メモ", "基礎から応用への橋渡し問題を増やしたい."),
            ("homework_history", "2026-03-12 宿題実施履歴", "標準問題は完了, 応用大問は未着手."),
            ("score_trend", "2026-03 成績推移", "72 -> 70 -> 76."),
            ("attendance", "2026-03 出欠サマリ", "安定."),
        ],
        "metrics": [("homework_completion_rate", 71), ("recent_test_score", 76), ("absence_count", 0), ("weak_unit_count", 2)],
        "homework": [(["C-01"], "appropriate", "completed", "標準は解ける"), (["C-02"], "heavy", "partial", "応用は負荷高め")],
    },
}


def build_seed_documents(student_id: str) -> list[dict]:
    detail = STUDENT_DETAILS[student_id]
    documents = []
    for index, (document_type, title, body_text) in enumerate(detail["documents"]):
        documents.append(
            {
                "student_id": student_id,
                "document_type": document_type,
                "title": title,
                "body_text": body_text,
                "source_system": "seed",
                "authored_by": "system" if document_type in {"test_report", "score_trend", "attendance", "mock_exam", "homework_history"} else "teacher",
                "document_date": _dt(15 - index),
            }
        )
    return documents


def build_seed_metrics(student_id: str) -> list[dict]:
    detail = STUDENT_DETAILS[student_id]
    return [
        {
            "student_id": student_id,
            "metric_type": metric_type,
            "metric_value": metric_value,
            "metric_date": _dt(4),
        }
        for metric_type, metric_value in detail["metrics"]
    ]


def build_seed_homework(student_id: str) -> list[dict]:
    detail = STUDENT_DETAILS[student_id]
    rows = []
    for index, (groups, expected_load, status, comment) in enumerate(detail["homework"]):
        rows.append(
            {
                "student_id": student_id,
                "assigned_date": _dt(10 - index * 4),
                "approved_problem_groups": json.dumps(groups, ensure_ascii=False),
                "expected_load": expected_load,
                "completion_status": status,
                "teacher_comment": comment,
                "created_at": _dt(10 - index * 4),
            }
        )
    return rows
