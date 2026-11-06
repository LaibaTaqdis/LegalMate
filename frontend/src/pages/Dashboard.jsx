import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowRight, BookOpen, Briefcase, Calculator, CheckCircle2, FilePlus2, FileText, Lock, MessageCircleMore,
  MessageSquareText, MoreHorizontal, Scale, Sun, Moon, Sunrise
} from 'lucide-react'
import { Breadcrumb, Donut } from '../components/common'
import { WhatsAppIcon } from '../components/Icons'
import { useUI } from '../components/UIContext'
import { EmptyState, PageSkeleton, QueryBoundary } from '../components/States'
import { useAuth } from '../context/AuthContext'
import { useQuery } from '../hooks/useApi'
import { dashboardService } from '../api/services/dashboardService'
import { formatBytes, formatDate, formatTime } from '../utils/format'

const QUICK = [
  { icon: MessageSquareText, tone: 'blue', title: 'Ask LegalMate', text: 'Get clear, source-backed answers to your legal questions.', cta: 'Start Chatting', to: '/chat' },
  { icon: FilePlus2, tone: 'green', title: 'Upload Document', text: 'Analyse agreements, notices and legal letters with AI.', cta: 'Upload Now', to: '/documents/upload' },
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
}
const STATUS = { completed: ['Completed', 'green'], analysed: ['Analysed', 'blue'], viewed: ['Viewed', 'blue'], processing: ['Processing', 'orange'] }
const VAULT_COLORS = { documents: '#1d4ed8', briefs: '#7c3aed', images: '#22a45a', other: '#cbd5e1' }
const RESOURCE_STYLE = { property: { icon: BookOpen, tone: 'blue' }, labour: { icon: Briefcase, tone: 'green' }, family: { icon: Scale, tone: 'purple' } }

const daysLeft = d => d.daysLeft ?? Math.max(0, Math.ceil((new Date(d.dueDate) - new Date()) / 86400000))

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return { text: 'Good morning', Icon: Sun }
  if (h < 17) return { text: 'Good afternoon', Icon: Sun }
  return { text: 'Good evening', Icon: Moon }
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { toast } = useUI()
  const { user } = useAuth()
  const [tab, setTab] = useState('All')
  const g = greeting()
  const query = useQuery(signal => dashboardService.get(signal), [])

  if (!query.data) return <QueryBoundary query={query} skeleton={<PageSkeleton cards={4} rows={2} />}>{() => null}</QueryBoundary>

  const { activity, vault, resources, deadlines } = query.data
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
            {['All', 'Chats', 'Documents', 'Briefs'].map(t => (
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
                  <button className="icon-btn-plain act-more" aria-label="More" onClick={e => { e.stopPropagation(); toast(`Options for “${a.title}”`, 'info') }}><MoreHorizontal size={18} /></button>
                </li>
              )
            })}
          </ul>
          {!rows.length && <EmptyState title="No activity yet" text="Your chats, documents and briefs will appear here." />}
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
                <li key={v.label}><span className="dv-dot" style={{ background: v.color }} />{v.label}<b>{Math.round(v.value / 1e6)} MB</b></li>
              ))}
            </ul>
          </div>
          <div className="dv-note"><Lock size={18} /><div><b>Your documents are encrypted and private.</b><span>Only you can access your legal records.</span></div></div>
          <Link to="/vault" className="btn btn-navy btn-block btn-lg dv-open">Open Vault <ArrowRight size={18} /></Link>
        </section>
      </div>

      <div className="dash-bottom">
        <section className="card card-pad">
          <div className="card-head">
            <h2 className="card-title">Recommended Legal Resources</h2>
            <Link to="/chat" className="link small">View All <ArrowRight size={15} /></Link>
          </div>
          <div className="res-grid">
            {resources.map(r => {
              const s = RESOURCE_STYLE[r.category] || RESOURCE_STYLE.property
              return (
                <Link to={r.link} key={r.id} className="res-card">
                  <span className={`icon-tile tile-${s.tone} tile-md`}><s.icon /></span>
                  <b>{r.title}</b>
                  <span>{r.summary}</span>
                  <span className="link small">Read More <ArrowRight size={14} /></span>
                </Link>
              )
            })}
          </div>
        </section>

        <section className="card card-pad">
          <div className="card-head">
            <h2 className="card-title">Upcoming Deadlines</h2>
            <Link to="/offline" className="link small">View All <ArrowRight size={15} /></Link>
          </div>
          <ul className="dl-list">
            {deadlines.map(d => {
              const due = new Date(`${d.dueDate}T00:00:00`)
              const left = daysLeft(d)
              return (
                <li key={d.id}>
                  <span className="dl-date"><b>{due.getDate()}</b>{due.toLocaleString('en-US', { month: 'short' }).toUpperCase()}</span>
                  <div className="dl-main"><b>{d.title}</b><span>{d.location}</span></div>
                  <span className={`pill ${left <= 7 ? 'pill-red' : 'pill-red'}`}>{left} day{left === 1 ? '' : 's'} left</span>
                </li>
              )
            })}
          </ul>
          {!deadlines.length && <EmptyState title="No upcoming deadlines" />}
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
