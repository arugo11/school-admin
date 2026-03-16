import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { AnalysisPage } from '../pages/analysis-page'

const mocks = vi.hoisted(() => ({
  setAnalysis: vi.fn(),
  setBanner: vi.fn(),
  navigate: vi.fn(),
  regradeProblem: vi.fn(),
  runAnalysis: vi.fn(),
  fetchRagHomeworkRecommendation: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mocks.navigate,
  }
})

vi.mock('../lib/demo-context', () => ({
  useDemo: () => ({
    session: {
      student: {
        student_id: 's-03',
        display_name: '生徒C',
      },
      normalizedOcr: {
        student_id: 's-03',
        source_image_id: 'img-1',
        source_image_paths: ['data/uploads/sample.png'],
        page_type: 'worksheet',
        test_id: 'ct-exhibit-main',
        source_alias: 'math-500-jp',
        ocr_confidence_summary: { low_confidence_count: 0, notes: [] },
        items: [],
      },
      previewUrl: 'blob:test-preview',
      analysis: {
        weak_units: ['\\frac{1}{2} の計算'],
        error_patterns: ['Q1 で $\\frac{1}{2}$ を誤答として読んだ'],
        homework_load_fit: 'appropriate',
        analysis_rationale: ['Q1 の最終解答は $\\frac{1}{2}$ と一致しませんでした。'],
        recommended_homework: [{ problem_no: 'A-02', reason: '$\\frac{1}{2}$ の復習', difficulty: 'basic' }],
        teacher_note: '短く復習させます。',
        fallback_used: false,
        source_mode: 'live',
        problem_feedback: [
          {
            problem_no: 'Q1',
            catalog_problem_no: 'CT-EXHIBIT-MAIN-Q01',
            expected_answer: '\\frac{1}{2}',
            recognized_answer: '\\boxed{\\frac{2}{3}}',
            work_text: 'x=\\frac{2}{3}',
            final_answer: '\\boxed{\\frac{2}{3}}',
            source_image_path: 'data/uploads/sample.png',
            grading_basis: '最終解答欄を優先して \\boxed{\\frac{2}{3}} を採用しました。',
            grading_status: 'incorrect',
            comment: '模範解答 \\frac{1}{2} と一致しませんでした。',
            needs_review: false,
            regrade_available: true,
            regrade_requested: false,
            regrade_note: null,
            regrade_outcome: null,
          },
        ],
      },
      },
      setAnalysis: mocks.setAnalysis,
      setBanner: mocks.setBanner,
  }),
}))

vi.mock('../lib/api', () => ({
  runAnalysis: mocks.runAnalysis,
  regradeProblem: mocks.regradeProblem,
  fetchRagHomeworkRecommendation: mocks.fetchRagHomeworkRecommendation,
}))

describe('AnalysisPage', () => {
  it('renders problem feedback and submits regrade', async () => {
    mocks.fetchRagHomeworkRecommendation.mockResolvedValue({
      student_id: 's-03',
      recommended_problem_groups: [
        {
          group_id: 'A-03',
          unit_name: '一次方程式',
          difficulty: 'standard',
          reason: '分配法則の復習',
          level_fit_comment: '標準帯で妥当',
          supporting_note: '短く出す',
          cited_document_titles: ['a', 'b', 'c'],
          fallback_used: false,
        },
      ],
      fallback_used: false,
    })
    mocks.regradeProblem.mockResolvedValue({
      problem_feedback: {
        problem_no: 'Q1',
        catalog_problem_no: 'CT-EXHIBIT-MAIN-Q01',
        expected_answer: '2',
        recognized_answer: 'wrong',
        work_text: 'x+1=2',
        final_answer: 'wrong',
        source_image_path: 'data/uploads/sample.png',
        grading_basis: '最終解答欄に OCR の影響があります。',
        grading_status: 'uncertain',
        comment: '要確認へ変更しました。',
        needs_review: true,
        regrade_available: true,
        regrade_requested: true,
        regrade_note: '符号が OCR で落ちています',
        regrade_outcome: 'OCR の影響があるため要確認に変更しました。',
      },
      analysis: {
        weak_units: ['\\frac{1}{2} の計算'],
        error_patterns: ['Q1 で $\\frac{1}{2}$ を誤答として読んだ'],
        homework_load_fit: 'appropriate',
        analysis_rationale: ['Q1 の最終解答は $\\frac{1}{2}$ と一致しませんでした。'],
        recommended_homework: [{ problem_no: 'A-02', reason: '$\\frac{1}{2}$ の復習', difficulty: 'basic' }],
        teacher_note: '短く復習させます。',
        fallback_used: false,
        source_mode: 'live',
        problem_feedback: [
          {
            problem_no: 'Q1',
            catalog_problem_no: 'CT-EXHIBIT-MAIN-Q01',
            expected_answer: '\\frac{1}{2}',
            recognized_answer: '\\boxed{\\frac{2}{3}}',
            work_text: 'x=\\frac{2}{3}',
            final_answer: '\\boxed{\\frac{2}{3}}',
            source_image_path: 'data/uploads/sample.png',
            grading_basis: '最終解答欄に OCR の影響があります。',
            grading_status: 'uncertain',
            comment: '要確認へ変更しました。',
            needs_review: true,
            regrade_available: true,
            regrade_requested: true,
            regrade_note: '符号が OCR で落ちています',
            regrade_outcome: 'OCR の影響があるため要確認に変更しました。',
          },
        ],
      },
    })

    render(
      <MemoryRouter>
        <AnalysisPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('読み取りと判定')).toBeInTheDocument()
    expect(screen.getByText('Q1')).toBeInTheDocument()
    expect(screen.getByText('誤答')).toBeInTheDocument()
    expect(document.querySelectorAll('.katex').length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: 'この判定に訂正を依頼' }))
    fireEvent.change(screen.getByPlaceholderText('例: 最終解答欄の数字が薄い / 計算過程に符号が残っている'), {
      target: { value: '符号が OCR で落ちています' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'この内容で再評価' }))

    await waitFor(() => expect(mocks.regradeProblem).toHaveBeenCalled())
    expect(mocks.setAnalysis).toHaveBeenCalled()
    expect(mocks.setBanner).toHaveBeenCalledWith('Q1 の訂正依頼を反映しました。')
  })

  it('renders latex-like answers with katex output', async () => {
    mocks.fetchRagHomeworkRecommendation.mockResolvedValue({
      student_id: 's-03',
      recommended_problem_groups: [],
      fallback_used: false,
    })

    render(
      <MemoryRouter>
        <AnalysisPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(document.querySelectorAll('.katex').length).toBeGreaterThan(0))
    expect(document.body.textContent).not.toContain('\\frac{1}{2}')
  })
})
