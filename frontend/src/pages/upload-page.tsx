import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { runOcr, uploadWorksheet } from '../lib/api'
import { useDemo } from '../lib/demo-context'
import { SectionCard } from '../components/section-card'

export function UploadPage() {
  const { session, setUpload, setNormalizedOcr, setPreviewUrl, setBanner } = useDemo()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const navigate = useNavigate()

  if (!session.student) {
    return <div className="empty-state">先に生徒を選んでください。</div>
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
      const ocr = await runOcr(session.student!.student_id, sourceImageIds.length === 1 ? sourceImageIds[0] : sourceImageIds)
      setNormalizedOcr(ocr.normalized_ocr)
      setBanner('画像を読み取りました。')
      navigate('/ocr-review')
    } catch (err) {
      setError((err as Error).message)
      setBanner('画像の読み取りに失敗しました。ファイルを確認して再試行してください。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page-grid detail-layout">
      <SectionCard title="答案を取り込む" subtitle={`${session.student.display_name} の答案画像を選択します。`}>
        <div className="upload-studio">
          <div className="image-stage">
            {session.previewUrl ? <img className="sheet-preview" src={session.previewUrl} alt="worksheet preview" /> : <div className="empty-state">画像を選択するとプレビューが表示されます。</div>}
          </div>
          <div className="upload-panel">
            <p className="lead-copy">計算過程と最終解答が見える画像を選択してください。</p>
            <label className="upload-label">
              <span>{busy ? '読み取り中...' : '画像を選ぶ / 撮る'}</span>
              <input type="file" accept="image/*,.svg,.pdf" multiple disabled={busy} onChange={(event) => onFileChange(event.target.files)} />
            </label>
            <p className="muted">複数画像を選んだ場合は、まとめてOCRへ渡します。</p>
          </div>
        </div>
        {error ? <div className="error-box">{error}</div> : null}
      </SectionCard>
    </div>
  )
}
