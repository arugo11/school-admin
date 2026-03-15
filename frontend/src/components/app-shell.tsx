import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

import { useDemo } from '../lib/demo-context'

const steps = [
  { to: '/students', label: '生徒一覧' },
  { to: '/upload', label: 'アップロード' },
  { to: '/ocr-review', label: 'OCR確認' },
  { to: '/analysis', label: '分析' },
  { to: '/homework-review', label: '宿題承認' }
]

export function AppShell({ children }: { children: ReactNode }) {
  const { session } = useDemo()

  return (
    <div className="app-frame">
      <header className="hero-bar">
        <div className="hero-copy">
          <p className="wordmark">答案確認フロー</p>
        </div>
        <div className="hero-status">
          {session.student ? <span className="student-chip">{session.student.display_name}</span> : <span className="student-chip subtle">生徒を選択</span>}
        </div>
      </header>
      <nav className="step-nav">
        {steps.map((step) => (
          <NavLink key={step.to} to={step.to} className={({ isActive }) => isActive ? 'step-link active' : 'step-link'}>
            {step.label}
          </NavLink>
        ))}
      </nav>
      {session.banner ? <div className="banner">{session.banner}</div> : null}
      <main>{children}</main>
    </div>
  )
}
