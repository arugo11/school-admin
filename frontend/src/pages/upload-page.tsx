import { useState } from 'react'

import { enqueueAnalysis, fetchProcessingJob, uploadWorksheet } from '../lib/api'
import { useDemo } from '../lib/demo-context'
import { SectionCard } from '../components/section-card'
import type { ProcessingJob } from '../lib/types'

export function UploadPage() {
  const { session, setUpload, setPreviewUrl, setBanner } = useDemo()
  const [busy, setBusy] = useState(false)
  const [job, setJob] = useState<ProcessingJob>()
  const [error, setError] = useState<string>()

  if (!session.student) {
    return <div className="empty-state">先に生徒を選んでください。</div>
  }

  async function pollJob(jobId: string) {
    for (let index = 0; index < 120; index += 1) {
      const latest = await fetchProcessingJob(jobId)
      setJob(latest)
      if (latest.status === 'succeeded' || latest.status === 'failed') {
        return latest
      }
      await new Promise((resolve) => setTimeout(resolve, 1500))
    }
    return undefined
  }

  async function onFileChange(files: FileList | null) {
    if (!files || files.length === 0) {
      return
    }
    setBusy(true)
    setError(undefined)
    try {
      const fileList = Array.from(files)
      setPreviewUrl(URL.createObjectURL(fileList[0]))
      const uploads = []
      for (const file of fileList) {
        uploads.push(await uploadWorksheet(session.student!.student_id, file))
      }
      setUpload(uploads[uploads.length - 1])
      const sourceImageIds = uploads.map((upload) => upload.source_image_id)
      const queued = await enqueueAnalysis(session.student!.student_id, sourceImageIds.length === 1 ? sourceImageIds[0] : sourceImageIds)
      setJob(queued)
      const finished = await pollJob(queued.job_id)
      if (finished?.status === 'succeeded') {
        setBanner('バックグラウンド処理が完了しました。生徒詳細で分析結果と宿題提案を確認できます。')
      } else if (finished?.status === 'failed') {
        setError(finished.error_detail ?? '処理に失敗しました。再撮影して再試行してください。')
        setBanner('バックグラウンド処理に失敗しました。')
      } else {
        setError('処理がタイムアウトしました。しばらく待ってから生徒詳細を更新してください。')
      }
    } catch (err) {
      setError((err as Error).message)
      setBanner('画像の読み取りに失敗しました。ファイルを確認して再試行してください。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page-grid detail-layout">
      <SectionCard title="答案を取り込む">
        <div className="upload-studio">
          <div className="image-stage">
            {session.previewUrl ? <img className="sheet-preview" src={session.previewUrl} alt="worksheet preview" /> : <div className="empty-state">画像を選択してください。</div>}
          </div>
          <div className="upload-panel">
            <p className="lead-copy">{session.student.display_name} の答案画像を選択します。</p>
            <label className="upload-label">
              <span>{busy ? '処理を開始しています...' : '画像を選ぶ / 撮る'}</span>
              <input type="file" accept="image/*,.svg,.pdf" multiple disabled={busy} onChange={(event) => onFileChange(event.target.files)} />
            </label>
            <p className="muted">複数枚も選択できます。</p>
            {job ? (
              <div className="banner compact">
                ステータス: {job.status} / {job.progress_message}
              </div>
            ) : null}
          </div>
        </div>
        {error ? <div className="error-box">{error}</div> : null}
      </SectionCard>
    </div>
  )
}
