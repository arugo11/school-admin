import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { UploadPage } from '../pages/upload-page'

const mocks = vi.hoisted(() => ({
  uploadWorksheet: vi.fn(),
  enqueueAnalysis: vi.fn(),
  setUpload: vi.fn(),
  setPreviewUrl: vi.fn(),
  setBanner: vi.fn(),
  addPendingJob: vi.fn(),
}))

vi.mock('../lib/api', () => ({
  uploadWorksheet: mocks.uploadWorksheet,
  enqueueAnalysis: mocks.enqueueAnalysis,
}))

vi.mock('../lib/demo-context', () => ({
  useDemo: () => ({
    session: {
      student: {
        student_id: 's-03',
        display_name: '生徒C',
      },
    },
    setUpload: mocks.setUpload,
    setPreviewUrl: mocks.setPreviewUrl,
    setBanner: mocks.setBanner,
    addPendingJob: mocks.addPendingJob,
  }),
}))

describe('UploadPage', () => {
  it('enqueues background processing without waiting for completion', async () => {
    vi.stubGlobal('URL', { ...URL, createObjectURL: vi.fn(() => 'blob:test-preview') })
    mocks.uploadWorksheet.mockResolvedValue({
      source_image_id: 'img-1',
      filename: 'sheet.png',
      stored_path: 'data/uploads/img-1.png',
      source_mode: 'live',
    })
    mocks.enqueueAnalysis.mockResolvedValue({
      job_id: 'job-1',
      student_id: 's-03',
      source_image_ids: ['img-1'],
      status: 'queued',
      job_type: 'confirmation_test_analysis',
      current_stage: 'queued',
      progress_message: '処理待機中です。',
      created_at: '2026-03-16T00:00:00Z',
    })

    render(<UploadPage />)

    const input = screen.getByLabelText(/画像を選ぶ \/ 撮る/i)
    fireEvent.change(input, {
      target: {
        files: [new File(['dummy'], 'sheet.png', { type: 'image/png' })],
      },
    })

    await waitFor(() => expect(mocks.enqueueAnalysis).toHaveBeenCalled())
    expect(mocks.addPendingJob).toHaveBeenCalledWith(expect.objectContaining({ job_id: 'job-1' }))
    expect(mocks.setBanner).toHaveBeenCalledWith('処理を開始しました。ページを離れて問題ありません。生徒一覧パネルで結果を確認できます。')
  })
})
