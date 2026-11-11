import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  AlertTriangle, ArrowRight, Banknote, BookOpen, Briefcase, Building2, Calculator, ExternalLink, FileText, Heart, House, Landmark, Laptop,
  Mail, MessageSquareText, Scale, ShieldCheck, Users
} from 'lucide-react'
import { EmptyState } from '../../components/States'
import { formatDate } from '../../utils/format'

const ICONS = {
  house: House, briefcase: Briefcase, shield: ShieldCheck, laptop: Laptop, alert: AlertTriangle, banknote: Banknote, heart: Heart, file: FileText,
  book: BookOpen, building: Building2, users: Users, message: MessageSquareText, scale: Scale, landmark: Landmark,
}
const TONES = ['blue', 'green', 'purple', 'orange']
const RISK = { Low: 'pill-green', Medium: 'pill-orange', High: 'pill-red' }
const isExternal = l => /^https?:/.test(l || '')

/** Checked items are kept in this browser only (one list per account). */
function useChecked(userId) {
  const key = `lm_checklist_${userId || 'anon'}`
  const [done, setDone] = useState(() => { try { return JSON.parse(localStorage.getItem(key) || '[]') } catch { return [] } })
  useEffect(() => { try { localStorage.setItem(key, JSON.stringify(done)) } catch { /* private window: the list just is not remembered */ } }, [key, done])
  return [done, id => setDone(d => (d.includes(id) ? d.filter(x => x !== id) : [...d, id]))]
}

export default function ForYou({ data, risk, userId }) {
  const navigate = useNavigate()
  const [key, setKey] = useState(data.selected)
  const [section, setSection] = useState('guides')
  const [allGuides, setAllGuides] = useState(false)
  const [done, toggle] = useChecked(userId)
  const persona = data.personas.find(p => p.key === key) || data.personas[0]
  const ask = q => navigate(`/chat?q=${encodeURIComponent(q)}`)
  const checklist = persona.checklist || []
  const finished = checklist.filter(c => done.includes(c.id)).length
  const sections = [
    { key: 'guides', label: 'Guides', n: persona.guides?.length },
    { key: 'rights', label: 'Know your rights', n: persona.topics.length },
    { key: 'tools', label: 'Calculators & letters' },
    checklist.length > 0 && { key: 'checklist', label: 'Checklist & contracts' },
  ].filter(Boolean)
  const active = sections.some(x => x.key === section) ? section : 'guides'
  const guides = allGuides ? persona.guides : (persona.guides || []).slice(0, 6)

  return (
    <section className="card card-pad fy">
      <div className="fy-top">
        <div>
          <h2 className="card-title">{persona.title}</h2>
          <p className="fy-sub">{persona.subtitle}</p>
        </div>
        <div className="seg fy-tabs" role="tablist" aria-label="Kind of user">
          {data.personas.map(p => (
            <button key={p.key} role="tab" aria-selected={key === p.key} className={key === p.key ? 'active' : ''} onClick={() => setKey(p.key)}>
              {p.userType === 'Business owner (SME)' ? 'Business' : p.userType}{p.key === data.selected && <em className="fy-you">For you</em>}
            </button>
          ))}
        </div>
      </div>

      <div className="fy-sections" role="tablist" aria-label="What to show">
        {sections.map(x => (
          <button key={x.key} role="tab" aria-selected={active === x.key} className={active === x.key ? 'on' : ''} onClick={() => setSection(x.key)}>
            {x.label}{x.n != null && <span>{x.n}</span>}
          </button>
        ))}
      </div>

      {active === 'guides' && (
        <div className="fy-panel">
          <p className="fy-lead">Pick your situation, answer a few questions, and get a step-by-step plan.</p>
          <div className="fy-guides">
            {guides.map((g, i) => {
              const Icon = ICONS[g.icon] || FileText
              return (
                <Link key={g.id} to={`/guides/${g.id}`} className="fy-guide">
                  <span className={`icon-tile tile-${TONES[i % TONES.length]} tile-md`}><Icon /></span>
                  <div><b>{g.title}</b><span>{g.text}</span></div>
                  <ArrowRight size={16} />
                </Link>
              )
            })}
          </div>
          {(persona.guides?.length || 0) > 6 && <button type="button" className="link small fy-more" onClick={() => setAllGuides(a => !a)}>{allGuides ? 'Show fewer' : `Show all ${persona.guides.length} guides`}</button>}
        </div>
      )}

      {active === 'rights' && (
        <div className="fy-panel">
          <p className="fy-lead">Each card opens a chat with a ready question, answered from the law library with its sources.</p>
          <div className="fy-grid">
            {persona.topics.map((t, i) => {
              const Icon = ICONS[t.icon] || FileText
              const acts = t.basis?.length ? `Based on: ${t.basis.join('; ')}` : ''
              const inner = (
                <>
                  <span className={`icon-tile tile-${TONES[i % TONES.length]} tile-md`}><Icon /></span>
                  <b>{t.title}</b>
                  <span>{t.text}</span>
                  {acts && <small className="fy-basis" title={acts}>{acts}</small>}
                  <span className="link small">{t.action === 'ask' ? <>Ask LegalMate <ArrowRight size={14} /></> : t.action === 'analyse' ? <>Open <ArrowRight size={14} /></> : <>Open website <ExternalLink size={14} /></>}</span>
                </>
              )
              if (t.action === 'ask') return <button key={t.id} type="button" className="res-card fy-card" onClick={() => ask(t.question)}>{inner}</button>
              if (isExternal(t.link)) return <a key={t.id} className="res-card fy-card" href={t.link} target="_blank" rel="noopener noreferrer">{inner}</a>
              return <Link key={t.id} className="res-card fy-card" to={t.link}>{inner}</Link>
            })}
          </div>
        </div>
      )}

      {active === 'tools' && (
        <div className="fy-panel fy-tools">
          <div>
            <h3 className="fy-h">Calculators, most useful first</h3>
            <ul className="fy-list">
              {(persona.calculators || []).map((c, i) => (
                <li key={c.key}><Link to={`/calculator?type=${c.key}`}><span className="fy-rank">{i + 1}</span><div><b>{c.name}</b><span>{c.why}</span></div><Calculator size={16} /></Link></li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="fy-h">Draft a letter</h3>
            <ul className="fy-list">
              {(persona.letters || []).map(l => (
                <li key={l.id}><Link to={`/letters/${l.id}`}><span className="fy-rank"><Mail size={14} /></span><div><b>{l.title}</b><span>{l.summary}</span></div><ArrowRight size={16} /></Link></li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {active === 'checklist' && (
        <div className="fy-panel fy-tools">
          <div className="fy-check">
            <h3>Business checklist <span>{finished} of {checklist.length} done</span></h3>
            <ul>
              {checklist.map(c => (
                <li key={c.id} className={done.includes(c.id) ? 'done' : ''}>
                  <label><input type="checkbox" checked={done.includes(c.id)} onChange={() => toggle(c.id)} /><span>{c.text}</span></label>
                  {c.question
                    ? <button type="button" className="link small" onClick={() => ask(c.question)}>Ask LegalMate <ArrowRight size={13} /></button>
                    : isExternal(c.link)
                      ? <a className="link small" href={c.link} target="_blank" rel="noopener noreferrer">Open <ExternalLink size={13} /></a>
                      : c.link && <Link className="link small" to={c.link}>Open <ArrowRight size={13} /></Link>}
                </li>
              ))}
            </ul>
            <p className="fy-note">Ticks are saved in this browser only.</p>
          </div>
          <div className="fy-risk">
            <h3>Your recent contract checks</h3>
            {risk?.length ? (
              <ul>
                {risk.map(r => (
                  <li key={r.id}>
                    <Link to={r.link}><b>{r.name}</b><span>{formatDate(r.occurredAt)}</span></Link>
                    {r.level ? <span className={`pill ${RISK[r.level] || 'pill-gray'}`}>{r.level} risk</span> : <span className="pill pill-gray">Not rated</span>}
                  </li>
                ))}
              </ul>
            ) : <EmptyState title="No contract checked yet" text="Upload a contract and its risk level will show here." />}
            <Link to="/contract-check" className="btn btn-outline fy-check-btn">Check a contract <ArrowRight size={16} /></Link>
          </div>
        </div>
      )}

      <details className="fy-foot"><summary>How these cards were made</summary><p>{data.note}</p></details>
    </section>
  )
}
