from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class StudentProfile(BaseModel):
    student_id: str
    display_name: str
    grade: str
    class_name: str = ""
    school_name: str = ""
    next_regular_exam_date: datetime | None = None
    days_until_regular_exam: int | None = None
    target_level: str
    persona_summary: str
    recent_scores: list[int]
    homework_style_notes: str
    weakness_history: list[str]
    preferred_difficulty: str
    attention_level: Literal["low", "medium", "high", "urgent"] = "medium"
    homework_completion_rate: int | None = None
    one_line_analysis: str | None = None
    recommended_action: str | None = None
    latest_summary_generated_at: datetime | None = None


class CatalogProblem(BaseModel):
    catalog_id: str
    textbook_name: str
    unit_name: str
    chapter_name: str
    problem_no: str
    difficulty: Literal["basic", "standard", "advanced"]
    skills: list[str]
    prerequisites: list[str]
    estimated_minutes: int
    tags: list[str]
    priority: int = 3


class OcrConfidenceSummary(BaseModel):
    low_confidence_count: int = 0
    notes: list[str] = Field(default_factory=list)


class OcrItem(BaseModel):
    problem_no: str
    recognized_answer: str
    work_text: str | None = None
    final_answer: str | None = None
    answer_source: Literal["final_answer", "work_text", "unknown"] = "unknown"
    source_image_path: str | None = None
    work_image_path: str | None = None
    final_image_path: str | None = None
    teacher_marks: list[str] = Field(default_factory=list)
    rewrite_detected: bool = False
    scratch_notes: str = ""
    raw_text: str
    uncertainty: list[str] = Field(default_factory=list)

    @field_validator("recognized_answer")
    @classmethod
    def normalize_unknown(cls, value: str) -> str:
        cleaned = value.strip()
        return cleaned or "unknown"


class NormalizedOcrDocument(BaseModel):
    student_id: str
    source_image_id: str
    source_image_paths: list[str] = Field(default_factory=list)
    page_type: Literal["worksheet", "notebook"] = "worksheet"
    ocr_confidence_summary: OcrConfidenceSummary
    items: list[OcrItem]
    test_id: str | None = None
    source_alias: str | None = None


class HomeworkRecommendation(BaseModel):
    problem_no: str
    reason: str
    difficulty: Literal["basic", "standard", "advanced"]


class ProblemFeedback(BaseModel):
    problem_no: str
    catalog_problem_no: str
    expected_answer: str
    recognized_answer: str
    work_text: str | None = None
    final_answer: str | None = None
    source_image_path: str | None = None
    work_image_path: str | None = None
    final_image_path: str | None = None
    grading_basis: str = ""
    grading_status: Literal["correct", "incorrect", "uncertain"]
    comment: str
    needs_review: bool = False
    regrade_available: bool = False
    regrade_requested: bool = False
    regrade_note: str | None = None
    regrade_outcome: str | None = None


class AnalysisResult(BaseModel):
    weak_units: list[str]
    error_patterns: list[str]
    homework_load_fit: Literal["light", "appropriate", "heavy"]
    analysis_rationale: list[str]
    recommended_homework: list[HomeworkRecommendation]
    teacher_note: str
    fallback_used: bool = False
    source_mode: Literal["live", "replay"] = "live"
    problem_feedback: list[ProblemFeedback] = Field(default_factory=list)
    rag_context_used: bool = False
    rag_cited_document_titles: list[str] = Field(default_factory=list)


class HomeworkApproval(BaseModel):
    student_id: str
    approved_problem_nos: list[str]
    removed_problem_nos: list[str] = Field(default_factory=list)
    approval_mode: str
    teacher_comment: str = ""
    approved_at: datetime


class UploadResponse(BaseModel):
    source_image_id: str
    filename: str
    stored_path: str
    source_mode: Literal["live", "replay"] = "live"


class OcrRunRequest(BaseModel):
    student_id: str
    source_image_id: str | None = None
    source_image_ids: list[str] = Field(default_factory=list)
    fixture_id: str | None = None

    @model_validator(mode="after")
    def validate_source_ids(self) -> "OcrRunRequest":
        if self.source_image_id or self.source_image_ids:
            return self
        raise ValueError("source_image_id or source_image_ids is required")


class OcrNormalizeRequest(BaseModel):
    student_id: str
    source_image_id: str
    raw_ocr: dict[str, Any]


class AnalysisRunRequest(BaseModel):
    student_id: str
    normalized_ocr: NormalizedOcrDocument
    mode: Literal["live", "replay"] = "live"
    action: Literal["initial", "regenerate", "lighten"] = "initial"


class ProblemRegradeRequest(BaseModel):
    student_id: str
    normalized_ocr: NormalizedOcrDocument
    problem_no: str
    student_note: str
    current_analysis: AnalysisResult | None = None


class ProblemRegradeResponse(BaseModel):
    problem_feedback: ProblemFeedback
    analysis: AnalysisResult


class ConfirmationTestLayout(BaseModel):
    page_size: Literal["A4"] = "A4"
    columns: int = 1
    estimated_question_pages: int
    includes_answer_sheet: bool = True
    max_pages: int


class ConfirmationProblem(BaseModel):
    display_no: int
    problem_id: str
    catalog_problem_no: str
    subject: str
    level: int
    problem: str
    answer: str
    solution: str | None = None
    estimated_minutes: int
    source_dataset: str
    source_config: str | None = None
    source_split: str
    source_unique_id: str
    answer_zone_type: Literal["final_answer"] = "final_answer"
    work_area_label: str | None = "計算過程"
    final_area_label: str | None = "最終解答"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConfirmationTestManifest(BaseModel):
    test_id: str
    source_alias: str
    source_dataset: str
    source_config: str | None = None
    source_split: str
    generated_at: str
    generator_version: str
    seed: int
    problem_count: int
    difficulty_min: int
    difficulty_max: int
    layout: ConfirmationTestLayout
    target_minutes: int
    problems: list[ConfirmationProblem]


class ConfirmationSelectionRecord(BaseModel):
    test_id: str
    source_alias: str
    source_dataset: str
    source_config: str | None = None
    source_split: str
    seed: int
    filters: dict[str, Any]
    selected_problems: list[ConfirmationProblem]


class ConfirmationPerformanceItem(BaseModel):
    problem_no: str
    catalog_problem_no: str
    expected_answer: str
    recognized_answer: str
    subject: str
    level: int
    is_correct: bool


class ConfirmationPerformanceSummary(BaseModel):
    test_id: str
    source_alias: str
    matched_count: int
    correct_count: int
    incorrect_count: int
    missed_subjects: list[str]
    missed_catalog_problem_nos: list[str]
    items: list[ConfirmationPerformanceItem]


DocumentType = Literal[
    "test_report",
    "score_trend",
    "homework_history",
    "counseling_memo",
    "teacher_note",
    "attendance",
    "mock_exam",
]


class StudentMetric(BaseModel):
    metric_type: str
    metric_value: float
    metric_date: datetime


class StudentDocumentCreateRequest(BaseModel):
    document_type: DocumentType
    title: str
    body_text: str
    source_system: str = "manual"
    authored_by: str = "teacher"
    document_date: datetime
    asset_paths: list[str] = Field(default_factory=list)
    payload: dict[str, Any] | None = None


class StudentDocumentResponse(StudentDocumentCreateRequest):
    document_id: int
    student_id: str
    created_at: datetime
    updated_at: datetime


class StudentHomeworkHistoryItem(BaseModel):
    homework_id: int
    student_id: str
    assigned_date: datetime
    approved_problem_groups: list[str]
    expected_load: str
    completion_status: str
    teacher_comment: str
    created_at: datetime


class StudentStateSummary(BaseModel):
    student_id: str
    current_status: str
    risk_signals: list[str]
    next_best_actions: list[str]
    recommended_response: str
    one_line_analysis: str
    recommended_action: str
    cited_document_titles: list[str]
    source_rankings: list["SummarySourceRanking"] = Field(default_factory=list)
    current_status_sources: list[str] = Field(default_factory=list)
    risk_signal_sources: list[str] = Field(default_factory=list)
    next_best_action_sources: list[str] = Field(default_factory=list)
    recommended_response_sources: list[str] = Field(default_factory=list)
    generated_at: datetime
    fallback_used: bool = False

    @field_validator("cited_document_titles")
    @classmethod
    def validate_cited_titles(cls, value: list[str]) -> list[str]:
        if len(value) < 3:
            raise ValueError("cited_document_titles must contain at least 3 items")
        return value[:3]


class SummarySourceRanking(BaseModel):
    rank: int
    title: str
    document_type: DocumentType
    score: float
    used_for: list[Literal["current_status", "risk_signals", "next_best_actions", "recommended_response"]]


StudentStateSummary.model_rebuild()


class StudentStateDraft(BaseModel):
    current_status: str
    risk_signals: list[str]
    next_best_actions: list[str]
    recommended_response: str
    one_line_analysis: str
    recommended_action: str


class StudentOverviewItem(BaseModel):
    student_id: str
    display_name: str
    grade: str
    class_name: str
    school_name: str
    next_regular_exam_date: datetime | None = None
    days_until_regular_exam: int | None = None
    target_level: str
    attention_level: Literal["low", "medium", "high", "urgent"]
    homework_completion_rate: int
    one_line_analysis: str
    recommended_action: str


class SchoolWorkProgressItem(BaseModel):
    progress_id: int
    student_id: str
    subject_name: str
    workbook_name: str
    completion_rate: int
    completed_pages: int
    target_pages: int
    note: str = ""
    updated_at: datetime


class SchoolWorkProgressUpdateRequest(BaseModel):
    subject_name: str
    workbook_name: str
    completion_rate: int = Field(ge=0, le=100)
    completed_pages: int = Field(ge=0)
    target_pages: int = Field(ge=1)
    note: str = ""


class StudentOverviewResponse(BaseModel):
    total_students: int
    urgent_count: int
    low_completion_count: int
    counseling_priority_count: int
    recommended_actions_today: int
    students: list[StudentOverviewItem]


class RagChunkSearchResult(BaseModel):
    chunk_id: int
    document_id: int
    student_id: str
    title: str
    document_type: DocumentType
    document_date: datetime
    chunk_text: str
    score: float


class RecommendedProblemGroup(BaseModel):
    group_id: str
    unit_name: str
    difficulty: Literal["basic", "standard", "advanced"]
    reason: str
    level_fit_comment: str
    supporting_note: str
    cited_document_titles: list[str]
    fallback_used: bool = False


class RagHomeworkRecommendation(BaseModel):
    student_id: str
    recommended_problem_groups: list[RecommendedProblemGroup]
    fallback_used: bool = False


class RagHomeworkRequest(BaseModel):
    student_id: str
    normalized_ocr: NormalizedOcrDocument | None = None
    analysis: AnalysisResult | None = None
    document_id: int | None = None


class AnalysisEnqueueRequest(BaseModel):
    student_id: str
    source_image_id: str | None = None
    source_image_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source_ids(self) -> "AnalysisEnqueueRequest":
        if self.source_image_id or self.source_image_ids:
            return self
        raise ValueError("source_image_id or source_image_ids is required")


class ProcessingJob(BaseModel):
    job_id: str
    student_id: str
    source_image_ids: list[str]
    status: Literal["queued", "running", "succeeded", "failed"]
    progress_message: str = ""
    error_detail: str | None = None
    result_document_id: int | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
