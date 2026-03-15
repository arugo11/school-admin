import type { StudentOverviewItem } from '../lib/types'

export function StudentCard({
  student,
  active,
  onSelect,
  onStartFlow,
}: {
  student: StudentOverviewItem
  active: boolean
  onSelect: (student: StudentOverviewItem) => void
  onStartFlow: (student: StudentOverviewItem) => void
}) {
  const attentionLabel = {
    low: '安定',
    medium: '通常',
    high: '要確認',
    urgent: '優先',
  }[student.attention_level]

  return (
    <article className={active ? 'student-card active-card' : 'student-card'}>
      <button className="student-card-select" onClick={() => onSelect(student)}>
        <div className="student-card-header">
          <div>
            <p className="student-name">{student.display_name}</p>
            <p className="student-grade">{student.grade} / {student.school_name}</p>
            <p className="subtle-label">定期テストまで {student.days_until_regular_exam != null ? `${student.days_until_regular_exam}日` : '未設定'}</p>
          </div>
          <span className={`attention-pill student-attention-pill ${student.attention_level}`}>{attentionLabel}</span>
        </div>
        <div className="student-metrics">
          <div>
            <span>宿題達成率</span>
            <strong>{student.homework_completion_rate}%</strong>
          </div>
          <div>
            <span>推奨対応</span>
            <strong>{student.recommended_action}</strong>
          </div>
        </div>
        <p className="student-summary">{student.one_line_analysis}</p>
      </button>
      <button className="secondary-btn compact-btn" onClick={() => onStartFlow(student)}>
        この生徒で答案確認へ
      </button>
    </article>
  )
}
