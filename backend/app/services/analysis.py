from __future__ import annotations

from app.clients.azure_openai import AzureOpenAIClient
from app.core.config import settings
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
- problem_feedback_seed を最優先の観測事実として参照する
- problem_feedback_seed の grading_status を区別し, incorrect は誤答分析の主根拠, uncertain は断定を避けた補助根拠, correct は弱点推定の反証として使う
- error_patterns は「答案上で観測された誤りの型」を具体的に返す。単なる科目名や抽象語だけにしない
- analysis_rationale は短文で具体的に返し, 問題番号, 模範解答との差, OCRの不確実性, 確認テストの誤答数のいずれかを必ず含める
- weak_units は confirmation_test_context の単元と problem_feedback_seed の内容を結びつけ, 同義反復を避ける
- teacher_note は講師向けの短い運用メモだけを書く。声かけや宿題量の調整に触れてよい
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
        mode: str = "live",
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
            result.source_mode = "replay" if mode == "replay" else "live"
            return self.enrich_result(constrain_to_catalog(result, catalog), normalized_ocr)

        payload = {
            "student_profile": student.model_dump(),
            "normalized_ocr": normalized_ocr.model_dump(),
            "catalog": [problem.model_dump() for problem in catalog],
            "action": action,
            "confirmation_test_context": manifest_context,
            "problem_feedback_seed": [
                {
                    "problem_no": item.problem_no,
                    "grading_status": item.grading_status,
                    "expected_answer": item.expected_answer,
                    "recognized_answer": item.recognized_answer,
                    "work_text": item.work_text,
                    "final_answer": item.final_answer,
                    "needs_review": item.needs_review,
                    "comment": item.comment,
                }
                for item in build_problem_feedback(normalized_ocr)
            ],
        }
        if mode == "live" and settings.azure_analysis_live_enabled:
            try:
                result = await self.client.analyze(SYSTEM_PROMPT, payload)
                result.source_mode = "live"
                return self.enrich_result(constrain_to_catalog(result, catalog), normalized_ocr)
            except Exception:
                pass

        result = recommend_by_rules(
            student,
            normalized_ocr,
            catalog,
            lighten=action == "lighten",
            manifest_context=manifest_context,
        )
        result.source_mode = "replay" if mode == "replay" else "live"
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
