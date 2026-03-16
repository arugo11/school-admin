import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { StudentsPage } from '../pages/students-page'

const mocks = vi.hoisted(() => ({
  fetchStudentsOverview: vi.fn(),
  fetchStudent: vi.fn(),
  fetchStudentSummary: vi.fn(),
  fetchStudentDocuments: vi.fn(),
  fetchStudentHomeworkHistory: vi.fn(),
  fetchStudentSchoolWorkProgress: vi.fn(),
  fetchStudentProcessingJobs: vi.fn(),
  setStudent: vi.fn(),
  setBanner: vi.fn(),
  resetFlow: vi.fn(),
  markJobNotificationSeen: vi.fn(),
  removePendingJob: vi.fn(),
}))

vi.mock('../lib/api', () => ({
  fetchStudentsOverview: mocks.fetchStudentsOverview,
  fetchStudent: mocks.fetchStudent,
  fetchStudentSummary: mocks.fetchStudentSummary,
  fetchStudentDocuments: mocks.fetchStudentDocuments,
  fetchStudentHomeworkHistory: mocks.fetchStudentHomeworkHistory,
  fetchStudentSchoolWorkProgress: mocks.fetchStudentSchoolWorkProgress,
  fetchStudentProcessingJobs: mocks.fetchStudentProcessingJobs,
  approveHomework: vi.fn(),
  createStudentDocument: vi.fn(),
  fetchRagHomeworkRecommendation: vi.fn(),
  refreshStudentSummary: vi.fn(),
  resolveAssetUrl: vi.fn(),
  updateStudentSchoolWorkProgress: vi.fn(),
}))

vi.mock('../lib/demo-context', () => ({
  useDemo: () => ({
    session: {
      seenJobNotifications: [],
    },
    setStudent: mocks.setStudent,
    setBanner: mocks.setBanner,
    resetFlow: mocks.resetFlow,
    markJobNotificationSeen: mocks.markJobNotificationSeen,
    removePendingJob: mocks.removePendingJob,
  }),
}))

vi.mock('../components/student-card', () => ({
  StudentCard: ({ student, onSelect }: { student: { student_id: string; display_name: string }, onSelect: (student: { student_id: string }) => void }) => (
    <button onClick={() => onSelect(student)}>{student.display_name}</button>
  ),
}))

describe('StudentsPage', () => {
  it('shows success notification when a background job completes', async () => {
    mocks.fetchStudentsOverview.mockResolvedValue({
      total_students: 1,
      urgent_count: 0,
      low_completion_count: 0,
      counseling_priority_count: 0,
      recommended_actions_today: 0,
      students: [{
        student_id: 's-03',
        display_name: '生徒C',
        grade: '中2',
        class_name: '',
        school_name: '若葉中学校',
        target_level: 'standard',
        attention_level: 'medium',
        homework_completion_rate: 84,
        one_line_analysis: '努力しているが伸び悩み',
        recommended_action: '符号を確認',
      }],
    })
    mocks.fetchStudent.mockResolvedValue({
      student_id: 's-03',
      display_name: '生徒C',
      grade: '中2',
      class_name: '',
      school_name: '若葉中学校',
      target_level: 'standard',
      persona_summary: '努力しているが伸び悩み',
      recent_scores: [],
      homework_style_notes: '',
      weakness_history: [],
      preferred_difficulty: 'standard',
      attention_level: 'medium',
      homework_completion_rate: 84,
      one_line_analysis: '努力しているが伸び悩み',
      recommended_action: '符号を確認',
    })
    mocks.fetchStudentSummary.mockResolvedValue({
      student_id: 's-03',
      current_status: '状態',
      risk_signals: ['危険'],
      next_best_actions: ['確認'],
      recommended_response: '対応',
      one_line_analysis: '努力しているが伸び悩み',
      recommended_action: '符号を確認',
      cited_document_titles: ['doc'],
      current_status_sources: ['1位 doc'],
      risk_signal_sources: ['1位 doc'],
      next_best_action_sources: ['1位 doc'],
      recommended_response_sources: ['1位 doc'],
      source_rankings: [],
      generated_at: '2026-03-16T00:00:00Z',
      fallback_used: false,
    })
    mocks.fetchStudentDocuments.mockResolvedValue([
      {
        document_id: 42,
        student_id: 's-03',
        document_type: 'test_report',
        title: '確認テスト',
        body_text: 'body',
        source_system: 'auto-analysis',
        authored_by: 'system',
        document_date: '2026-03-16T00:00:00Z',
        asset_paths: [],
        payload: null,
        created_at: '2026-03-16T00:00:00Z',
        updated_at: '2026-03-16T00:00:00Z',
      },
    ])
    mocks.fetchStudentHomeworkHistory.mockResolvedValue([])
    mocks.fetchStudentSchoolWorkProgress.mockResolvedValue([])
    mocks.fetchStudentProcessingJobs.mockResolvedValue([
      {
        job_id: 'job-1',
        student_id: 's-03',
        source_image_ids: ['img-1'],
        status: 'succeeded',
        job_type: 'confirmation_test_analysis',
        current_stage: 'done',
        progress_message: '処理が完了しました。',
        notification_message: '分析済みに確認テストが追加されました',
        result_document_id: 42,
        created_at: '2026-03-16T00:00:00Z',
      },
    ])

    render(
      <MemoryRouter>
        <StudentsPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('生徒C')).toBeInTheDocument())
    fireEvent.click(screen.getByText('生徒C'))

    await waitFor(() => expect(screen.getByText('分析済みに確認テストが追加されました')).toBeInTheDocument())
    expect(mocks.markJobNotificationSeen).toHaveBeenCalledWith('job-1')
    expect(mocks.removePendingJob).toHaveBeenCalledWith('job-1')
  })
})
