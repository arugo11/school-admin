import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { fetchRagHomeworkRecommendation, regradeProblem, resolveAssetUrl, runAnalysis } from '../lib/api'
import { useDemo } from '../lib/demo-context'
import { SectionCard } from '../components/section-card'
import type { RecommendedProblemGroup, Recommendation } from '../lib/types'

export function AnalysisPage() {
  const { session, setAnalysis, setBanner, setRagRecommendation } = useDemo()
  const navigate = useNavigate()
  const [busyAction, setBusyAction] = useState<string>()
  const [expandedProblem, setExpandedProblem] = useState<string>()
  const [studentNote, setStudentNote] = useState('')
  const [regradeBusy, setRegradeBusy] = useState<string>()
  const [regradeError, setRegradeError] = useState<string>()
  const [ragBusy, setRagBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function loadRecommendation() {
      if (!session.student || !session.normalizedOcr || !session.analysis) return
      setRagBusy(true)
      try {
        const recommendation = await fetchRagHomeworkRecommendation(session.student.student_id, session.normalizedOcr, session.analysis)
        if (!cancelled) {
          setRagRecommendation(recommendation)
        }
      } catch (err) {
        if (!cancelled) {
          setBanner((err as Error).message)
        }
      } finally {
        if (!cancelled) {
          setRagBusy(false)
        }
      }
    }
    void loadRecommendation()
    return () => {
      cancelled = true
    }
  }, [session.student, session.normalizedOcr, session.analysis, setRagRecommendation, setBanner])

  if (!session.student || !session.normalizedOcr || !session.analysis) {
    return <div className="empty-state">分析結果がありません。OCR確認から進めてください。</div>
  }

  async function rerun(action: 'regenerate' | 'lighten') {
    setBusyAction(action)
    const analysis = await runAnalysis(session.student!.student_id, session.normalizedOcr!, action)
    setAnalysis(analysis)
    setRagRecommendation(undefined)
    setBanner(action === 'lighten' ? '宿題セットを軽く調整しました。' : '提案を再生成しました。')
    setBusyAction(undefined)
  }

  async function submitRegrade(problemNo: string) {
    if (!studentNote.trim()) {
      setRegradeError('訂正理由を短く入力してください。')
      return
    }
    setRegradeBusy(problemNo)
    setRegradeError(undefined)
    try {
      const response = await regradeProblem(
        session.student!.student_id,
        session.normalizedOcr!,
        problemNo,
        studentNote,
        session.analysis!,
      )
      setAnalysis(response.analysis)
      setBanner(`${problemNo} の訂正依頼を反映しました。`)
      setExpandedProblem(undefined)
      setStudentNote('')
    } catch (err) {
      setRegradeError((err as Error).message)
    } finally {
      setRegradeBusy(undefined)
    }
  }

  function statusLabel(status: 'correct' | 'incorrect' | 'uncertain') {
    if (status === 'correct') return '正解'
    if (status === 'incorrect') return '誤答'
    return '要確認'
  }

  return (
    <div className="page-grid">
      <div className="page-grid detail-layout">
        <SectionCard title="読み取りと判定">
          <div className="analysis-hero">
            <div className="image-stage">
              {session.previewUrl ? <img className="sheet-preview" src={session.previewUrl} alt="uploaded worksheet" /> : <div className="empty-state">画像プレビューはアップロード後に表示されます。</div>}
            </div>
            <div className="analysis-summary">
              {session.normalizedOcr.test_id ? <div className="banner compact">テストID: {session.normalizedOcr.test_id}</div> : null}
              <div className="pill-row">
                {session.analysis.weak_units.map((item) => <span key={item} className="tag-pill">{item}</span>)}
              </div>
              <div className="analysis-grid single-column">
                <div className="analysis-panel">
                  <h3>誤答パターン</h3>
                  <ul>{session.analysis.error_patterns.map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
                <div className="analysis-panel">
                  <h3>宿題負荷</h3>
                  <p className={`load-pill ${session.analysis.homework_load_fit}`}>{session.analysis.homework_load_fit}</p>
                  <p>{session.analysis.teacher_note}</p>
                </div>
              </div>
            </div>
          </div>
          {session.analysis.problem_feedback.length > 0 ? (
            <div className="problem-feedback-grid">
              {session.analysis.problem_feedback.map((item) => (
                <div key={item.problem_no} className="problem-feedback-card">
                  <div className="ocr-row">
                    <strong>{item.problem_no}</strong>
                    <span className={`grading-badge ${item.grading_status}`}>{statusLabel(item.grading_status)}</span>
                  </div>
                  <p className="muted">教材問題: {item.catalog_problem_no}</p>
                  {(item.work_image_path || item.final_image_path) ? (
                    <div className="crop-strip">
                      {item.work_image_path ? (
                        <figure className="crop-card">
                          <img src={resolveAssetUrl(item.work_image_path)} alt={`${item.problem_no} work crop`} />
                          <figcaption>計算過程の切り出し</figcaption>
                        </figure>
                      ) : null}
                      {item.final_image_path ? (
                        <figure className="crop-card">
                          <img src={resolveAssetUrl(item.final_image_path)} alt={`${item.problem_no} final crop`} />
                          <figcaption>最終解答の切り出し</figcaption>
                        </figure>
                      ) : null}
                    </div>
                  ) : null}
                  <div className="dual-stat-grid">
                    <div>
                      <span>計算過程</span>
                      <strong>{item.work_text || '未抽出'}</strong>
                    </div>
                    <div>
                      <span>最終解答</span>
                      <strong>{item.final_answer || item.recognized_answer}</strong>
                    </div>
                  </div>
                  <div className="dual-stat-grid compact-grid">
                    <div>
                      <span>模範解答</span>
                      <strong>{item.expected_answer}</strong>
                    </div>
                    <div>
                      <span>判定根拠</span>
                      <strong>{item.grading_basis}</strong>
                    </div>
                  </div>
                  <p>{item.comment}</p>
                  {item.regrade_requested ? <div className="banner compact">{item.regrade_outcome}</div> : null}
                  {item.regrade_available ? (
                    <>
                      <button
                        className="secondary-btn"
                        onClick={() => {
                          setExpandedProblem((prev) => prev === item.problem_no ? undefined : item.problem_no)
                          setStudentNote(item.regrade_note ?? '')
                          setRegradeError(undefined)
                        }}
                      >
                        この判定に訂正を依頼
                      </button>
                      {expandedProblem === item.problem_no ? (
                        <div className="regrade-box">
                          <label>
                            訂正理由
                            <textarea
                              value={studentNote}
                              onChange={(event) => setStudentNote(event.target.value)}
                              placeholder="例: 最終解答欄の数字が薄い / 計算過程に符号が残っている"
                              rows={3}
                            />
                          </label>
                          {regradeError ? <div className="error-box">{regradeError}</div> : null}
                          <div className="mode-actions">
                            <button className="secondary-btn" onClick={() => setExpandedProblem(undefined)}>閉じる</button>
                            <button className="primary-btn" disabled={regradeBusy === item.problem_no} onClick={() => submitRegrade(item.problem_no)}>
                              {regradeBusy === item.problem_no ? '再評価中...' : 'この内容で再評価'}
                            </button>
                          </div>
                        </div>
                      ) : null}
                    </>
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}
          <div className="analysis-panel">
            <h3>分析メモ</h3>
            <ul className="plain-list">
              {session.analysis.analysis_rationale.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
          <div className="mode-actions">
            <button className="secondary-btn" disabled={!!busyAction} onClick={() => rerun('regenerate')}>
              {busyAction === 'regenerate' ? '再生成中...' : '再提案'}
            </button>
            <button className="secondary-btn" disabled={!!busyAction} onClick={() => rerun('lighten')}>
              {busyAction === 'lighten' ? '調整中...' : '軽くする'}
            </button>
            <button className="primary-btn" onClick={() => navigate('/students')}>生徒詳細で宿題提案へ</button>
          </div>
        </SectionCard>
        <SectionCard title="提案問題">
          <div className="pill-row">
            <span className={`load-pill ${session.analysis.homework_load_fit}`}>{session.analysis.homework_load_fit}</span>
          </div>
          {ragBusy ? <div className="banner compact">生徒文脈込みの宿題提案を更新しています...</div> : null}
          <div className="recommendation-list compact-list">
            {(session.ragRecommendation?.recommended_problem_groups ?? session.analysis.recommended_homework).map((item: Recommendation | RecommendedProblemGroup) => (
              <div key={'group_id' in item ? item.group_id : item.problem_no} className="recommendation-card">
                <strong>{'group_id' in item ? item.group_id : item.problem_no}</strong>
                <span>{item.difficulty}</span>
                <p>{item.reason}</p>
                {'level_fit_comment' in item ? <small>{item.level_fit_comment}</small> : null}
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
