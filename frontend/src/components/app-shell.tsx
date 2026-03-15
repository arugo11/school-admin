import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

import { useDemo } from '../lib/demo-context'

const steps = [
  { to: '/students', label: '生徒一覧' },
  { to: '/upload', label: 'アップロード' },
  { to: '/analysis', label: '分析（任意）' }
]

export function AppShell({ children }: { children: ReactNode }) {
  const { session } = useDemo()

  return (
    <div className="app-frame">
      <header className="hero-bar">
        <div className="hero-copy">
          <p className="wordmark">school admin system</p>
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
