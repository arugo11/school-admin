import type { AnalysisResult, HomeworkApproval, NormalizedOcr, ProblemRegradeResponse, StudentProfile, UploadResponse } from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export function resolveAssetUrl(storedPath?: string | null): string | undefined {
  if (!storedPath) return undefined
  if (storedPath.startsWith('blob:') || storedPath.startsWith('http')) return storedPath
  if (storedPath.startsWith('frontend/public/')) return `/${storedPath.replace(/^frontend\/public\//, '')}`
  const normalized = storedPath.replace(/^data\//, '')
  return `${API_BASE}/assets/${normalized}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    const detail = await response.text()
    let message = detail || `Request failed: ${response.status}`
    try {
      const parsed = JSON.parse(detail) as { detail?: string }
      message = parsed.detail || message
    } catch {
      // keep the plain-text fallback when the response is not JSON
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export function fetchStudents(): Promise<StudentProfile[]> {
  return request<StudentProfile[]>('/api/students')
}

export function fetchStudent(studentId: string): Promise<StudentProfile> {
  return request<StudentProfile>(`/api/students/${studentId}`)
}

export async function uploadWorksheet(studentId: string, file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('student_id', studentId)
  form.append('file', file)
  return request<UploadResponse>('/api/uploads', { method: 'POST', body: form })
}

export function runOcr(studentId: string, sourceImageId: string | string[]): Promise<{ source_mode: 'live'; raw_ocr: Record<string, unknown>; normalized_ocr: NormalizedOcr }> {
  const body = Array.isArray(sourceImageId)
    ? { student_id: studentId, source_image_ids: sourceImageId }
    : { student_id: studentId, source_image_id: sourceImageId }
  return request('/api/ocr/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
}

export function runAnalysis(studentId: string, normalizedOcr: NormalizedOcr, action: 'initial' | 'regenerate' | 'lighten' = 'initial'): Promise<AnalysisResult> {
  return request('/api/analysis/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ student_id: studentId, normalized_ocr: normalizedOcr, action })
  })
}

export function regradeProblem(
  studentId: string,
  normalizedOcr: NormalizedOcr,
  problemNo: string,
  studentNote: string,
  currentAnalysis: AnalysisResult,
): Promise<ProblemRegradeResponse> {
  return request('/api/analysis/regrade-problem', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      student_id: studentId,
      normalized_ocr: normalizedOcr,
      problem_no: problemNo,
      student_note: studentNote,
      current_analysis: currentAnalysis,
    })
  })
}

export function approveHomework(payload: HomeworkApproval): Promise<HomeworkApproval> {
  return request('/api/homework/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}
