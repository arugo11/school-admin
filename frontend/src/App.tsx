import { Route, Routes } from 'react-router-dom'

const NOTICE_MESSAGE = '現在このデモは公開を停止しています. 何かあれば me@argo11.devまで'

function SuspendedNoticePage() {
  return (
    <main className="suspended-shell">
      <section className="suspended-card" aria-labelledby="suspended-title">
        <p className="suspended-eyebrow">School Admin MVP</p>
        <h1 id="suspended-title" className="suspended-title">
          公開停止中
        </h1>
        <p className="suspended-copy">{NOTICE_MESSAGE}</p>
      </section>
    </main>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="*" element={<SuspendedNoticePage />} />
    </Routes>
  )
}
