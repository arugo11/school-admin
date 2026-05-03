import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import App from '../App'

describe('App', () => {
  it('renders the suspended notice on public routes', () => {
    render(
      <MemoryRouter initialEntries={['/students']}><App /></MemoryRouter>
    )

    expect(screen.getByText('公開停止中')).toBeInTheDocument()
    expect(
      screen.getByText('現在このデモは公開を停止しています. 何かあれば me@argo11.devまで'),
    ).toBeInTheDocument()
  })
})
