from __future__ import annotations

from app.clients.azure_openai import AzureOpenAIClient
from app.schemas import AnalysisResult, CatalogProblem, NormalizedOcrDocument, ProblemFeedback, StudentProfile
from app.services.confirmation_tests import apply_problem_regrade, build_problem_feedback, manifest_context_for_analysis
from app.services.homework import constrain_to_catalog, recommend_by_rules

SYSTEM_PROMPT = """
あなたは学習塾の講師補助AIです。必ずJSONのみを返してください。
出力必須フィールド:
- weak_units: string[]
- error_patterns: string[]
- homework_load_fit: "light" | "appropriate" | "heavy"
- analysis_rationale: string[]
- recommended_homework: [{problem_no, reason, difficulty}]
- teacher_note: string
- fallback_used: boolean
- source_mode: "live"
制約:
- OCRの不確実な箇所を断定しない
- 教材カタログに存在する problem_no のみ使う
- 数学の宿題は3〜5問相当を想定し、重すぎる場合は light に寄せる
- 確認テスト manifest がある場合は, その正答と誤答数を参考にしてよい
""".strip()


class AnalysisService:
    def __init__(self, client: AzureOpenAIClient | None = None) -> None:
        self.client = client or AzureOpenAIClient()

    def enrich_result(
        self,
        result: AnalysisResult,
        normalized_ocr: NormalizedOcrDocument,
        previous_feedback: list[ProblemFeedback] | None = None,
    ) -> AnalysisResult:
        result.problem_feedback = build_problem_feedback(normalized_ocr, previous_feedback=previous_feedback)
        return result

    async def run(
        self,
        student: StudentProfile,
        normalized_ocr: NormalizedOcrDocument,
        catalog: list[CatalogProblem],
        action: str = "initial",
    ) -> AnalysisResult:
        manifest_context = manifest_context_for_analysis(normalized_ocr)

        if action == "lighten":
            result = recommend_by_rules(
                student,
                normalized_ocr,
                catalog,
                lighten=True,
                manifest_context=manifest_context,
            )
            result.source_mode = "live"
            return self.enrich_result(constrain_to_catalog(result, catalog), normalized_ocr)

        payload = {
            "student_profile": student.model_dump(),
            "normalized_ocr": normalized_ocr.model_dump(),
            "catalog": [problem.model_dump() for problem in catalog],
            "action": action,
            "confirmation_test_context": manifest_context,
        }
        try:
            result = await self.client.analyze(SYSTEM_PROMPT, payload)
            result.source_mode = "live"
            return self.enrich_result(constrain_to_catalog(result, catalog), normalized_ocr)
        except Exception:
            result = recommend_by_rules(
                student,
                normalized_ocr,
                catalog,
                lighten=action == "lighten",
                manifest_context=manifest_context,
            )
            result.source_mode = "live"
            return self.enrich_result(constrain_to_catalog(result, catalog), normalized_ocr)

    def regrade_problem(
        self,
        analysis: AnalysisResult,
        normalized_ocr: NormalizedOcrDocument,
        problem_no: str,
        student_note: str,
    ) -> tuple[AnalysisResult, ProblemFeedback]:
        next_feedback, updated_problem = apply_problem_regrade(
            normalized_ocr,
            current_feedback=analysis.problem_feedback,
            problem_no=problem_no,
            student_note=student_note,
        )
        updated_analysis = analysis.model_copy(deep=True)
        updated_analysis.problem_feedback = next_feedback
        return updated_analysis, updated_problem
