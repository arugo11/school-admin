import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import App from '../App'
import { DemoProvider } from '../lib/demo-context'

const overview = {
  total_students: 1,
  urgent_count: 1,
  low_completion_count: 0,
  counseling_priority_count: 1,
  recommended_actions_today: 1,
  students: [
    {
      student_id: 's-03',
      display_name: '生徒C',
      grade: '中2',
      target_level: 'standard',
      attention_level: 'urgent',
      homework_completion_rate: 84,
      one_line_analysis: '努力しているが伸び悩み',
      recommended_action: '次回は符号処理を確認',
    }
  ]
}

describe('App', () => {
  it('renders student list from backend data', async () => {
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify(overview), { status: 200 })) as typeof fetch
    render(
      <MemoryRouter initialEntries={['/students']}>
        <DemoProvider>
          <App />
        </DemoProvider>
      </MemoryRouter>
    )
    await waitFor(() => expect(screen.getByText('生徒C')).toBeInTheDocument())
    expect(screen.getByText('努力しているが伸び悩み')).toBeInTheDocument()
    expect(screen.getByText('84%')).toBeInTheDocument()
  })
})
