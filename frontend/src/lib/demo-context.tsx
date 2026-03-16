import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

import type { AnalysisResult, HomeworkApproval, NormalizedOcr, ProcessingJob, RagHomeworkRecommendation, StudentProfile, UploadResponse } from './types'

const PENDING_JOBS_KEY = 'school-admin.pending-jobs'
const SEEN_NOTIFICATIONS_KEY = 'school-admin.seen-job-notifications'

type DemoSession = {
  student?: StudentProfile
  upload?: UploadResponse
  normalizedOcr?: NormalizedOcr
  analysis?: AnalysisResult
  ragRecommendation?: RagHomeworkRecommendation
  approval?: HomeworkApproval
  previewUrl?: string
  banner?: string
  pendingJobs: ProcessingJob[]
  seenJobNotifications: string[]
}

type DemoContextValue = {
  session: DemoSession
  setStudent: (student: StudentProfile | undefined) => void
  setUpload: (upload: UploadResponse | undefined) => void
  setNormalizedOcr: (ocr: NormalizedOcr | undefined) => void
  setAnalysis: (analysis: AnalysisResult | undefined) => void
  setRagRecommendation: (recommendation: RagHomeworkRecommendation | undefined) => void
  setApproval: (approval: HomeworkApproval | undefined) => void
  setPreviewUrl: (previewUrl: string | undefined) => void
  setBanner: (banner: string | undefined) => void
  addPendingJob: (job: ProcessingJob) => void
  removePendingJob: (jobId: string) => void
  markJobNotificationSeen: (jobId: string) => void
  resetFlow: () => void
}

const DemoContext = createContext<DemoContextValue | null>(null)

export function DemoProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<DemoSession>(() => ({
    pendingJobs: typeof window === 'undefined' ? [] : JSON.parse(window.localStorage.getItem(PENDING_JOBS_KEY) ?? '[]'),
    seenJobNotifications: typeof window === 'undefined' ? [] : JSON.parse(window.localStorage.getItem(SEEN_NOTIFICATIONS_KEY) ?? '[]'),
  }))
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
  const setRagRecommendation = useCallback((ragRecommendation: RagHomeworkRecommendation | undefined) => {
    setSession((prev) => ({ ...prev, ragRecommendation }))
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
  const addPendingJob = useCallback((job: ProcessingJob) => {
    setSession((prev) => {
      const pendingJobs = [job, ...prev.pendingJobs.filter((item) => item.job_id !== job.job_id)]
      window.localStorage.setItem(PENDING_JOBS_KEY, JSON.stringify(pendingJobs))
      return { ...prev, pendingJobs }
    })
  }, [])
  const removePendingJob = useCallback((jobId: string) => {
    setSession((prev) => {
      const pendingJobs = prev.pendingJobs.filter((item) => item.job_id !== jobId)
      window.localStorage.setItem(PENDING_JOBS_KEY, JSON.stringify(pendingJobs))
      return { ...prev, pendingJobs }
    })
  }, [])
  const markJobNotificationSeen = useCallback((jobId: string) => {
    setSession((prev) => {
      if (prev.seenJobNotifications.includes(jobId)) {
        return prev
      }
      const seenJobNotifications = [...prev.seenJobNotifications, jobId]
      window.localStorage.setItem(SEEN_NOTIFICATIONS_KEY, JSON.stringify(seenJobNotifications))
      return { ...prev, seenJobNotifications }
    })
  }, [])
  const resetFlow = useCallback(() => {
    setSession((prev) => ({
      student: prev.student,
      banner: prev.banner,
      pendingJobs: prev.pendingJobs,
      seenJobNotifications: prev.seenJobNotifications,
    }))
  }, [])

  const value = useMemo<DemoContextValue>(() => ({
    session,
    setStudent,
    setUpload,
    setNormalizedOcr,
      setAnalysis,
      setRagRecommendation,
      setApproval,
    setPreviewUrl,
    setBanner,
    addPendingJob,
    removePendingJob,
    markJobNotificationSeen,
    resetFlow
  }), [session, setStudent, setUpload, setNormalizedOcr, setAnalysis, setRagRecommendation, setApproval, setPreviewUrl, setBanner, addPendingJob, removePendingJob, markJobNotificationSeen, resetFlow])

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
}

export function useDemo() {
  const context = useContext(DemoContext)
  if (!context) {
    throw new Error('useDemo must be used within DemoProvider')
  }
  return context
}
