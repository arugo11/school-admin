import type { StudentProfile } from '../lib/types'

export function StudentCard({ student, onSelect }: { student: StudentProfile; onSelect: (student: StudentProfile) => void }) {
  const avg = Math.round(student.recent_scores.reduce((sum, value) => sum + value, 0) / student.recent_scores.length)
  const attentionLabel = {
    low: '安定',
    medium: '通常',
    high: '要確認',
    urgent: '優先',
  }[student.attention_level]

  return (
    <button className="student-card" onClick={() => onSelect(student)}>
      <div className="student-card-header">
        <div>
          <p className="student-name">{student.display_name}</p>
          <p className="student-grade">{student.grade} / {student.target_level}</p>
        </div>
        <span className={`attention-pill ${student.attention_level}`}>{attentionLabel}</span>
      </div>
      <p className="student-summary">{student.persona_summary}</p>
      <div className="student-metrics">
        <div>
          <span>平均点</span>
          <strong>{avg}</strong>
        </div>
        <div>
          <span>優先課題</span>
          <strong>{student.weakness_history[0] ?? '確認中'}</strong>
        </div>
      </div>
      <p className="student-footnote">宿題メモ: {student.homework_style_notes}</p>
    </button>
  )
}
