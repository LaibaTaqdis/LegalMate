import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowRight, Calculator, ClipboardCheck, FileText, Info, ListChecks } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { QueryBoundary, PageSkeleton } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { guidanceService } from '../api/services/guidanceService'

const OTHER = '__other__'
const TOOL_ICON = { calculator: Calculator, letter: FileText, check: ClipboardCheck }

export default function Guide() {
  const { id } = useParams()
  const query = useQuery(signal => guidanceService.guide(id, signal), [id])
  return <QueryBoundary query={query} skeleton={<PageSkeleton cards={2} rows={3} />}>{g => <GuidePage key={g.id} g={g} />}</QueryBoundary>
}

function GuidePage({ g }) {
  const navigate = useNavigate()
  const [picked, setPicked] = useState({})
  const [typed, setTyped] = useState({})
  const answer = q => (picked[q.id] === OTHER ? (typed[q.id] || '').trim() : picked[q.id])
  const ready = g.questions.every(q => answer(q))

  const plan = (withAnswers = true) => {
    const facts = withAnswers ? g.questions.map(q => `${q.text} ${answer(q)}.`).join(' ') : ''
    const text = `${g.situation} ${facts} Please give me an ordered plan: what to do first, the documents to collect, any deadline that matters and where to go.`.replace(/\s+/g, ' ').trim()
    navigate(`/chat?q=${encodeURIComponent(text)}`)
  }

  return (
    <div className="guide">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Dashboard', to: '/dashboard' }, { label: g.title }]} />
      <div className="page-head"><div><h1 className="page-title">{g.title}</h1><p className="page-sub">{g.intro}</p></div></div>

      <div className="guide-grid">
        <section className="card card-pad guide-form">
          <h2 className="card-title"><ListChecks size={20} /> Tell us a little more</h2>
          {g.questions.map(q => (
            <div key={q.id} className="clarify-q guide-q">
              <b>{q.text}</b>
              <div className="clarify-opts" role="radiogroup" aria-label={q.text}>
                {q.options.map(o => (
                  <button key={o} type="button" role="radio" aria-checked={picked[q.id] === o} className={`ps-chip ${picked[q.id] === o ? 'on' : ''}`} onClick={() => setPicked(p => ({ ...p, [q.id]: o }))}>{o}</button>
                ))}
                <button type="button" role="radio" aria-checked={picked[q.id] === OTHER} className={`ps-chip ps-chip-other ${picked[q.id] === OTHER ? 'on' : ''}`} onClick={() => setPicked(p => ({ ...p, [q.id]: OTHER }))}>Other…</button>
              </div>
              {picked[q.id] === OTHER && (
                <input className="input clarify-input" autoFocus maxLength={200} placeholder="Type your answer here" aria-label={`${q.text} Other`} value={typed[q.id] || ''}
                  onChange={e => setTyped(t => ({ ...t, [q.id]: e.target.value }))} onKeyDown={e => { if (e.key === 'Enter' && ready) { e.preventDefault(); plan() } }} />
              )}
            </div>
          ))}
          <div className="guide-go">
            <button className="btn btn-orange btn-lg" disabled={!ready} onClick={() => plan()}>Get my step-by-step plan <ArrowRight size={18} /></button>
            <button type="button" className="link small" onClick={() => plan(false)}>Skip the questions and get a plan anyway</button>
          </div>
          <p className="guide-note"><Info size={15} /> {g.note}</p>
        </section>

        <aside className="card card-pad guide-tools">
          <h2 className="card-title">Tools for this situation</h2>
          {g.tools.length ? (
            <ul>
              {g.tools.map(t => {
                const Icon = TOOL_ICON[t.type] || FileText
                return (
                  <li key={t.link}>
                    <Link to={t.link} className="guide-tool">
                      <span className="icon-tile tile-blue tile-md"><Icon /></span>
                      <div><b>{t.label}</b><span>{t.name}</span></div>
                      <ArrowRight size={16} />
                    </Link>
                  </li>
                )
              })}
            </ul>
          ) : <p className="guide-note">No form or calculator fits this one. The plan will tell you what to collect and where to go.</p>}
        </aside>
      </div>
    </div>
  )
}
