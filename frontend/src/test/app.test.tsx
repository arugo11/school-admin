import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import App from '../App'
import { DemoProvider } from '../lib/demo-context'

const students = [
  {
    student_id: 's-03',
    display_name: '生徒C',
    grade: '中2',
    target_level: 'standard',
    persona_summary: '努力型',
    recent_scores: [61, 64, 63],
    homework_style_notes: '短く',
    weakness_history: ['符号処理'],
    preferred_difficulty: 'standard',
    attention_level: 'urgent',
  }
]

describe('App', () => {
  it('renders student list from backend data', async () => {
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify(students), { status: 200 })) as typeof fetch
    render(
      <MemoryRouter initialEntries={['/students']}>
        <DemoProvider>
          <App />
        </DemoProvider>
      </MemoryRouter>
    )
    await waitFor(() => expect(screen.getByText('生徒C')).toBeInTheDocument())
  })
})
