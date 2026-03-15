import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from './components/app-shell'
import { AnalysisPage } from './pages/analysis-page'
import { HomeworkReviewPage } from './pages/homework-review-page'
import { OcrReviewPage } from './pages/ocr-review-page'
import { StudentsPage } from './pages/students-page'
import { UploadPage } from './pages/upload-page'

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/students" replace />} />
        <Route path="/students" element={<StudentsPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/ocr-review" element={<OcrReviewPage />} />
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/homework-review" element={<HomeworkReviewPage />} />
      </Routes>
    </AppShell>
  )
}
