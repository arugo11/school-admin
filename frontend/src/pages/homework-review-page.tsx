import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { approveHomework, runAnalysis } from '../lib/api'
import { useDemo } from '../lib/demo-context'
import type { Recommendation } from '../lib/types'
import { SectionCard } from '../components/section-card'

export function HomeworkReviewPage() {
  const { session, setAnalysis, setApproval, setBanner } = useDemo()
  const [removed, setRemoved] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [teacherComment, setTeacherComment] = useState('')
  const navigate = useNavigate()

  const selectedRecommendations = useMemo(() => (
    session.analysis?.recommended_homework.filter((item) => !removed.includes(item.problem_no)) ?? []
  ), [session.analysis, removed])

  if (!session.student || !session.normalizedOcr || !session.analysis) {
    return <div className="empty-state">宿題候補がありません。分析から進めてください。</div>
  }

  async function lightenAgain() {
    const analysis = await runAnalysis(session.student!.student_id, session.normalizedOcr!, 'lighten')
    setAnalysis(analysis)
    setRemoved([])
    setBanner('より軽い宿題セットへ更新しました。')
  }

  async function approve() {
    setBusy(true)
    const approval = await approveHomework({
      student_id: session.student!.student_id,
      approved_problem_nos: selectedRecommendations.map((item) => item.problem_no),
      removed_problem_nos: removed,
      approval_mode: 'teacher-approved',
      teacher_comment: teacherComment,
      approved_at: new Date().toISOString()
    })
    setApproval(approval)
    setBanner('講師承認が完了しました。')
    setBusy(false)
    navigate('/students')
  }

  return (
    <div className="page-grid detail-layout">
      <SectionCard title="宿題承認">
        <div className="recommendation-list">
          {session.analysis.recommended_homework.map((item: Recommendation) => {
            const active = !removed.includes(item.problem_no)
            return (
              <button key={item.problem_no} className={active ? 'recommendation-card active' : 'recommendation-card muted-card'} onClick={() => setRemoved((prev) => prev.includes(item.problem_no) ? prev.filter((value) => value !== item.problem_no) : [...prev, item.problem_no])}>
                <strong>{item.problem_no}</strong>
                <span>{item.difficulty}</span>
                <p>{item.reason}</p>
                <small>{active ? '採用中。タップで外す' : '除外済み。タップで戻す'}</small>
              </button>
            )
          })}
        </div>
        <label className="stack-field">
          講師コメント
          <textarea
            value={teacherComment}
            onChange={(event) => setTeacherComment(event.target.value)}
            rows={3}
            placeholder="必要な場合のみ入力"
          />
        </label>
        <div className="mode-actions">
          <button className="secondary-btn" onClick={lightenAgain}>1クリックで軽くする</button>
          <button className="primary-btn" disabled={busy || selectedRecommendations.length === 0} onClick={approve}>{busy ? '承認中...' : 'この内容で承認'}</button>
        </div>
      </SectionCard>
      <SectionCard title="承認内容">
        <ul className="plain-list">
          {selectedRecommendations.map((item) => <li key={item.problem_no}>{item.problem_no}: {item.reason}</li>)}
        </ul>
      </SectionCard>
    </div>
  )
}
