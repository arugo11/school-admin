from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


NOW = datetime(2026, 3, 16, 12, 0, tzinfo=timezone.utc)


def _dt(days_ago: int) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


STUDENT_DETAILS = {
    "s-01": {
        "documents": [
            ("test_report", "確認テスト", "数学は処理が遅めだが, 手順は守れている。"),
            ("mock_exam", "塾内模試", "英語偏差値は 53 -> 47 -> 51 と回復傾向。"),
            ("homework_history", "宿題履歴", "宿題量が多いと不満が出るため, 量を調整して継続。"),
            ("teacher_note", "講師メモ", "入塾初期に宿題量への不満が強かったため, 量は最小限で達成体験を優先。英語は偏差値 53→47→51 のため, 週2回の語彙確認を継続。"),
        ],
        "metrics": [("homework_completion_rate", 84), ("recent_test_score", 68), ("absence_count", 0), ("weak_unit_count", 1)],
        "homework": [(["A-03"], "appropriate", "completed", "英語と並行して短く復習")],
    },
    "s-02": {
        "documents": [
            ("test_report", "確認テスト", "総合力は高い。数学だけ相対的にミスが出る。"),
            ("mock_exam", "塾内模試", "理科・英語は高得点を維持。"),
            ("homework_history", "宿題履歴", "難問を含めても概ね完了。"),
            ("teacher_note", "講師メモ", "理科・英語は満点帯。数学だけ相対的に落ちるため, 授業後半に応用1題を固定で入れて上限を伸ばす。"),
        ],
        "metrics": [("homework_completion_rate", 94), ("recent_test_score", 91), ("absence_count", 0), ("weak_unit_count", 1)],
        "homework": [(["C-03"], "appropriate", "completed", "数学応用を追加")],
    },
    "s-03": {
        "documents": [
            ("test_report", "確認テスト", "得意科目は未確立。基礎計算で取りこぼし。"),
            ("mock_exam", "塾内模試", "平均点付近だが, 伸び幅は小さい。"),
            ("homework_history", "宿題履歴", "提出はできるが習熟不足で再ミスが多い。"),
            ("counseling_memo", "面談メモ", "危機感はある。毎回の確認で前進したい。"),
            ("teacher_note", "講師メモ", "2月入塾。得意科目がないため, まず計算と式変形を授業冒頭10分で毎回チェック。危機感はあるので声掛けは短く具体的に。"),
        ],
        "metrics": [("homework_completion_rate", 72), ("recent_test_score", 61), ("absence_count", 0), ("weak_unit_count", 3)],
        "homework": [(["A-02"], "light", "partial", "危機感維持のため基礎優先")],
    },
    "s-04": {
        "documents": [
            ("test_report", "確認テスト", "やる気の波で得点がぶれる。"),
            ("mock_exam", "塾内模試", "一科目集中時は改善幅が大きい。"),
            ("teacher_note", "講師メモ", "やる気の波が大きい。数学か英語のどちらか1科目を週単位で重点化し, atama+は単元単位で区切って完了判定を出す。"),
        ],
        "metrics": [("homework_completion_rate", 66), ("recent_test_score", 69), ("absence_count", 0), ("weak_unit_count", 2)],
        "homework": [(["B-03"], "appropriate", "partial", "単元単位で管理")],
    },
    "s-05": {
        "documents": [
            ("mock_exam", "塾内模試", "定期テスト重視で範囲学習に寄せる必要あり。"),
            ("attendance", "出欠", "部活動で土日の学習時間が確保しづらい。"),
            ("homework_history", "宿題履歴", "平日提出は安定, 週末課題は未達。"),
            ("teacher_note", "講師メモ", "土日は野球で学習時間が取れない。私立志望の内申条件を意識し, 定期テスト範囲を平日に全振りで進める。"),
        ],
        "metrics": [("homework_completion_rate", 57), ("recent_test_score", 66), ("absence_count", 1), ("weak_unit_count", 2)],
        "homework": [(["B-02"], "appropriate", "partial", "平日配分で実行")],
    },
    "s-06": {
        "documents": [
            ("test_report", "確認テスト", "全体的に安定して高水準。"),
            ("mock_exam", "塾内模試", "定期前も得点を維持。"),
            ("homework_history", "宿題履歴", "提出品質ともに良好。"),
            ("teacher_note", "講師メモ", "新中2の中では安定して高水準。授業では先取り1題のみ追加し, 基本は現状維持で負荷を増やしすぎない。"),
        ],
        "metrics": [("homework_completion_rate", 92), ("recent_test_score", 90), ("absence_count", 0), ("weak_unit_count", 1)],
        "homework": [(["C-04"], "appropriate", "completed", "維持セット")],
    },
    "s-07": {
        "documents": [
            ("test_report", "確認テスト", "やる気の波で正答率がぶれる。"),
            ("mock_exam", "塾内模試", "集中時の伸びは大きい。"),
            ("homework_history", "宿題履歴", "単元単位なら完走しやすい。"),
            ("teacher_note", "講師メモ", "一科目を上げる方針が有効。週初めに数学 or 英語の重点を決め, 目標未達時は翌週も同科目を継続。"),
        ],
        "metrics": [("homework_completion_rate", 66), ("recent_test_score", 69), ("absence_count", 0), ("weak_unit_count", 2)],
        "homework": [(["B-03"], "appropriate", "partial", "重点科目方式")],
    },
    "s-08": {
        "documents": [
            ("test_report", "確認テスト", "数学英語は平均超え。"),
            ("mock_exam", "塾内模試", "理科の難問で失点。"),
            ("homework_history", "宿題履歴", "理科課題は分割で実行。"),
            ("teacher_note", "講師メモ", "数学と英語は平均点超え。理科は入試形式で難しいため, 宿題は易問→標準の2段階に分けて出す。"),
        ],
        "metrics": [("homework_completion_rate", 74), ("recent_test_score", 71), ("absence_count", 0), ("weak_unit_count", 1)],
        "homework": [(["B-04"], "appropriate", "completed", "理科対応を含む")],
    },
    "s-09": {
        "documents": [
            ("test_report", "確認テスト", "定期範囲問題は正答できる。"),
            ("attendance", "出欠", "部活で土日の学習時間が不足。"),
            ("homework_history", "宿題履歴", "平日は提出, 週末は未達。"),
            ("teacher_note", "講師メモ", "定期テスト重視。オール3+4を満たすため, 数学・保体など内申に効く科目を優先して平日配分を固定。"),
        ],
        "metrics": [("homework_completion_rate", 57), ("recent_test_score", 66), ("absence_count", 1), ("weak_unit_count", 2)],
        "homework": [(["B-02"], "appropriate", "partial", "平日配分セット")],
    },
    "s-10": {
        "documents": [
            ("test_report", "確認テスト", "基礎問題での失点が多い。"),
            ("attendance", "出欠", "遅刻が多く授業立ち上がりが遅い。"),
            ("homework_history", "宿題履歴", "提出遅れが目立つ。"),
            ("teacher_note", "講師メモ", "授業態度と遅刻が課題。学習内容より先に行動管理を優先し, 提出期限を当日中に短縮して運用。"),
        ],
        "metrics": [("homework_completion_rate", 44), ("recent_test_score", 50), ("absence_count", 2), ("weak_unit_count", 3)],
        "homework": [(["A-01"], "light", "missed", "最小課題で習慣化")],
    },
    "s-11": {
        "documents": [
            ("test_report", "確認テスト", "数学・理科・英語が課題。"),
            ("mock_exam", "塾内模試", "モチベーション低下で失点増。"),
            ("homework_history", "宿題履歴", "図形課題は着手できる。"),
            ("teacher_note", "講師メモ", "モチベーション低下。3-4月は数学を軸に再起動し, 春季テキストの図形を毎回1セットずつ完了させる。"),
        ],
        "metrics": [("homework_completion_rate", 52), ("recent_test_score", 58), ("absence_count", 0), ("weak_unit_count", 3)],
        "homework": [(["B-01"], "light", "partial", "図形再起動セット")],
    },
    "s-12": {
        "documents": [
            ("test_report", "確認テスト", "平均点より上を維持。"),
            ("mock_exam", "塾内模試", "安定して上位帯。"),
            ("homework_history", "宿題履歴", "定期前の提出も安定。"),
            ("teacher_note", "講師メモ", "新中3は1学期の定期テストを最優先。平均点より上を維持できるので, 先取りよりも取りこぼし防止を重視。"),
        ],
        "metrics": [("homework_completion_rate", 86), ("recent_test_score", 80), ("absence_count", 0), ("weak_unit_count", 1)],
        "homework": [(["C-02"], "appropriate", "completed", "中3定期対策")],
    },
    "s-13": {
        "documents": [
            ("test_report", "確認テスト", "数学96点。計算精度が高い。"),
            ("mock_exam", "塾内模試", "上位を維持。"),
            ("homework_history", "宿題履歴", "高難度問題まで完了。"),
            ("teacher_note", "講師メモ", "数学96点を維持。E中学校は中間テストがあるため, 数学は維持運用にして英語学習時間を確保する。"),
        ],
        "metrics": [("homework_completion_rate", 93), ("recent_test_score", 95), ("absence_count", 0), ("weak_unit_count", 1)],
        "homework": [(["C-07"], "appropriate", "completed", "高得点維持セット")],
    },
    "s-14": {
        "documents": [
            ("test_report", "確認テスト", "数学は維持, 英語課題が中心。"),
            ("mock_exam", "塾内模試", "英語で失点が目立つ。"),
            ("homework_history", "宿題履歴", "英語課題優先で数学は維持。"),
            ("teacher_note", "講師メモ", "中3の英語課題が大きい。定期前は数学を維持しつつ, 英語の語彙と文法の補強を優先して配分。"),
        ],
        "metrics": [("homework_completion_rate", 68), ("recent_test_score", 63), ("absence_count", 0), ("weak_unit_count", 2)],
        "homework": [(["B-05"], "appropriate", "partial", "英語時間確保")],
    },
    "s-15": {
        "documents": [
            ("test_report", "確認テスト", "英語文法で失点。"),
            ("mock_exam", "塾内模試", "語彙不足で伸び悩み。"),
            ("homework_history", "宿題履歴", "解き直しは実施できる。"),
            ("teacher_note", "講師メモ", "英語文法の抜けが継続。短い文法課題を高頻度で回し, 解き直しの速度も記録する。"),
        ],
        "metrics": [("homework_completion_rate", 66), ("recent_test_score", 62), ("absence_count", 0), ("weak_unit_count", 2)],
        "homework": [(["B-06"], "light", "completed", "英語基礎補強")],
    },
    "s-16": {
        "documents": [
            ("test_report", "確認テスト", "英語基礎と提出遅れが課題。"),
            ("attendance", "出欠", "提出期限の遅れが複数回。"),
            ("homework_history", "宿題履歴", "必須問題は完了, 追加問題は未達。"),
            ("teacher_note", "講師メモ", "英語課題と提出遅れの両方がある。提出期限を短く固定し, 未提出時は次回冒頭で即フォロー。"),
        ],
        "metrics": [("homework_completion_rate", 60), ("recent_test_score", 61), ("absence_count", 1), ("weak_unit_count", 2)],
        "homework": [(["A-04"], "light", "partial", "期限固定セット")],
    },
}


def build_seed_documents(student_id: str) -> list[dict]:
    documents = []
    for index, (document_type, title, body_text) in enumerate(STUDENT_DETAILS[student_id]["documents"]):
        documents.append(
            {
                "student_id": student_id,
                "document_type": document_type,
                "title": title,
                "body_text": body_text,
                "source_system": "seed",
                "authored_by": "teacher",
                "document_date": _dt(5 - index),
            }
        )
    return documents


def build_seed_metrics(student_id: str) -> list[dict]:
    return [
        {
            "student_id": student_id,
            "metric_type": metric_type,
            "metric_value": metric_value,
            "metric_date": _dt(1),
        }
        for metric_type, metric_value in STUDENT_DETAILS[student_id]["metrics"]
    ]


def build_seed_homework(student_id: str) -> list[dict]:
    rows = []
    for index, (groups, expected_load, status, comment) in enumerate(STUDENT_DETAILS[student_id]["homework"]):
        rows.append(
            {
                "student_id": student_id,
                "assigned_date": _dt(3 + index),
                "approved_problem_groups": json.dumps(groups, ensure_ascii=False),
                "expected_load": expected_load,
                "completion_status": status,
                "teacher_comment": comment,
                "created_at": _dt(3 + index),
            }
        )
    return rows
