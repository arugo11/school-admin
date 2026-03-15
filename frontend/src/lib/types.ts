export type StudentProfile = {
  student_id: string
  display_name: string
  grade: string
  target_level: string
  persona_summary: string
  recent_scores: number[]
  homework_style_notes: string
  weakness_history: string[]
  preferred_difficulty: string
  attention_level: 'low' | 'medium' | 'high' | 'urgent'
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
  source_mode: 'live'
  problem_feedback: ProblemFeedback[]
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
