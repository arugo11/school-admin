from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.clients.azure_openai import AzureOpenAIClient
from app.schemas import (
    AnalysisResult,
    CatalogProblem,
    NormalizedOcrDocument,
    RagChunkSearchResult,
    RagHomeworkRecommendation,
    RecommendedProblemGroup,
    SummarySourceRanking,
    StudentDocumentResponse,
    StudentStateDraft,
    StudentHomeworkHistoryItem,
    StudentMetric,
    StudentProfile,
    StudentStateSummary,
)

SUMMARY_SYSTEM_PROMPT = """
あなたは学習塾の講師補助AIです。必ずJSONのみを返してください。
以下のキーを必ず埋めてください。
- current_status: string
- risk_signals: string[]
- next_best_actions: string[]
- recommended_response: string
- one_line_analysis: string
- recommended_action: string
制約:
- 取得した文書要約だけを根拠にする
- 曖昧な推測を増やさない
- 講師が次に動ける短い表現にする
- risk_signals と next_best_actions は 2 件以内
""".strip()


def _metric_map(metrics: list[StudentMetric]) -> dict[str, float]:
    return {metric.metric_type: metric.metric_value for metric in metrics}


def _used_for(document_type: str, rank: int) -> list[str]:
    mapping = {
        "test_report": ["current_status", "risk_signals"],
        "homework_history": ["risk_signals", "next_best_actions"],
        "counseling_memo": ["recommended_response"],
        "teacher_note": ["recommended_response", "next_best_actions"],
        "mock_exam": ["current_status"],
        "attendance": ["risk_signals"],
        "score_trend": ["current_status"],
    }
    values = mapping.get(document_type, ["current_status"])
    if rank == 1 and "current_status" not in values:
        values = ["current_status", *values]
    return values[:2]


def _section_sources(rankings: list[SummarySourceRanking], key: str) -> list[str]:
    labels = []
    for ranking in rankings:
        if key in ranking.used_for:
            labels.append(f"{ranking.rank}位 {ranking.title}")
    return labels[:3]


def _build_summary_from_draft(
    *,
    student_id: str,
    draft: StudentStateDraft,
    source_rankings: list[SummarySourceRanking],
    titles: list[str],
    fallback_used: bool,
) -> StudentStateSummary:
    return StudentStateSummary(
        student_id=student_id,
        current_status=draft.current_status,
        risk_signals=draft.risk_signals[:2],
        next_best_actions=draft.next_best_actions[:2],
        recommended_response=draft.recommended_response,
        one_line_analysis=draft.one_line_analysis,
        recommended_action=draft.recommended_action,
        cited_document_titles=titles[:3],
        source_rankings=source_rankings,
        current_status_sources=_section_sources(source_rankings, "current_status"),
        risk_signal_sources=_section_sources(source_rankings, "risk_signals"),
        next_best_action_sources=_section_sources(source_rankings, "next_best_actions"),
        recommended_response_sources=_section_sources(source_rankings, "recommended_response"),
        generated_at=datetime.now(timezone.utc),
        fallback_used=fallback_used,
    )


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
    source_rankings = [
        SummarySourceRanking(
            rank=index + 1,
            title=chunk.title,
            document_type=chunk.document_type,
            score=round(chunk.score, 3),
            used_for=_used_for(chunk.document_type, index + 1),
        )
        for index, chunk in enumerate(preferred_chunks[:5])
    ]
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
    draft = StudentStateDraft(
        current_status=current_status,
        risk_signals=risk_signals[:2],
        next_best_actions=next_actions[:2],
        recommended_response=recommended_response,
        one_line_analysis=one_line_analysis,
        recommended_action=recommended_action,
    )
    return _build_summary_from_draft(
        student_id=student.student_id,
        draft=draft,
        source_rankings=source_rankings,
        titles=titles,
        fallback_used=True,
    )


async def generate_student_summary(
    *,
    student: StudentProfile,
    metrics: list[StudentMetric],
    retrieved_chunks: list[RagChunkSearchResult],
    documents: list[StudentDocumentResponse],
    client: AzureOpenAIClient | None = None,
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
    source_rankings = [
        SummarySourceRanking(
            rank=index + 1,
            title=chunk.title,
            document_type=chunk.document_type,
            score=round(chunk.score, 3),
            used_for=_used_for(chunk.document_type, index + 1),
        )
        for index, chunk in enumerate(preferred_chunks[:5])
    ]
    titles = [chunk.title for chunk in preferred_chunks[:3]]
    while len(titles) < 3:
        fallback_title = documents[min(len(titles), len(documents) - 1)].title if documents else f"{student.display_name} 文書"
        titles.append(fallback_title)

    payload = {
        "student": {
            "student_id": student.student_id,
            "display_name": student.display_name,
            "grade": student.grade,
            "class_name": student.class_name,
        },
        "metrics": metric_map,
        "retrieved_chunks": [
            {
                "rank": ranking.rank,
                "title": ranking.title,
                "document_type": ranking.document_type,
                "score": ranking.score,
                "used_for_hint": ranking.used_for,
                "content": chunk.chunk_text,
            }
            for ranking, chunk in zip(source_rankings, preferred_chunks[:5], strict=False)
        ],
    }
    aoai_client = client or AzureOpenAIClient()
    try:
        draft = await aoai_client.summarize_student_state(SUMMARY_SYSTEM_PROMPT, payload)
        return _build_summary_from_draft(
            student_id=student.student_id,
            draft=draft,
            source_rankings=source_rankings,
            titles=titles,
            fallback_used=False,
        )
    except Exception:
        return build_fallback_summary(student, metrics, retrieved_chunks, documents)


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
