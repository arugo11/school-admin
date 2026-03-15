import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import {
  createStudentDocument,
  fetchStudent,
  fetchStudentDocuments,
  fetchStudentHomeworkHistory,
  fetchStudentsOverview,
  fetchStudentSummary,
  refreshStudentSummary
} from '../lib/api'
import { useDemo } from '../lib/demo-context'
import type { StudentDocument, StudentHomeworkHistoryItem, StudentOverviewItem, StudentProfile, StudentStateSummary } from '../lib/types'
import { SectionCard } from '../components/section-card'
import { StudentCard } from '../components/student-card'

export function StudentsPage() {
  const [students, setStudents] = useState<StudentOverviewItem[]>([])
  const [selected, setSelected] = useState<StudentProfile>()
  const [summary, setSummary] = useState<StudentStateSummary>()
  const [documents, setDocuments] = useState<StudentDocument[]>([])
  const [homeworkHistory, setHomeworkHistory] = useState<StudentHomeworkHistoryItem[]>([])
  const [overviewStats, setOverviewStats] = useState<{ total_students: number; urgent_count: number; low_completion_count: number; counseling_priority_count: number; recommended_actions_today: number }>()
  const [error, setError] = useState<string>()
  const [detailBusy, setDetailBusy] = useState(false)
  const [note, setNote] = useState('')
  const [saveBusy, setSaveBusy] = useState(false)
  const navigate = useNavigate()
  const { setStudent, setBanner, resetFlow } = useDemo()

  useEffect(() => {
    fetchStudentsOverview()
      .then((payload) => {
        setStudents(payload.students)
        setOverviewStats(payload)
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  async function loadStudentDetail(studentId: string) {
    setDetailBusy(true)
    try {
      const [studentPayload, summaryPayload, documentPayload, homeworkPayload] = await Promise.all([
        fetchStudent(studentId),
        fetchStudentSummary(studentId),
        fetchStudentDocuments(studentId),
        fetchStudentHomeworkHistory(studentId),
      ])
      setSelected(studentPayload)
      setSummary(summaryPayload)
      setDocuments(documentPayload)
      setHomeworkHistory(homeworkPayload)
      setError(undefined)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setDetailBusy(false)
    }
  }

  async function handleRefreshSummary() {
    if (!selected) return
    setDetailBusy(true)
    try {
      const refreshed = await refreshStudentSummary(selected.student_id)
      setSummary(refreshed)
      setBanner('生徒サマリを更新しました。')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setDetailBusy(false)
    }
  }

  async function handleAddNote() {
    if (!selected || !note.trim()) return
    setSaveBusy(true)
    try {
      await createStudentDocument(selected.student_id, {
        document_type: 'teacher_note',
        title: `${new Date().toISOString().slice(0, 10)} 講師追記`,
        body_text: note.trim(),
        source_system: 'manual',
        authored_by: 'teacher',
        document_date: new Date().toISOString(),
      })
      await loadStudentDetail(selected.student_id)
      setNote('')
      setBanner('講師メモを追加しました。')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSaveBusy(false)
    }
  }

  function startFlow(studentCard: StudentOverviewItem) {
    const profile: StudentProfile = {
      student_id: studentCard.student_id,
      display_name: studentCard.display_name,
      grade: studentCard.grade,
      target_level: studentCard.target_level,
      persona_summary: studentCard.one_line_analysis,
      recent_scores: [],
      homework_style_notes: '',
      weakness_history: [],
      preferred_difficulty: studentCard.target_level,
      attention_level: studentCard.attention_level,
      homework_completion_rate: studentCard.homework_completion_rate,
      one_line_analysis: studentCard.one_line_analysis,
      recommended_action: studentCard.recommended_action,
    }
    resetFlow()
    setStudent(profile)
    setBanner(undefined)
    navigate('/upload')
  }

  return (
    <div className="page-grid dashboard-layout">
      <SectionCard title="教室全体の状況" subtitle="直近1か月の生徒文脈をまとめています。">
        {error ? <div className="empty-state">{error}</div> : null}
        <div className="overview-strip">
          <div className="callout-box"><span>在籍</span><strong>{overviewStats?.total_students ?? students.length}</strong></div>
          <div className="callout-box"><span>要確認</span><strong>{overviewStats?.urgent_count ?? 0}</strong></div>
          <div className="callout-box"><span>宿題低達成</span><strong>{overviewStats?.low_completion_count ?? 0}</strong></div>
          <div className="callout-box"><span>本日の推奨対応</span><strong>{overviewStats?.recommended_actions_today ?? 0}</strong></div>
        </div>
      </SectionCard>
      <div className="dashboard-main">
        <SectionCard title="生徒パネル一覧" subtitle="右ペインで状態と根拠を確認できます。">
          <div className="student-grid">
            {students.map((student) => (
              <StudentCard
                key={student.student_id}
                student={student}
                active={selected?.student_id === student.student_id}
                onSelect={(studentCard) => { void loadStudentDetail(studentCard.student_id) }}
                onStartFlow={startFlow}
              />
            ))}
          </div>
        </SectionCard>
        <SectionCard title={selected ? `${selected.display_name} の詳細` : '生徒詳細'} subtitle="次に打つべき手と危険信号を優先表示します。">
          {!selected ? <div className="empty-state">生徒カードを選ぶと、右側に詳細を表示します。</div> : null}
          {detailBusy ? <div className="banner compact">詳細を更新しています...</div> : null}
          {selected && summary ? (
            <div className="student-detail-pane">
              <div className="detail-actions">
                <span className={`attention-pill ${selected.attention_level}`}>{selected.grade}</span>
                <button className="secondary-btn compact-btn" onClick={() => void handleRefreshSummary()}>手動更新</button>
              </div>
              <div className="analysis-grid single-column">
                <div className="analysis-panel">
                  <h3>現在の状態</h3>
                  <p>{summary.current_status}</p>
                </div>
                <div className="analysis-panel">
                  <h3>直近の危険信号</h3>
                  <ul className="plain-list">{summary.risk_signals.map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
                <div className="analysis-panel">
                  <h3>次に打つべき手</h3>
                  <ul className="plain-list">{summary.next_best_actions.map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
                <div className="analysis-panel">
                  <h3>推奨対応</h3>
                  <p>{summary.recommended_response}</p>
                </div>
              </div>
              <div className="detail-meta-grid">
                <div className="callout-box"><span>宿題達成率</span><strong>{selected.homework_completion_rate ?? 0}%</strong></div>
                <div className="callout-box"><span>一言AI分析</span><strong>{summary.one_line_analysis}</strong></div>
              </div>
              <div className="analysis-panel">
                <h3>根拠文書</h3>
                <ul className="plain-list">{summary.cited_document_titles.map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
              <div className="analysis-panel">
                <h3>ドキュメント一覧</h3>
                <div className="document-list">
                  {documents.map((document) => (
                    <article key={document.document_id} className="document-card">
                      <div className="ocr-row">
                        <strong>{document.title}</strong>
                        <span className="tag-pill">{document.document_type}</span>
                      </div>
                      <p>{document.body_text}</p>
                    </article>
                  ))}
                </div>
              </div>
              <div className="analysis-panel">
                <h3>宿題履歴</h3>
                <ul className="plain-list">
                  {homeworkHistory.map((item) => (
                    <li key={item.homework_id}>
                      {item.assigned_date.slice(0, 10)} / {item.approved_problem_groups.join(', ')} / {item.completion_status}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="analysis-panel">
                <h3>講師自由記述追加</h3>
                <label className="stack-field">
                  講師メモ
                  <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={4} placeholder="今日の集中度や次回授業で気を付けたい点を記録" />
                </label>
                <div className="detail-actions">
                  <button className="primary-btn" disabled={saveBusy || !note.trim()} onClick={() => void handleAddNote()}>
                    {saveBusy ? '保存中...' : '講師メモを追加'}
                  </button>
                  <button className="secondary-btn compact-btn" onClick={() => startFlow({
                    student_id: selected.student_id,
                    display_name: selected.display_name,
                    grade: selected.grade,
                    target_level: selected.target_level,
                    attention_level: selected.attention_level,
                    homework_completion_rate: selected.homework_completion_rate ?? 0,
                    one_line_analysis: summary.one_line_analysis,
                    recommended_action: summary.recommended_action,
                  })}>この生徒で答案確認へ</button>
                </div>
              </div>
            </div>
          ) : null}
        </SectionCard>
      </div>
    </div>
  )
}
