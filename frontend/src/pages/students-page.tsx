import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { fetchStudents } from '../lib/api'
import { useDemo } from '../lib/demo-context'
import type { StudentProfile } from '../lib/types'
import { SectionCard } from '../components/section-card'
import { StudentCard } from '../components/student-card'

export function StudentsPage() {
  const [students, setStudents] = useState<StudentProfile[]>([])
  const [error, setError] = useState<string>()
  const navigate = useNavigate()
  const { setStudent, setBanner, resetFlow } = useDemo()

  useEffect(() => {
    fetchStudents().then(setStudents).catch((err: Error) => setError(err.message))
  }, [])

  return (
    <div className="page-grid">
      <SectionCard title="生徒一覧">
        {error ? <div className="empty-state">{error}</div> : null}
        <div className="student-grid">
          {students.map((student) => (
            <StudentCard
              key={student.student_id}
              student={student}
              onSelect={(selected) => {
                resetFlow()
                setStudent(selected)
                setBanner(undefined)
                navigate('/upload')
              }}
            />
          ))}
        </div>
      </SectionCard>
    </div>
  )
}
