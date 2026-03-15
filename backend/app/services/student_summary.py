from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.schemas import (
    AnalysisResult,
    CatalogProblem,
    NormalizedOcrDocument,
    RagChunkSearchResult,
    RagHomeworkRecommendation,
    RecommendedProblemGroup,
    StudentDocumentResponse,
    StudentHomeworkHistoryItem,
    StudentMetric,
    StudentProfile,
    StudentStateSummary,
)


def _metric_map(metrics: list[StudentMetric]) -> dict[str, float]:
    return {metric.metric_type: metric.metric_value for metric in metrics}


def build_fallback_summary(
    student: StudentProfile,
    metrics: list[StudentMetric],
    retrieved_chunks: list[RagChunkSearchResult],
    documents: list[StudentDocumentResponse],
) -> StudentStateSummary:
    metric_map = _metric_map(metrics)
    preferred_chunks = sorted(
        retrieved_chunks,
        key=lambda chunk: {
            "test_report": 0,
            "homework_history": 1,
            "counseling_memo": 2,
            "teacher_note": 3,
            "mock_exam": 4,
            "score_trend": 5,
            "attendance": 6,
        }.get(chunk.document_type, 7),
    )
    titles = [chunk.title for chunk in preferred_chunks[:3]]
    while len(titles) < 3:
        fallback_title = documents[min(len(titles), len(documents) - 1)].title if documents else f"{student.display_name} 文書"
        titles.append(fallback_title)
    low_completion = metric_map.get("homework_completion_rate", 0) < 60
    absence_risk = metric_map.get("absence_count", 0) >= 2
    top_chunk = preferred_chunks[0].chunk_text if preferred_chunks else student.persona_summary
    current_status = f"{student.display_name}は{top_chunk}"
    risk_signals = []
    if low_completion:
        risk_signals.append("宿題達成率が低く, 宿題量の再設計が必要")
    if absence_risk:
        risk_signals.append("出欠が不安定で学習リズムが崩れやすい")
    if not risk_signals:
        risk_signals.append(f"{student.weakness_history[0]}が直近も継続課題")
    if len(risk_signals) == 1:
        risk_signals.append("同系統のつまずきを授業冒頭で再確認したい")
    next_actions = [
        f"{student.weakness_history[0]}を授業冒頭に短く確認する",
        "宿題は達成可能な量へ再構成する" if low_completion else "根拠を言語化する1問を宿題に含める",
    ]
    recommended_response = "量より定着を優先し, 次回授業で原因説明まで確認する"
    one_line_analysis = student.one_line_analysis or f"{student.weakness_history[0]}が継続課題"
    recommended_action = student.recommended_action or next_actions[0]
    return StudentStateSummary(
        student_id=student.student_id,
        current_status=current_status,
        risk_signals=risk_signals[:2],
        next_best_actions=next_actions[:2],
        recommended_response=recommended_response,
        one_line_analysis=one_line_analysis,
        recommended_action=recommended_action,
        cited_document_titles=titles[:3],
        generated_at=datetime.now(timezone.utc),
        fallback_used=True,
    )


def build_rag_homework_recommendation(
    *,
    student: StudentProfile,
    metrics: list[StudentMetric],
    summary: StudentStateSummary,
    homework_history: list[StudentHomeworkHistoryItem],
    catalog: list[CatalogProblem],
    analysis: AnalysisResult | None,
    normalized_ocr: NormalizedOcrDocument,
) -> RagHomeworkRecommendation:
    metric_map = _metric_map(metrics)
    recent_groups = {group for row in homework_history[:3] for group in row.approved_problem_groups}
    weakness_terms = set(student.weakness_history + (analysis.weak_units if analysis else []))
    desired_units = set()
    if any("分配" in term or "方程式" in term for term in weakness_terms):
        desired_units.add("一次方程式")
    if any("符号" in term for term in weakness_terms):
        desired_units.add("正負の数")
    if any("関数" in term for term in weakness_terms):
        desired_units.add("関数")
    if any("分数" in term for term in weakness_terms):
        desired_units.add("分数計算")
    candidates = []
    for problem in catalog:
        if student.preferred_difficulty == "basic" and problem.difficulty == "advanced":
            continue
        if student.preferred_difficulty == "standard" and metric_map.get("homework_completion_rate", 0) < 50 and problem.difficulty == "advanced":
            continue
        score = problem.priority
        if not desired_units or problem.unit_name in desired_units:
            score += 4
        else:
            score -= 3
        if problem.difficulty == student.preferred_difficulty:
            score += 2
        if metric_map.get("homework_completion_rate", 100) < 50 and problem.estimated_minutes > 10:
            score -= 2
        if problem.problem_no in recent_groups:
            score -= 3
        candidates.append((score, problem))
    ranked = [problem for _, problem in sorted(candidates, key=lambda item: (-item[0], item[1].problem_no))]
    group_count = 2 if metric_map.get("homework_completion_rate", 100) < 60 else 3
    groups = []
    for problem in ranked:
        if any(group.group_id == problem.problem_no for group in groups):
            continue
        groups.append(
            RecommendedProblemGroup(
                group_id=problem.problem_no,
                unit_name=problem.unit_name,
                difficulty=problem.difficulty,
                reason=f"{problem.unit_name}の弱点を, 直近1か月の履歴も踏まえて補強する",
                level_fit_comment=f"{student.preferred_difficulty}帯を超えすぎない範囲で設定",
                supporting_note="類題の連続を避け, 達成可能な量を優先",
                cited_document_titles=summary.cited_document_titles[:3],
                fallback_used=False,
            )
        )
        if len(groups) >= group_count:
            break
    if not groups:
        fallback = catalog[0]
        groups = [
            RecommendedProblemGroup(
                group_id=fallback.problem_no,
                unit_name=fallback.unit_name,
                difficulty=fallback.difficulty,
                reason="安全側の基礎問題へ戻す",
                level_fit_comment="現時点の学力帯に対して安全",
                supporting_note="fallback",
                cited_document_titles=summary.cited_document_titles[:3],
                fallback_used=True,
            )
        ]
    return RagHomeworkRecommendation(
        student_id=student.student_id,
        recommended_problem_groups=groups,
        fallback_used=any(group.fallback_used for group in groups),
    )
