import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowRight, BookOpen, Bookmark, Briefcase, Calculator, CheckCircle2, ExternalLink, FilePlus2, FileText, Landmark, Lock, MessageCircleMore,
  MessageSquareText, Paperclip, Scale, Sun, Moon
} from 'lucide-react'
import { Breadcrumb, Donut } from '../components/common'
import { WhatsAppIcon } from '../components/Icons'
import { EmptyState, PageSkeleton, QueryBoundary } from '../components/States'
import { useAuth } from '../context/AuthContext'
import { useQuery } from '../hooks/useApi'
import { dashboardService } from '../api/services/dashboardService'
import { formatBytes, formatDate, formatTime } from '../utils/format'

const QUICK = [
  { icon: MessageSquareText, tone: 'blue', title: 'Ask LegalMate', text: 'Get clear, source-backed answers to your legal questions.', cta: 'Start Chatting', to: '/chat' },
  { icon: FilePlus2, tone: 'green', title: 'Upload Document', text: 'Analyse agreements, notices and legal letters with AI.', cta: 'Upload Now', to: '/analysis/new' },
  { icon: FileText, tone: 'purple', title: 'Create Case Brief', text: 'Generate concise case briefs from documents or chats.', cta: 'Create Brief', to: '/case-briefs/new' },
  { icon: Calculator, tone: 'orange', title: 'Open Legal Calculator', text: 'Calculate fines, limitation periods and other legal timelines.', cta: 'Open Calculator', to: '/calculator' },
]

// API `type` / `status` / `category` values -> presentation
const ACTIVITY_STYLE = {
  chat: { icon: MessageCircleMore, tone: 'blue', tab: 'Chats' },
  document: { icon: FileText, tone: 'green', tab: 'Documents' },
  brief: { icon: FileText, tone: 'purple', tab: 'Briefs' },
  calculator: { icon: Calculator, tone: 'orange', tab: 'Chats' },
  resource: { icon: FileText, tone: 'green', tab: 'Documents' },
  saved: { icon: Bookmark, tone: 'orange', tab: 'Saved' },
  file: { icon: Paperclip, tone: 'purple', tab: 'Saved' },
}
const STATUS = { completed: ['Completed', 'green'], saved: ['Saved', 'orange'], failed: ['Failed', 'red'], analysed: ['Analysed', 'blue'], viewed: ['Viewed', 'blue'], processing: ['Processing', 'orange'] }
const HOLIDAY_STATUS = { notified: ['Notified', 'green'], reported: ['Reported', 'blue'], expected: ['Expected', 'orange'] }
const VAULT_COLORS = { documents: '#1d4ed8', briefs: '#7c3aed', images: '#22a45a', other: '#cbd5e1' }
const RESOURCE_STYLE = {
  property: { icon: BookOpen, tone: 'blue' }, labour: { icon: Briefcase, tone: 'green' }, family: { icon: Scale, tone: 'purple' },
  laws: { icon: BookOpen, tone: 'blue' }, courts: { icon: Landmark, tone: 'purple' }, tax: { icon: Scale, tone: 'orange' },
}

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
const parseDay = str => { const [y, m, d] = str.split('-').map(Number); return { y, m: m - 1, d } }
const dayLabel = str => { const { m, d } = parseDay(str); return `${d} ${MONTHS[m].charAt(0)}${MONTHS[m].slice(1).toLowerCase()}` }
const holidayRange = h => (h.start === h.end ? dayLabel(h.start) : `${dayLabel(h.start)} - ${dayLabel(h.end)} ${parseDay(h.end).y}`)
const holidayWhen = h => (h.ongoing ? 'Now' : h.daysUntil === 0 ? 'Today' : h.daysUntil === 1 ? 'Tomorrow' : `In ${h.daysUntil} days`)

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return { text: 'Good morning', Icon: Sun }
  if (h < 17) return { text: 'Good afternoon', Icon: Sun }
  return { text: 'Good evening', Icon: Moon }
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [tab, setTab] = useState('All')
  const g = greeting()
  const query = useQuery(signal => dashboardService.get(signal), [])

  if (!query.data) return <QueryBoundary query={query} skeleton={<PageSkeleton cards={4} rows={2} />}>{() => null}</QueryBoundary>

  const { activity, vault, resources, holidays } = query.data
  const rows = tab === 'All' ? activity : activity.filter(a => ACTIVITY_STYLE[a.type]?.tab === tab)
  const vaultSegments = vault.breakdown.map(b => ({ label: b.label, value: b.bytes, color: VAULT_COLORS[b.category] || '#cbd5e1' }))

  return (
    <div className="dash">
      <div className="dash-head">
        <div>
          <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Dashboard' }]} />
          <h1 className="dash-greet">{g.text}, {user?.firstName} <g.Icon className="dash-sun" size={34} /></h1>
          <p className="page-sub">How can LegalMate help you today?</p>
        </div>
        <div className="dash-head-right">
          <div className="dash-quote">
            <span className="dash-quote-mark">“</span>
            <div><p>Knowledge of law empowers citizens.”</p><span>- A fairer Pakistan for all</span></div>
            <img src="/assets/img/dash-mosque.png" alt="" />
          </div>
          <Link to="/chat" className="btn btn-orange dash-ask"><MessageCircleMore size={22} /> Ask a Legal Question <ArrowRight size={20} /></Link>
        </div>
      </div>

      <div className="dash-quick">
        {QUICK.map(q => (
          <Link to={q.to} key={q.title} className="card dash-qcard">
            <span className={`icon-tile tile-${q.tone} tile-lg`}><q.icon /></span>
            <h3>{q.title}</h3>
            <p>{q.text}</p>
            <div className="dash-qfoot"><span>{q.cta}</span><span className="circle-btn"><ArrowRight size={17} /></span></div>
          </Link>
        ))}
      </div>

      <div className="dash-mid">
        <section className="card card-pad dash-activity">
          <div className="card-head">
            <h2 className="card-title">Recent Activity</h2>
            <Link to="/vault" className="link small">View All <ArrowRight size={15} /></Link>
          </div>
          <div className="seg">
            {['All', 'Chats', 'Documents', 'Saved'].map(t => (
              <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>{t}</button>
            ))}
          </div>
          <ul className="act-list">
            {rows.map(a => {
              const s = ACTIVITY_STYLE[a.type] || ACTIVITY_STYLE.document
              const [label, tone] = STATUS[a.status] || [a.status, 'gray']
              return (
                <li key={a.id} className="act-row" onClick={() => navigate(a.link)}>
                  <span className={`icon-tile tile-${s.tone} tile-sm`}><s.icon /></span>
                  <div className="act-main"><b>{a.title}</b><span>{a.subtitle}</span></div>
                  <div className="act-date"><span>{formatDate(a.occurredAt)}</span><span>{formatTime(a.occurredAt)}</span></div>
                  <span className={`pill pill-${tone} act-pill`}>{label}</span>
                </li>
              )
            })}
          </ul>
          {!rows.length && <EmptyState title="No activity yet" text="Your chats, document analyses and saved items will appear here." />}
        </section>

        <section className="card card-pad dash-vault">
          <div className="card-head">
            <h2 className="card-title">Legal Vault</h2>
            <Link to="/vault" className="link small">Manage <ArrowRight size={15} /></Link>
          </div>
          <div className="dv-body">
            <Donut size={170} stroke={24} segments={vaultSegments}>
              <div className="dv-center"><b>{formatBytes(vault.usedBytes)}</b><span>of {formatBytes(vault.quotaBytes).replace('.0 ', ' ')} used</span></div>
            </Donut>
            <ul className="dv-legend">
              {vaultSegments.map(v => (
                <li key={v.label}><span className="dv-dot" style={{ background: v.color }} />{v.label}<b>{formatBytes(v.value)}</b></li>
              ))}
              <li><span className="dv-dot" style={{ background: '#f59e0b' }} />Saved answers &amp; analyses<b>{vault.savedCount}</b></li>
            </ul>
          </div>
          {vault.filesEnabled === false
            ? <div className="dv-note"><Lock size={18} /><div><b>File storage is switched off on this server.</b><span>Saved answers and analyses still work.</span></div></div>
            : <div className="dv-note"><Lock size={18} /><div><b>{vault.fileCount} file{vault.fileCount === 1 ? '' : 's'} stored, encrypted and private</b><span>Only you can open your legal records.</span></div></div>}
          <Link to="/vault" className="btn btn-navy btn-block btn-lg dv-open">Open Vault <ArrowRight size={18} /></Link>
        </section>
      </div>

      <div className="dash-bottom">
        <section className="card card-pad">
          <div className="card-head">
            <h2 className="card-title">Official Legal Resources</h2>
          </div>
          <div className="res-grid">
            {resources.map(r => {
              const s = RESOURCE_STYLE[r.category] || RESOURCE_STYLE.property
              const external = /^https?:/.test(r.link)
              const body = (
                <>
                  <span className={`icon-tile tile-${s.tone} tile-md`}><s.icon /></span>
                  <b>{r.title}</b>
                  <span>{r.summary}</span>
                  <span className="link small">{external ? <>Open website <ExternalLink size={14} /></> : <>Read More <ArrowRight size={14} /></>}</span>
                </>
              )
              return external
                ? <a href={r.link} key={r.id} className="res-card" target="_blank" rel="noopener noreferrer">{body}</a>
                : <Link to={r.link} key={r.id} className="res-card">{body}</Link>
            })}
          </div>
        </section>

        <section className="card card-pad">
          <div className="card-head">
            <h2 className="card-title">Court Holidays &amp; Vacations</h2>
          </div>
          <ul className="dl-list">
            {holidays.items.map(h => {
              const start = parseDay(h.start)
              const [label, tone] = HOLIDAY_STATUS[h.status] || [h.status, 'gray']
              return (
                <li key={h.id}>
                  <span className="dl-date"><b>{start.d}</b>{MONTHS[start.m]}</span>
                  <div className="dl-main">
                    <b>{h.title}</b>
                    <span>{holidayRange(h)}{h.days > 1 ? ` · ${h.days} days` : ''} · {h.courtNames.join(', ')}</span>
                    <span>{h.url ? <a className="link small" href={h.url} target="_blank" rel="noopener noreferrer">{h.source}</a> : h.source}</span>
                  </div>
                  <div className="dl-side"><span className={`pill pill-${tone}`}>{label}</span><span className="dl-when">{holidayWhen(h)}</span></div>
                </li>
              )
            })}
          </ul>
          {!holidays.items.length && <EmptyState title="No upcoming court holidays on record" />}
          <p className="dl-note">{holidays.note}{holidays.notYetAnnounced ? ` ${holidays.notYetAnnounced}` : ''}{holidays.verifiedOn ? ` Collected on ${formatDate(holidays.verifiedOn)}.` : ''}</p>
        </section>

        <section className="card card-pad dash-wa">
          <div className="dash-wa-text">
            <div className="dash-wa-head">
              <WhatsAppIcon filled size={40} />
              <div><b>Chat on WhatsApp <span className="pill pill-orange dash-new">New</span></b><span>Get instant legal guidance on WhatsApp.</span></div>
            </div>
            <ul className="dash-wa-list">
              <li><CheckCircle2 size={16} />Ask questions</li>
              <li><CheckCircle2 size={16} />Get quick answers</li>
              <li><CheckCircle2 size={16} />Available in English &amp; Urdu</li>
            </ul>
            <Link to="/whatsapp" className="btn btn-green-soft dash-wa-btn">Open WhatsApp Bot <ArrowRight size={17} /></Link>
          </div>
          <img src="/assets/img/dash-whatsapp.png" alt="Legal help, where you are" className="dash-wa-img" />
        </section>
      </div>
    </div>
  )
}
