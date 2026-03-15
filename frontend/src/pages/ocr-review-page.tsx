import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { resolveAssetUrl, runAnalysis } from '../lib/api'
import { useDemo } from '../lib/demo-context'
import { SectionCard } from '../components/section-card'

export function OcrReviewPage() {
  const { session, setNormalizedOcr, setAnalysis, setBanner } = useDemo()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)

  if (!session.student || !session.normalizedOcr) {
    return <div className="empty-state">OCR データがありません。アップロードから進めてください。</div>
  }

  const current = session.normalizedOcr

  async function continueToAnalysis() {
    setBusy(true)
    const analysis = await runAnalysis(session.student!.student_id, current, 'initial')
    setAnalysis(analysis)
    setBanner('分析結果を更新しました。')
    setBusy(false)
    navigate('/analysis')
  }

  return (
    <div className="page-grid">
      <SectionCard title="OCR確認" subtitle="画像と抽出結果を確認し、必要な箇所を修正します。">
        <div className="review-layout">
          <div className="image-stage">
            {session.previewUrl ? <img className="sheet-preview" src={session.previewUrl} alt="uploaded worksheet" /> : <div className="empty-state">画像プレビューはアップロード後に表示されます。</div>}
            {current.test_id ? <div className="banner compact">テストID: {current.test_id}</div> : null}
          </div>
          <div className="review-panel">
            <div className="confidence-box compact">
              <strong>要確認 {current.ocr_confidence_summary.low_confidence_count}件</strong>
              {current.ocr_confidence_summary.notes.length ? (
                <ul>
                  {current.ocr_confidence_summary.notes.map((note) => <li key={note}>{note}</li>)}
                </ul>
              ) : <p>大きな不確実箇所は見つかっていません。</p>}
            </div>
            <div className="ocr-list">
              {current.items.map((item, index) => (
                <div className="ocr-item-card" key={`${item.problem_no}-${index}`}>
                  <div className="ocr-row">
                    <strong>{item.problem_no}</strong>
                    <span className="subtle-label">{item.answer_source === 'final_answer' ? '最終解答欄優先' : '要確認'}</span>
                  </div>
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
                  {item.work_text !== undefined || item.final_answer !== undefined ? (
                    <div className="dual-answer-grid">
                      <label>
                        計算過程
                        <textarea
                          value={item.work_text ?? ''}
                          onChange={(event) => {
                            const next = { ...current, items: current.items.map((entry, itemIndex) => itemIndex === index ? { ...entry, work_text: event.target.value } : entry) }
                            setNormalizedOcr(next)
                          }}
                          rows={3}
                        />
                      </label>
                      <label>
                        最終解答
                        <input
                          value={item.final_answer ?? item.recognized_answer}
                          onChange={(event) => {
                            const next = {
                              ...current,
                              items: current.items.map((entry, itemIndex) => itemIndex === index ? {
                                ...entry,
                                final_answer: event.target.value,
                                recognized_answer: event.target.value || 'unknown',
                                answer_source: event.target.value ? 'final_answer' as const : 'unknown' as const
                              } : entry)
                            }
                            setNormalizedOcr(next)
                          }}
                        />
                      </label>
                    </div>
                  ) : (
                    <label>
                      回答候補
                      <input
                        value={item.recognized_answer}
                        onChange={(event) => {
                          const next = { ...current, items: current.items.map((entry, itemIndex) => itemIndex === index ? { ...entry, recognized_answer: event.target.value } : entry) }
                          setNormalizedOcr(next)
                        }}
                      />
                    </label>
                  )}
                  <p className="muted">{item.raw_text}</p>
                  {item.uncertainty.length ? <div className="uncertainty-chip">{item.uncertainty.join(' / ')}</div> : null}
                </div>
              ))}
            </div>
          </div>
        </div>
        <button className="primary-btn" disabled={busy} onClick={continueToAnalysis}>{busy ? '分析中...' : '分析へ進む'}</button>
      </SectionCard>
    </div>
  )
}
