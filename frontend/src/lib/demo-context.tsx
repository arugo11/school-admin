import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

import type { AnalysisResult, HomeworkApproval, NormalizedOcr, StudentProfile, UploadResponse } from './types'

type DemoSession = {
  student?: StudentProfile
  upload?: UploadResponse
  normalizedOcr?: NormalizedOcr
  analysis?: AnalysisResult
  approval?: HomeworkApproval
  previewUrl?: string
  banner?: string
}

type DemoContextValue = {
  session: DemoSession
  setStudent: (student: StudentProfile | undefined) => void
  setUpload: (upload: UploadResponse | undefined) => void
  setNormalizedOcr: (ocr: NormalizedOcr | undefined) => void
  setAnalysis: (analysis: AnalysisResult | undefined) => void
  setApproval: (approval: HomeworkApproval | undefined) => void
  setPreviewUrl: (previewUrl: string | undefined) => void
  setBanner: (banner: string | undefined) => void
  resetFlow: () => void
}

const DemoContext = createContext<DemoContextValue | null>(null)

export function DemoProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<DemoSession>({})
  const setStudent = useCallback((student: StudentProfile | undefined) => {
    setSession((prev) => ({ ...prev, student }))
  }, [])
  const setUpload = useCallback((upload: UploadResponse | undefined) => {
    setSession((prev) => ({ ...prev, upload }))
  }, [])
  const setNormalizedOcr = useCallback((normalizedOcr: NormalizedOcr | undefined) => {
    setSession((prev) => ({ ...prev, normalizedOcr }))
  }, [])
  const setAnalysis = useCallback((analysis: AnalysisResult | undefined) => {
    setSession((prev) => ({ ...prev, analysis }))
  }, [])
  const setApproval = useCallback((approval: HomeworkApproval | undefined) => {
    setSession((prev) => ({ ...prev, approval }))
  }, [])
  const setPreviewUrl = useCallback((previewUrl: string | undefined) => {
    setSession((prev) => ({ ...prev, previewUrl }))
  }, [])
  const setBanner = useCallback((banner: string | undefined) => {
    setSession((prev) => ({ ...prev, banner }))
  }, [])
  const resetFlow = useCallback(() => {
    setSession((prev) => ({ student: prev.student }))
  }, [])

  const value = useMemo<DemoContextValue>(() => ({
    session,
    setStudent,
    setUpload,
    setNormalizedOcr,
    setAnalysis,
    setApproval,
    setPreviewUrl,
    setBanner,
    resetFlow
  }), [session, setStudent, setUpload, setNormalizedOcr, setAnalysis, setApproval, setPreviewUrl, setBanner, resetFlow])

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
}

export function useDemo() {
  const context = useContext(DemoContext)
  if (!context) {
    throw new Error('useDemo must be used within DemoProvider')
  }
  return context
}
