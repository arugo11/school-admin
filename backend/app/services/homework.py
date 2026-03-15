from __future__ import annotations

from collections import Counter
from typing import Any

from app.schemas import AnalysisResult, CatalogProblem, HomeworkRecommendation, NormalizedOcrDocument, StudentProfile

SUBJECT_TAG_HINTS = {
    "一次方程式": ["equation", "sign", "distribution"],
    "式の変形": ["distribution", "sign"],
    "関数・座標": ["function"],
    "整数・四則計算": ["review"],
    "図形": ["review"],
    "確率・場合の数": ["review"],
}


def estimate_load(student: StudentProfile, selected: list[CatalogProblem]) -> str:
    total_minutes = sum(item.estimated_minutes for item in selected)
    if student.preferred_difficulty == "basic" and total_minutes > 18:
        return "heavy"
    if total_minutes < 12:
        return "light"
    return "appropriate"


def _merge_manifest_context(
    weakness_candidates: list[str],
    error_patterns: list[str],
    desired_tags: list[str],
    manifest_context: dict[str, Any] | None,
) -> tuple[list[str], list[str], list[str], list[str]]:
    rationale: list[str] = []
    if not manifest_context:
        return weakness_candidates, error_patterns, desired_tags, rationale
    missed_subjects = manifest_context.get("missed_subjects", [])
    if missed_subjects:
        weakness_candidates.extend(missed_subjects[:2])
        for subject in missed_subjects:
            desired_tags.extend(SUBJECT_TAG_HINTS.get(subject, ["review"]))
    incorrect_count = manifest_context.get("incorrect_count", 0)
    matched_count = manifest_context.get("matched_count", 0)
    if incorrect_count:
        error_patterns.append(f"確認テストで {incorrect_count} 問の誤答または未記入があった")
        rationale.append(f"確認テスト {manifest_context['test_id']} の {matched_count} 問を照合し, {incorrect_count} 問でつまずきが見えた")
    missed_catalog_problem_nos = manifest_context.get("missed_catalog_problem_nos", [])
    if missed_catalog_problem_nos:
        rationale.append(f"要復習問題: {', '.join(missed_catalog_problem_nos[:3])}")
    return weakness_candidates, error_patterns, desired_tags, rationale


def recommend_by_rules(
    student: StudentProfile,
    normalized_ocr: NormalizedOcrDocument,
    catalog: list[CatalogProblem],
    lighten: bool = False,
    manifest_context: dict[str, Any] | None = None,
) -> AnalysisResult:
    text_blob = " ".join(item.raw_text for item in normalized_ocr.items)
    weakness_candidates: list[str] = []
    error_patterns: list[str] = []
    desired_tags: list[str] = []

    if "-" in text_blob or any("minus" in note for note in normalized_ocr.ocr_confidence_summary.notes):
        weakness_candidates.append("符号処理")
        desired_tags.append("sign")
    if any("cross" in item.teacher_marks for item in normalized_ocr.items):
        error_patterns.append("誤答が残っている設問がある")
    if any(item.rewrite_detected for item in normalized_ocr.items):
        error_patterns.append("解き直し痕跡はあるが理由の言語化が薄い")
    if any("distribution" in note.lower() for note in normalized_ocr.ocr_confidence_summary.notes) or "(" in text_blob:
        weakness_candidates.append("一次方程式の分配法則")
        desired_tags.append("distribution")

    weakness_candidates, error_patterns, desired_tags, manifest_rationale = _merge_manifest_context(
        weakness_candidates, error_patterns, desired_tags, manifest_context
    )

    if not weakness_candidates:
        weakness_candidates = student.weakness_history[:2] or ["見直し"]
    if not error_patterns:
        error_patterns = [student.weakness_history[0] if student.weakness_history else "見直し不足"]

    desired_tags.extend(tag for problem in catalog for tag in problem.tags if tag in {"review"} and student.attention_level in {"high", "urgent"})

    scored: list[tuple[int, CatalogProblem]] = []
    for problem in catalog:
        score = problem.priority
        if any(tag in problem.tags for tag in desired_tags):
            score += 3
        if student.preferred_difficulty == problem.difficulty:
            score += 2
        if any(unit.replace("の", "") in problem.unit_name for unit in weakness_candidates):
            score += 2
        if any(skill in student.weakness_history for skill in problem.skills):
            score += 1
        scored.append((score, problem))
    ranked = [problem for _, problem in sorted(scored, key=lambda item: (-item[0], item[1].problem_no))]

    selected: list[CatalogProblem] = []
    seen_problem_nos: set[str] = set()
    max_count = 3 if lighten or student.attention_level in {"high", "urgent"} else 4
    for problem in ranked:
        if problem.problem_no in seen_problem_nos:
            continue
        if problem.difficulty == "advanced" and student.preferred_difficulty == "basic":
            continue
        if any(req not in seen_problem_nos and req not in {p.problem_no for p in selected} for req in problem.prerequisites):
            continue
        selected.append(problem)
        seen_problem_nos.add(problem.problem_no)
        if len(selected) >= max_count:
            break

    if lighten:
        selected = sorted(selected, key=lambda item: (item.difficulty != "basic", item.estimated_minutes, item.problem_no))[:3]

    load = estimate_load(student, selected)
    recs = [
        HomeworkRecommendation(
            problem_no=problem.problem_no,
            reason=f"{problem.unit_name}の{problem.chapter_name}を短く復習する",
            difficulty=problem.difficulty,
        )
        for problem in selected
    ]
    rationale = [
        f"OCRから {normalized_ocr.ocr_confidence_summary.low_confidence_count} 件の要確認箇所が見つかった",
        f"{len(recs)} 問の短い復習セットを優先した",
    ]
    rationale.extend(manifest_rationale)
    return AnalysisResult(
        weak_units=list(dict.fromkeys(weakness_candidates))[:2],
        error_patterns=error_patterns[:2],
        homework_load_fit=load,
        analysis_rationale=rationale[:4],
        recommended_homework=recs,
        teacher_note="ライブ分析が不安定な場合でも、このセットなら講師がその場で説明しやすい。",
        fallback_used=True,
        source_mode="live",
    )


def constrain_to_catalog(analysis: AnalysisResult, catalog: list[CatalogProblem]) -> AnalysisResult:
    valid = {problem.problem_no: problem for problem in catalog}
    filtered = [rec for rec in analysis.recommended_homework if rec.problem_no in valid]
    if not filtered:
        fallback = next(iter(valid.values()))
        filtered = [
            HomeworkRecommendation(
                problem_no=fallback.problem_no,
                reason="教材カタログにある基礎問題へ安全に戻す",
                difficulty=fallback.difficulty,
            )
        ]
        analysis.fallback_used = True
    analysis.recommended_homework = filtered
    return analysis


def summarize_problem_mix(recommendations: list[HomeworkRecommendation]) -> dict[str, int]:
    return dict(Counter(rec.difficulty for rec in recommendations))
