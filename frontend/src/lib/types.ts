export type StudentProfile = {
  student_id: string
  display_name: string
  grade: string
  class_name?: string
  school_name?: string
  next_regular_exam_date?: string | null
  days_until_regular_exam?: number | null
  target_level: string
  persona_summary: string
  recent_scores: number[]
  homework_style_notes: string
  weakness_history: string[]
  preferred_difficulty: string
  attention_level: 'low' | 'medium' | 'high' | 'urgent'
  homework_completion_rate?: number | null
  one_line_analysis?: string | null
  recommended_action?: string | null
  latest_summary_generated_at?: string | null
}

export type CatalogProblem = {
  catalog_id: string
  textbook_name: string
  unit_name: string
  chapter_name: string
  problem_no: string
  difficulty: 'basic' | 'standard' | 'advanced'
  skills: string[]
  prerequisites: string[]
  estimated_minutes: number
  tags: string[]
  priority: number
}

export type OcrItem = {
  problem_no: string
  recognized_answer: string
  work_text?: string | null
  final_answer?: string | null
  answer_source?: 'final_answer' | 'work_text' | 'unknown'
  source_image_path?: string | null
  work_image_path?: string | null
  final_image_path?: string | null
  teacher_marks: string[]
  rewrite_detected: boolean
  scratch_notes: string
  raw_text: string
  uncertainty: string[]
}

export type NormalizedOcr = {
  student_id: string
  source_image_id: string
  source_image_paths?: string[]
  page_type: 'worksheet' | 'notebook'
  test_id?: string | null
  source_alias?: string | null
  ocr_confidence_summary: {
    low_confidence_count: number
    notes: string[]
  }
  items: OcrItem[]
}

export type Recommendation = {
  problem_no: string
  reason: string
  difficulty: 'basic' | 'standard' | 'advanced'
}

export type ProblemFeedback = {
  problem_no: string
  catalog_problem_no: string
  expected_answer: string
  recognized_answer: string
  work_text?: string | null
  final_answer?: string | null
  source_image_path?: string | null
  work_image_path?: string | null
  final_image_path?: string | null
  grading_basis: string
  grading_status: 'correct' | 'incorrect' | 'uncertain'
  comment: string
  needs_review: boolean
  regrade_available: boolean
  regrade_requested: boolean
  regrade_note?: string | null
  regrade_outcome?: string | null
}

export type AnalysisResult = {
  weak_units: string[]
  error_patterns: string[]
  homework_load_fit: 'light' | 'appropriate' | 'heavy'
  analysis_rationale: string[]
  recommended_homework: Recommendation[]
  teacher_note: string
  fallback_used: boolean
  source_mode: 'live' | 'replay'
  problem_feedback: ProblemFeedback[]
  rag_context_used?: boolean
  rag_cited_document_titles?: string[]
}

export type UploadResponse = {
  source_image_id: string
  filename: string
  stored_path: string
  source_mode: 'live'
}

export type HomeworkApproval = {
  student_id: string
  approved_problem_nos: string[]
  removed_problem_nos: string[]
  approval_mode: string
  teacher_comment: string
  approved_at: string
}

export type ProblemRegradeResponse = {
  problem_feedback: ProblemFeedback
  analysis: AnalysisResult
}

export type StudentOverviewItem = {
  student_id: string
  display_name: string
  grade: string
  class_name: string
  school_name: string
  next_regular_exam_date?: string | null
  days_until_regular_exam?: number | null
  target_level: string
  attention_level: 'low' | 'medium' | 'high' | 'urgent'
  homework_completion_rate: number
  one_line_analysis: string
  recommended_action: string
}

export type StudentOverviewResponse = {
  total_students: number
  urgent_count: number
  low_completion_count: number
  counseling_priority_count: number
  recommended_actions_today: number
  students: StudentOverviewItem[]
}

export type StudentStateSummary = {
  student_id: string
  current_status: string
  risk_signals: string[]
  next_best_actions: string[]
  recommended_response: string
  one_line_analysis: string
  recommended_action: string
  cited_document_titles: string[]
  current_status_sources: string[]
  risk_signal_sources: string[]
  next_best_action_sources: string[]
  recommended_response_sources: string[]
  source_rankings: {
    rank: number
    title: string
    document_type: 'test_report' | 'score_trend' | 'homework_history' | 'counseling_memo' | 'teacher_note' | 'attendance' | 'mock_exam'
    score: number
    used_for: ('current_status' | 'risk_signals' | 'next_best_actions' | 'recommended_response')[]
  }[]
  generated_at: string
  fallback_used: boolean
}

export type StudentDocument = {
  document_id: number
  student_id: string
  document_type: 'test_report' | 'score_trend' | 'homework_history' | 'counseling_memo' | 'teacher_note' | 'attendance' | 'mock_exam'
  title: string
  body_text: string
  source_system: string
  authored_by: string
  document_date: string
  asset_paths?: string[]
  payload?: {
    normalized_ocr?: NormalizedOcr
    analysis?: AnalysisResult
  } | null
  created_at: string
  updated_at: string
}

export type StudentDocumentCreateRequest = {
  document_type: StudentDocument['document_type']
  title: string
  body_text: string
  source_system: string
  authored_by: string
  document_date: string
}

export type StudentHomeworkHistoryItem = {
  homework_id: number
  student_id: string
  assigned_date: string
  approved_problem_groups: string[]
  expected_load: string
  completion_status: string
  teacher_comment: string
  created_at: string
}

export type SchoolWorkProgressItem = {
  progress_id: number
  student_id: string
  subject_name: string
  workbook_name: string
  completion_rate: number
  completed_pages: number
  target_pages: number
  note: string
  updated_at: string
}

export type SchoolWorkProgressUpdateRequest = {
  subject_name: string
  workbook_name: string
  completion_rate: number
  completed_pages: number
  target_pages: number
  note: string
}

export type RecommendedProblemGroup = {
  group_id: string
  unit_name: string
  difficulty: 'basic' | 'standard' | 'advanced'
  reason: string
  level_fit_comment: string
  supporting_note: string
  cited_document_titles: string[]
  fallback_used: boolean
}

export type RagHomeworkRecommendation = {
  student_id: string
  recommended_problem_groups: RecommendedProblemGroup[]
  fallback_used: boolean
}

export type ProcessingJobStatus = 'queued' | 'running' | 'succeeded' | 'failed'

export type ProcessingJob = {
  job_id: string
  student_id: string
  source_image_ids: string[]
  status: ProcessingJobStatus
  progress_message: string
  error_detail?: string | null
  result_document_id?: number | null
  created_at: string
  started_at?: string | null
  finished_at?: string | null
}
