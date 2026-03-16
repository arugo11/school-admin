import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { OcrReviewPage } from '../pages/ocr-review-page'

const mocks = vi.hoisted(() => ({
  navigate: vi.fn(),
  setNormalizedOcr: vi.fn(),
  setAnalysis: vi.fn(),
  setBanner: vi.fn(),
  runAnalysis: vi.fn(),
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
        page_type: 'worksheet',
        ocr_confidence_summary: { low_confidence_count: 1, notes: ['Q2 の分数が不鮮明'] },
        items: [
          {
            problem_no: 'Q1',
            recognized_answer: '\\frac{1}{2}',
            work_text: 'x=\\frac{1}{2}',
            final_answer: '\\boxed{\\frac{1}{2}}',
            answer_source: 'final_answer',
            teacher_marks: [],
            rewrite_detected: false,
            scratch_notes: '',
            raw_text: '$$\\frac{1}{2}$$',
            uncertainty: [],
          },
        ],
      },
      previewUrl: 'blob:test-preview',
    },
    setNormalizedOcr: mocks.setNormalizedOcr,
    setAnalysis: mocks.setAnalysis,
    setBanner: mocks.setBanner,
  }),
}))

vi.mock('../lib/api', () => ({
  runAnalysis: mocks.runAnalysis,
  resolveAssetUrl: vi.fn(),
}))

describe('OcrReviewPage', () => {
  it('shows editable fields with rendered math previews', () => {
    render(
      <MemoryRouter>
        <OcrReviewPage />
      </MemoryRouter>,
    )

    expect(screen.getAllByText('プレビュー').length).toBeGreaterThan(0)
    expect(document.querySelectorAll('.katex').length).toBeGreaterThan(0)
    expect(document.body.textContent).not.toContain('\\boxed{\\frac{1}{2}}')
  })

  it('keeps editable OCR fields visible', () => {
    render(
      <MemoryRouter>
        <OcrReviewPage />
      </MemoryRouter>,
    )

    expect(screen.getAllByDisplayValue('x=\\frac{1}{2}').length).toBeGreaterThan(0)
    const finalInputs = screen.getAllByDisplayValue('\\boxed{\\frac{1}{2}}')
    expect(finalInputs.length).toBeGreaterThan(0)
    fireEvent.change(finalInputs[0], { target: { value: 'x=2' } })
    expect(mocks.setNormalizedOcr).toHaveBeenCalled()
  })
})
