import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import {
  approveHomework,
  createStudentDocument,
  fetchStudentProcessingJobs,
  fetchRagHomeworkRecommendation,
  fetchStudent,
  fetchStudentDocuments,
  fetchStudentHomeworkHistory,
  fetchStudentSchoolWorkProgress,
  fetchStudentsOverview,
  fetchStudentSummary,
  refreshStudentSummary,
  resolveAssetUrl,
  updateStudentSchoolWorkProgress,
} from '../lib/api'
import { useDemo } from '../lib/demo-context'
import type {
  ProcessingJob,
  RecommendedProblemGroup,
  SchoolWorkProgressItem,
  StudentDocument,
  StudentHomeworkHistoryItem,
  StudentOverviewItem,
  StudentProfile,
  StudentStateSummary
} from '../lib/types'
import { SectionCard } from '../components/section-card'
import { MathText } from '../components/math-text'
import { StudentCard } from '../components/student-card'

export function StudentsPage() {
  const [students, setStudents] = useState<StudentOverviewItem[]>([])
  const [classFilter, setClassFilter] = useState('all')
  const [selected, setSelected] = useState<StudentProfile>()
  const [summary, setSummary] = useState<StudentStateSummary>()
  const [documents, setDocuments] = useState<StudentDocument[]>([])
  const [selectedDocument, setSelectedDocument] = useState<StudentDocument>()
  const [openDocumentTypes, setOpenDocumentTypes] = useState<string[]>([])
  const [homeworkHistory, setHomeworkHistory] = useState<StudentHomeworkHistoryItem[]>([])
  const [schoolWorkProgress, setSchoolWorkProgress] = useState<SchoolWorkProgressItem[]>([])
  const [overviewStats, setOverviewStats] = useState<{ total_students: number; urgent_count: number; low_completion_count: number; counseling_priority_count: number; recommended_actions_today: number }>()
  const [error, setError] = useState<string>()
  const [detailBusy, setDetailBusy] = useState(false)
  const [note, setNote] = useState('')
  const [saveBusy, setSaveBusy] = useState(false)
  const [workCompletionRate, setWorkCompletionRate] = useState('0')
  const [workCompletedPages, setWorkCompletedPages] = useState('0')
  const [workTargetPages, setWorkTargetPages] = useState('0')
  const [workNote, setWorkNote] = useState('')
  const [workSaveBusy, setWorkSaveBusy] = useState(false)
  const [ragRecommendation, setRagRecommendation] = useState<RecommendedProblemGroup[]>([])
  const [ragBusy, setRagBusy] = useState(false)
  const [homeworkApproveBusy, setHomeworkApproveBusy] = useState(false)
  const [processingJobs, setProcessingJobs] = useState<ProcessingJob[]>([])
  const [jobNotification, setJobNotification] = useState<string>()
  const navigate = useNavigate()
  const { setStudent, setBanner, resetFlow, session, markJobNotificationSeen, removePendingJob } = useDemo()

  useEffect(() => {
    fetchStudentsOverview()
      .then((payload) => {
        setStudents(payload.students)
        setOverviewStats(payload)
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  useEffect(() => {
    if (!selected) return
    const activeStudent = selected
    let cancelled = false
    async function loadJobs() {
      try {
        const jobs = await fetchStudentProcessingJobs(activeStudent.student_id, 'recent')
        if (cancelled) return
        setProcessingJobs(jobs)
        const latestSuccess = jobs.find((job) => job.status === 'succeeded' && job.result_document_id && !session.seenJobNotifications.includes(job.job_id))
        if (latestSuccess) {
          const [summaryPayload, documentPayload] = await Promise.all([
            fetchStudentSummary(activeStudent.student_id),
            fetchStudentDocuments(activeStudent.student_id),
          ])
          if (cancelled) return
          setSummary(summaryPayload)
          setDocuments(documentPayload)
          setSelectedDocument(documentPayload.find((document) => document.document_id === latestSuccess.result_document_id) ?? documentPayload[0])
          setOpenDocumentTypes((prev) => prev.includes('test_report') ? prev : [...prev, 'test_report'])
          setJobNotification(latestSuccess.notification_message ?? '分析済みに確認テストが追加されました')
          markJobNotificationSeen(latestSuccess.job_id)
          removePendingJob(latestSuccess.job_id)
        }
        jobs.filter((job) => job.status === 'failed').forEach((job) => removePendingJob(job.job_id))
      } catch (err) {
        if (!cancelled) {
          setError((err as Error).message)
        }
      }
    }
    void loadJobs()
    const interval = window.setInterval(loadJobs, 3000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [selected, session.seenJobNotifications, markJobNotificationSeen, removePendingJob])

  const gradeOptions = ['all', ...Array.from(new Set(students.map((student) => student.grade)))]
  const visibleStudents = classFilter === 'all' ? students : students.filter((student) => student.grade === classFilter)
  const documentGroups = [
    { key: 'test_report', label: '確認テスト' },
    { key: 'mock_exam', label: '塾内模試' },
    { key: 'homework_history', label: '宿題履歴' },
    { key: 'teacher_note', label: '講師メモ' },
    { key: 'counseling_memo', label: '面談メモ' },
    { key: 'attendance', label: '出欠' },
    { key: 'score_trend', label: '成績推移' },
  ] as const

  async function loadStudentDetail(studentId: string) {
    setDetailBusy(true)
    try {
      const [studentPayload, summaryPayload, documentPayload, homeworkPayload, schoolWorkPayload] = await Promise.all([
        fetchStudent(studentId),
        fetchStudentSummary(studentId),
        fetchStudentDocuments(studentId),
        fetchStudentHomeworkHistory(studentId),
        fetchStudentSchoolWorkProgress(studentId),
      ])
      setSelected(studentPayload)
      setSummary(summaryPayload)
      setDocuments(documentPayload)
      setSelectedDocument(documentPayload[0])
      setOpenDocumentTypes(documentPayload[0] ? [documentPayload[0].document_type] : [])
      setHomeworkHistory(homeworkPayload)
      setSchoolWorkProgress(schoolWorkPayload)
      setRagRecommendation([])
      const firstWork = schoolWorkPayload[0]
      setWorkCompletionRate(String(firstWork?.completion_rate ?? 0))
      setWorkCompletedPages(String(firstWork?.completed_pages ?? 0))
      setWorkTargetPages(String(firstWork?.target_pages ?? 0))
      setWorkNote(firstWork?.note ?? '')
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
      const created = await createStudentDocument(selected.student_id, {
        document_type: 'teacher_note',
        title: `${new Date().toISOString().slice(0, 10)} 講師追記`,
        body_text: note.trim(),
        source_system: 'manual',
        authored_by: 'teacher',
        document_date: new Date().toISOString(),
      })
      const [summaryPayload, documentPayload, homeworkPayload] = await Promise.all([
        fetchStudentSummary(selected.student_id),
        fetchStudentDocuments(selected.student_id),
        fetchStudentHomeworkHistory(selected.student_id),
      ])
      setSummary(summaryPayload)
      setDocuments(documentPayload)
      setHomeworkHistory(homeworkPayload)
      setSelectedDocument(documentPayload.find((document) => document.document_id === created.document_id) ?? created)
      setOpenDocumentTypes((prev) => prev.includes('teacher_note') ? prev : [...prev, 'teacher_note'])
      setNote('')
      setBanner('講師メモを追加しました。')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSaveBusy(false)
    }
  }

  async function handleSaveSchoolWork() {
    if (!selected) return
    setWorkSaveBusy(true)
    try {
      const payload = await updateStudentSchoolWorkProgress(selected.student_id, {
        subject_name: '数学',
        workbook_name: '学校ワーク',
        completion_rate: Number(workCompletionRate),
        completed_pages: Number(workCompletedPages),
        target_pages: Number(workTargetPages),
        note: workNote.trim(),
      })
      const refreshed = await fetchStudentSchoolWorkProgress(selected.student_id)
      setSchoolWorkProgress(refreshed)
      setWorkCompletionRate(String(payload.completion_rate))
      setWorkCompletedPages(String(payload.completed_pages))
      setWorkTargetPages(String(payload.target_pages))
      setWorkNote(payload.note)
      setBanner('学校ワーク進捗を更新しました。')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setWorkSaveBusy(false)
    }
  }

  async function handleGenerateHomeworkFromDocument() {
    if (!selected || !selectedDocument) return
    setRagBusy(true)
    try {
      const recommendation = await fetchRagHomeworkRecommendation(
        selected.student_id,
        selectedDocument.payload?.normalized_ocr,
        selectedDocument.payload?.analysis,
        selectedDocument.document_id,
      )
      setRagRecommendation(recommendation.recommended_problem_groups)
      setBanner('大問単位の宿題提案を生成しました。')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setRagBusy(false)
    }
  }

  async function handleApproveGeneratedHomework() {
    if (!selected || ragRecommendation.length === 0) return
    setHomeworkApproveBusy(true)
    try {
      await approveHomework({
        student_id: selected.student_id,
        approved_problem_nos: ragRecommendation.map((item) => item.group_id),
        removed_problem_nos: [],
        approval_mode: 'teacher-approved-student-panel',
        teacher_comment: '生徒詳細パネルで承認',
        approved_at: new Date().toISOString(),
      })
      const homeworkPayload = await fetchStudentHomeworkHistory(selected.student_id)
      setHomeworkHistory(homeworkPayload)
      setBanner('宿題指示を承認して履歴へ保存しました。')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setHomeworkApproveBusy(false)
    }
  }

  function toggleDocumentType(documentType: string) {
    setOpenDocumentTypes((prev) => prev.includes(documentType) ? prev.filter((item) => item !== documentType) : [...prev, documentType])
  }

  function startFlow(studentCard: StudentOverviewItem) {
    const profile: StudentProfile = {
      student_id: studentCard.student_id,
      display_name: studentCard.display_name,
      grade: studentCard.grade,
      class_name: studentCard.class_name,
      school_name: studentCard.school_name,
      next_regular_exam_date: studentCard.next_regular_exam_date,
      days_until_regular_exam: studentCard.days_until_regular_exam,
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
      <SectionCard title="教室全体の状況">
        {error ? <div className="empty-state">{error}</div> : null}
        <div className="overview-strip">
          <div className="callout-box"><span>在籍</span><strong>{overviewStats?.total_students ?? students.length}</strong></div>
          <div className="callout-box"><span>要確認</span><strong>{overviewStats?.urgent_count ?? 0}</strong></div>
          <div className="callout-box"><span>宿題低達成</span><strong>{overviewStats?.low_completion_count ?? 0}</strong></div>
          <div className="callout-box"><span>本日の推奨対応</span><strong>{overviewStats?.recommended_actions_today ?? 0}</strong></div>
        </div>
      </SectionCard>
      <div className={selected ? 'dashboard-main detail-open' : 'dashboard-main detail-closed'}>
        <SectionCard title="生徒パネル一覧">
          <div className="detail-actions">
            <label className="filter-field">
              学年
              <select value={classFilter} onChange={(event) => setClassFilter(event.target.value)}>
                {gradeOptions.map((option) => (
                  <option key={option} value={option}>{option === 'all' ? 'すべて' : option}</option>
                ))}
              </select>
            </label>
          </div>
          <div className={selected ? 'student-grid' : 'student-grid wide-grid'}>
            {visibleStudents.map((student) => (
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
        {selected ? (
          <SectionCard title={`${selected.display_name} の詳細`}>
            {detailBusy ? <div className="banner compact">詳細を更新しています...</div> : null}
            {jobNotification ? <div className="banner compact">{jobNotification}</div> : null}
            {summary ? (
              <div className="student-detail-pane">
                {processingJobs.find((job) => job.status === 'queued' || job.status === 'running') ? (
                  <div className="banner compact">
                    処理中: {processingJobs.find((job) => job.status === 'queued' || job.status === 'running')?.progress_message}
                  </div>
                ) : null}
                <div className="detail-actions">
                  <span className={`attention-pill ${selected.attention_level}`}>{selected.grade}</span>
                  <button className="secondary-btn compact-btn" onClick={() => void handleRefreshSummary()}>手動更新</button>
                </div>
                <div className="detail-meta-grid">
                  <div className="callout-box"><span>学校名</span><strong>{selected.school_name || '未設定'}</strong></div>
                  <div className="callout-box"><span>定期テストまで</span><strong>{selected.days_until_regular_exam != null ? `${selected.days_until_regular_exam}日` : '未設定'}</strong></div>
                </div>
                <div className="analysis-grid single-column">
                  <div className="analysis-panel">
                    <h3>現在の状態</h3>
                    <p>{summary.current_status}</p>
                    <p className="subtle-label">根拠: {summary.current_status_sources.join(' / ')}</p>
                  </div>
                  <div className="analysis-panel">
                    <h3>直近の危険信号</h3>
                    <ul className="plain-list">{summary.risk_signals.map((item) => <li key={item}>{item}</li>)}</ul>
                    <p className="subtle-label">根拠: {summary.risk_signal_sources.join(' / ')}</p>
                  </div>
                  <div className="analysis-panel">
                    <h3>次に打つべき手</h3>
                    <ul className="plain-list">{summary.next_best_actions.map((item) => <li key={item}>{item}</li>)}</ul>
                    <p className="subtle-label">根拠: {summary.next_best_action_sources.join(' / ')}</p>
                  </div>
                  <div className="analysis-panel">
                    <h3>推奨対応</h3>
                    <p>{summary.recommended_response}</p>
                    <p className="subtle-label">根拠: {summary.recommended_response_sources.join(' / ')}</p>
                  </div>
                </div>
                <div className="detail-meta-grid">
                  <div className="callout-box"><span>宿題達成率</span><strong>{selected.homework_completion_rate ?? 0}%</strong></div>
                  <div className="callout-box"><span>一言AI分析</span><strong>{summary.one_line_analysis}</strong></div>
                </div>
                <div className="analysis-panel">
                  <h3>学校ワーク進捗</h3>
                  <ul className="plain-list">
                    {schoolWorkProgress.map((item) => (
                      <li key={item.progress_id}>
                        {item.subject_name} / {item.workbook_name} / {item.completion_rate}% ({item.completed_pages}/{item.target_pages}ページ)
                      </li>
                    ))}
                  </ul>
                  <div className="analysis-grid two-column">
                    <label className="stack-field">
                      進捗率
                      <input value={workCompletionRate} onChange={(event) => setWorkCompletionRate(event.target.value)} type="number" min="0" max="100" />
                    </label>
                    <label className="stack-field">
                      進んだページ
                      <input value={workCompletedPages} onChange={(event) => setWorkCompletedPages(event.target.value)} type="number" min="0" />
                    </label>
                    <label className="stack-field">
                      目標ページ
                      <input value={workTargetPages} onChange={(event) => setWorkTargetPages(event.target.value)} type="number" min="1" />
                    </label>
                    <label className="stack-field">
                      メモ
                      <input value={workNote} onChange={(event) => setWorkNote(event.target.value)} placeholder="例: 連立方程式まで終了" />
                    </label>
                  </div>
                  <div className="detail-actions">
                    <button className="primary-btn" disabled={workSaveBusy} onClick={() => void handleSaveSchoolWork()}>
                      {workSaveBusy ? '保存中...' : '学校ワーク進捗を更新'}
                    </button>
                  </div>
                </div>
                <div className="analysis-panel">
                  <h3>ドキュメント一覧</h3>
                  <div className="document-ribbon-list">
                    {documentGroups.map((group) => {
                      const groupDocuments = documents.filter((document) => document.document_type === group.key)
                      if (groupDocuments.length === 0) return null
                      const isOpen = openDocumentTypes.includes(group.key)
                      return (
                        <section key={group.key} className="ribbon-section">
                          <button type="button" className={isOpen ? 'ribbon-toggle open' : 'ribbon-toggle'} onClick={() => toggleDocumentType(group.key)}>
                            <strong>{group.label}</strong>
                            <span>{isOpen ? '閉じる' : `開く (${groupDocuments.length})`}</span>
                          </button>
                          {isOpen ? (
                            <div className="ribbon-body">
                              {groupDocuments.map((document) => (
                                <button
                                  key={document.document_id}
                                  type="button"
                                  className={selectedDocument?.document_id === document.document_id ? 'document-link active-link' : 'document-link'}
                                  onClick={() => setSelectedDocument(document)}
                                >
                                  {document.title}
                                </button>
                              ))}
                            </div>
                          ) : null}
                        </section>
                      )
                    })}
                  </div>
                  {selectedDocument ? (
                    <div className="document-viewer">
                      <div className="ocr-row">
                        <strong>{selectedDocument.title}</strong>
                        <span className="tag-pill">{selectedDocument.document_type}</span>
                      </div>
                      <p className="subtle-label">文書日付: {selectedDocument.document_date.slice(0, 10)}</p>
                      <div className="viewer-body">
                        <p>{selectedDocument.body_text}</p>
                      </div>
                      {selectedDocument.asset_paths && selectedDocument.asset_paths.length > 0 ? (
                        <div className="crop-strip">
                          {selectedDocument.asset_paths.map((path) => (
                            <a key={path} href={resolveAssetUrl(path)} target="_blank" rel="noreferrer" className="document-link">
                              画像を開く: {path.split('/').pop()}
                            </a>
                          ))}
                        </div>
                      ) : null}
                      {selectedDocument.document_type === 'test_report' && selectedDocument.payload?.analysis ? (
                        <div className="analysis-panel">
                          <h3>最新確認テスト分析</h3>
                          <p>弱点単元: <MathText text={selectedDocument.payload.analysis.weak_units.join(' / ') || 'なし'} inline /></p>
                          <p>誤答傾向: <MathText text={selectedDocument.payload.analysis.error_patterns.join(' / ') || 'なし'} inline /></p>
                          <p>宿題負荷: {selectedDocument.payload.analysis.homework_load_fit}</p>
                          <div className="detail-actions">
                            <button className="secondary-btn compact-btn" disabled={ragBusy} onClick={() => void handleGenerateHomeworkFromDocument()}>
                              {ragBusy ? '生成中...' : 'この分析から宿題指示を生成'}
                            </button>
                            <button className="primary-btn compact-btn" disabled={homeworkApproveBusy || ragRecommendation.length === 0} onClick={() => void handleApproveGeneratedHomework()}>
                              {homeworkApproveBusy ? '承認中...' : '提案を承認して保存'}
                            </button>
                          </div>
                          {ragRecommendation.length > 0 ? (
                            <ul className="plain-list">
                              {ragRecommendation.map((item) => (
                                <li key={item.group_id}>
                                  <MathText text={`${item.group_id} / ${item.unit_name} / ${item.reason}`} />
                                </li>
                              ))}
                            </ul>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
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
                      class_name: selected.class_name ?? '',
                      school_name: selected.school_name ?? '',
                      next_regular_exam_date: selected.next_regular_exam_date ?? null,
                      days_until_regular_exam: selected.days_until_regular_exam ?? null,
                      target_level: selected.target_level,
                      attention_level: selected.attention_level,
                      homework_completion_rate: selected.homework_completion_rate ?? 0,
                      one_line_analysis: summary.one_line_analysis,
                      recommended_action: summary.recommended_action,
                    })}>この生徒で撮影へ</button>
                  </div>
                </div>
              </div>
            ) : null}
          </SectionCard>
        ) : null}
      </div>
    </div>
  )
}
