import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle, ArrowRight, Bookmark, CalendarDays, CheckCircle2, ChevronDown, ChevronRight, ChevronUp,
  CircleHelp, Download, ExternalLink, FileText, ListChecks, Loader2, MessageCircleMore, MoreHorizontal, Share2,
  ShieldAlert, ShieldCheck, Users, Landmark, FileCheck2, Sparkles
} from 'lucide-react'
import { Breadcrumb, Donut } from '../components/common'
import { FileIcon } from '../components/Icons'
import { useUI } from '../components/UIContext'
import { ErrorState, PageSkeleton, QueryBoundary } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { documentService } from '../api/services/documentService'
import { formatBytes, formatDate, formatDateTime } from '../utils/format'

const RISK_TONE = { Low: 'green', Medium: 'orange', High: 'red' }
const FILE_TYPE_LABEL = { pdf: 'PDF Document', docx: 'Word Document', jpg: 'JPG Image', png: 'PNG Image' }
const isRunning = a => a && (a.status === 'queued' || a.status === 'processing')

export default function Analysis() {
  const { id = 'tenancy' } = useParams()
  const query = useQuery(signal => documentService.getAnalysis(id, signal), [id], { pollInterval: 3000, shouldPoll: isRunning })

  return (
    <QueryBoundary query={query} skeleton={<PageSkeleton cards={4} rows={2} />}>
      {a => {
        if (a.status === 'failed') return <ErrorState error={{ message: a.error || 'The analysis could not be completed. Please try uploading the document again.' }} />
        if (isRunning(a)) return <AnalysisProgress a={a} />
        return <AnalysisResult a={a} />
      }}
    </QueryBoundary>
  )
}

function Preview({ doc, title }) {
  return doc.thumbnailUrl ? <img src={doc.thumbnailUrl} alt="" /> : <>
    <b>{title.toUpperCase()}</b>
    {Array.from({ length: 16 }).map((_, i) => <i key={i} style={{ width: `${60 + ((i * 37) % 40)}%` }} />)}
  </>
}

function AnalysisProgress({ a }) {
  return (
    <div className="analysis">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Analysis', to: '/analysis' }, { label: 'Details' }]} />
      <div className="card state-box">
        <span className="icon-tile tile-blue tile-lg"><Sparkles /></span>
        <b>Analysing {a.document?.name || 'your document'}…</b>
        <p>LegalMate is reading the document and identifying clauses, risks and deadlines. This usually takes under a minute.</p>
        <div className="progress" style={{ width: 320 }}><span style={{ width: `${a.progress || 10}%`, background: '#1d5fd6' }} /></div>
        <span className="muted small"><Loader2 size={14} className="spin" style={{ display: 'inline', verticalAlign: -2 }} /> {a.progress || 0}% complete</span>
      </div>
    </div>
  )
}

function AnalysisResult({ a }) {
  const navigate = useNavigate()
  const { toast } = useUI()
  const [openClauses, setOpenClauses] = useState(true)
  const [allClauses, setAllClauses] = useState(false)
  const [openRisks, setOpenRisks] = useState(true)
  const [allRisks, setAllRisks] = useState(false)
  const [expanded, setExpanded] = useState(null)
  const [openLaw, setOpenLaw] = useState(null)
  const [sections, setSections] = useState({})
  const [busy, setBusy] = useState(null)

  const showLaw = id => {
    setOpenLaw(id)
    setTimeout(() => document.getElementById(`law-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 60)
  }
  const doc = a.document
  const docLink = doc.vaultDocumentId ? `/vault/document/${doc.vaultDocumentId}` : null     // the Legal Vault keeps originals; without it there is no page to open
  const title = doc.name.replace(/\.[a-z]+$/i, '')
  const clauses = allClauses ? a.clauses : a.clauses.slice(0, 5)
  const risks = allRisks ? a.risks : a.risks.slice(0, 3)
  const dist = a.riskDistribution
  const totalIssues = dist.high + dist.medium + dist.low
  const SECTIONS = [
    { key: 'obl', icon: Users, title: 'Obligations', items: a.obligations },
    { key: 'dates', icon: CalendarDays, title: 'Important Dates', items: a.importantDates },
    { key: 'miss', icon: CircleHelp, title: 'Missing Information', items: a.missingInformation },
  ]

  const act = async (key, fn, success) => {
    setBusy(key)
    try { const r = await fn(); if (success) toast(typeof success === 'function' ? success(r) : success) } catch (e) { toast(e.message, 'info') } finally { setBusy(null) }
  }
  const download = () => act('download', () => documentService.downloadReport(a.id, `${title.replace(/\s+/g, '_')}_Analysis.pdf`), `Report downloaded: ${title.replace(/\s+/g, '_')}_Analysis.pdf`)
  const save = () => act('save', () => documentService.saveToVault(a.id), 'Saved to Legal Vault')
  const share = () => act('share', async () => { const { url } = await documentService.share(a.id); await navigator.clipboard?.writeText(url) }, 'Share link copied')

  return (
    <div className="analysis">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Analysis', to: '/analysis' }, { label: title, ...(docLink ? { to: docLink } : {}) }]} />
      <div className="an-head">
        <span className="an-file"><FileIcon type={doc.fileType} size={30} /></span>
        <div className="an-title">
          <h1>{doc.name} <span className="pill pill-blue">{doc.documentType}</span></h1>
          <p>Uploaded on {formatDate(doc.uploadedAt)} • {doc.pages} pages • {formatBytes(doc.sizeBytes)}</p>
        </div>
        <div className="an-actions">
          <span className="pill pill-green an-complete"><CheckCircle2 size={17} fill="#22a45a" color="#fff" /> Analysis Complete</span>
          <button className="btn btn-outline" onClick={download} disabled={busy === 'download'}>{busy === 'download' ? <Loader2 size={17} className="spin" /> : <Download size={17} />} Download Report</button>
          <button className="btn btn-outline" onClick={save} disabled={busy === 'save'}>{busy === 'save' ? <Loader2 size={17} className="spin" /> : <Bookmark size={17} />} Save to Vault</button>
          <button className="btn btn-outline" onClick={share} disabled={busy === 'share'}><Share2 size={17} /> Share</button>
          <button className="icon-btn" aria-label="More" onClick={() => toast('More options coming soon', 'info')}><MoreHorizontal size={18} /></button>
        </div>
      </div>

      {a.notes?.length > 0 && (
        <div className="an-notes" role="note">
          <AlertTriangle size={18} />
          <ul>{a.notes.map(n => <li key={n}>{n}</li>)}</ul>
        </div>
      )}

      <div className="an-stats">
        <div className="card an-stat"><span className={`icon-tile tile-${RISK_TONE[a.overallRisk.level]} tile-lg`}><ShieldAlert /></span><div><span>Overall Risk</span><b className={`t-${RISK_TONE[a.overallRisk.level]}`}>{a.overallRisk.level}</b><small>{a.overallRisk.note}</small></div></div>
        <div className="card an-stat"><span className="icon-tile tile-blue tile-lg"><FileText /></span><div><span>Important Clauses</span><b>{a.counts.clauses}</b><small>Key clauses identified</small></div></div>
        <div className="card an-stat"><span className="icon-tile tile-red tile-lg"><CalendarDays /></span><div><span>Deadlines</span><b className="t-red">{a.counts.deadlines}</b><small>Important dates found</small></div></div>
        <div className="card an-stat"><span className="icon-tile tile-red tile-lg"><AlertTriangle /></span><div><span>Missing Information</span><b className="t-red">{a.counts.missing}</b><small>Items need clarification</small></div></div>
      </div>

      <div className="an-grid">
        <div className="an-left">
          <section className="card an-card">
            <div className="an-card-head">
              <h2><span className="icon-tile tile-blue tile-sm"><FileText /></span> Plain-Language Summary</h2>
              <Link to={`/chat?q=${encodeURIComponent(`Explain the key risks in my ${doc.name}`)}`} className="btn btn-soft btn-sm"><MessageCircleMore size={17} /> Ask About This</Link>
            </div>
            <p className="an-summary" dir="auto">{a.summary}</p>
          </section>

          <section className="card an-card an-flush">
            <div className="an-card-head">
              <button className="an-toggle" onClick={() => setOpenClauses(o => !o)}><FileText size={20} /> Key Clauses <span>({a.clauses.length})</span></button>
              <div className="an-head-links">
                <button className="link small" onClick={() => { setAllClauses(v => !v); setOpenClauses(true) }}>{allClauses ? 'Show Less' : 'View All'}</button>
                <button className="icon-btn-plain" onClick={() => setOpenClauses(o => !o)} aria-label="Toggle">{openClauses ? <ChevronUp size={20} /> : <ChevronDown size={20} />}</button>
              </div>
            </div>
            {openClauses && (
              <div className="clauses">
                {clauses.map((c, i) => (
                  <div key={c.id} className={`clause ${expanded === i ? 'open' : ''}`}>
                    <button className="clause-row" onClick={() => setExpanded(expanded === i ? null : i)}>
                      <span className={`icon-tile tile-${RISK_TONE[c.risk] === 'green' ? 'blue' : RISK_TONE[c.risk]} tile-sm clause-ic`}><FileText /></span>
                      <b>{i + 1}. <bdi>{c.title}</bdi></b>
                      <span className="clause-no">{c.reference}</span>
                      <span className={`pill pill-${RISK_TONE[c.risk]}`}>{c.risk} Risk</span>
                      <span className="clause-d">{c.summary}</span>
                      <ChevronDown size={18} className="clause-chev" />
                    </button>
                    {expanded === i && (
                      <div className="clause-more">
                        <p dir="auto">{c.detail}</p>
                        {c.lawRefs?.length > 0 && (
                          <p className="clause-laws"><span>Related laws:</span>
                            {c.lawRefs.map(id => {
                              const l = (a.citations || []).find(x => x.id === id)
                              return l && <button key={id} type="button" className="law-chip" onClick={() => showLaw(id)}>{l.title.replace(/,\s*\d{4}$/, '')} · {l.reference.split(' - ')[0]}</button>
                            })}
                          </p>
                        )}
                        {c.quote && <blockquote className="clause-quote" dir="auto">“{c.quote}”{c.quoteVerified === false && <small>Closest text from your document; the exact wording could not be matched.</small>}</blockquote>}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card an-card an-flush">
            <div className="an-card-head">
              <button className="an-toggle" onClick={() => setOpenRisks(o => !o)}><ShieldCheck size={20} /> Potential Risks <span>({a.risks.length})</span></button>
              <div className="an-head-links">
                <button className="link small" onClick={() => { setAllRisks(v => !v); setOpenRisks(true) }}>{allRisks ? 'Show Less' : 'View All'}</button>
                <button className="icon-btn-plain" onClick={() => setOpenRisks(o => !o)} aria-label="Toggle">{openRisks ? <ChevronUp size={20} /> : <ChevronDown size={20} />}</button>
              </div>
            </div>
            {openRisks && (
              <div className="risks">
                {risks.map(r => (
                  <div key={r.id} className={`risk risk-${RISK_TONE[r.level]}`}>
                    <span className={`icon-tile tile-${RISK_TONE[r.level]} tile-sm`}><AlertTriangle /></span>
                    <div><b>{r.title}</b><span>{r.description}</span></div>
                    <span className={`pill pill-${RISK_TONE[r.level]}`}>{r.level} Risk</span>
                  </div>
                ))}
              </div>
            )}
            {SECTIONS.map(s => (
              <div key={s.key} className="an-collapse">
                <button className="an-collapse-head" onClick={() => setSections(p => ({ ...p, [s.key]: !p[s.key] }))}>
                  <s.icon size={20} /> <b>{s.title}</b> <span>({s.items.length})</span>
                  {sections[s.key] ? <ChevronUp size={20} className="an-collapse-chev" /> : <ChevronDown size={20} className="an-collapse-chev" />}
                </button>
                {sections[s.key] && <ul>{s.items.map(it => <li key={it}>{it}</li>)}</ul>}
              </div>
            ))}
          </section>
        </div>

        <div className="an-right">
          <section className="card an-card">
            <h3 className="an-side-title"><FileText size={19} /> Document Preview</h3>
            <div className="an-preview">
              {docLink
                ? <Link to={docLink} className="mini-page" aria-label="Open document"><Preview doc={doc} title={title} /></Link>
                : <div className="mini-page"><Preview doc={doc} title={title} /></div>}
              <div className="an-meta">
                <b>{doc.name}</b>
                <dl>
                  <dt>Type</dt><dd>{FILE_TYPE_LABEL[doc.fileType] || doc.fileType}</dd>
                  <dt>Size</dt><dd>{formatBytes(doc.sizeBytes)}</dd>
                  <dt>Pages</dt><dd>{doc.pages}</dd>
                  <dt>Uploaded</dt><dd>{formatDateTime(doc.uploadedAt)}</dd>
                </dl>
                {docLink && <Link to={docLink} className="btn btn-soft btn-block">View Document <ExternalLink size={16} /></Link>}
              </div>
            </div>
          </section>

          <section className="card an-card">
            <h3 className="an-side-title"><ShieldCheck size={19} /> Risk Distribution</h3>
            <div className="an-dist">
              <Donut size={120} stroke={22} gap={0} segments={[{ value: dist.high, color: '#e5322d' }, { value: dist.medium, color: '#f59e0b' }, { value: dist.low, color: '#22a45a' }]}>
                <div className="an-dist-c"><b>{totalIssues}</b><span>Total Issues</span></div>
              </Donut>
              <ul>
                <li><span className="dot" style={{ background: '#e5322d' }} />High Risk<b>{dist.high}</b></li>
                <li><span className="dot" style={{ background: '#f59e0b' }} />Medium Risk<b>{dist.medium}</b></li>
                <li><span className="dot" style={{ background: '#22a45a' }} />Low Risk<b>{dist.low}</b></li>
              </ul>
            </div>
          </section>

          {a.citations?.length > 0 && <section className="card an-card">
            <div className="an-card-head an-card-head-tight">
              <h3 className="an-side-title"><Landmark size={19} /> Related Laws</h3>
            </div>
            {a.citationsNote && <p className="laws-note">{a.citationsNote}</p>}
            <ul className="laws">
              {a.citations.map(l => {
                const open = openLaw === l.id
                return (
                  <li key={l.id} id={`law-${l.id}`} className={open ? 'open' : ''}>
                    <button type="button" className="law-row" aria-expanded={open} onClick={() => setOpenLaw(open ? null : l.id)}>
                      <span className="icon-tile tile-gray tile-sm"><Landmark /></span>
                      <span className="law-main"><b>{l.title}</b><span>{l.reference}</span></span>
                      {l.jurisdiction && <span className="pill pill-gray">{l.jurisdiction}</span>}
                      <ChevronDown size={16} className="law-chev" />
                    </button>
                    {open && (
                      <div className="law-more">
                        {l.topics?.length > 0 && <p className="law-topics">Relates to: {l.topics.join(', ')}</p>}
                        {l.quote && <blockquote>{l.quote}</blockquote>}
                        {l.note && <p className="source-flag"><AlertTriangle size={14} /> {l.note}</p>}
                        <p className="law-links">
                          {l.url && <a className="link small" href={l.url} target="_blank" rel="noreferrer">View full law <ExternalLink size={14} /></a>}
                          <Link className="link small" to={`/chat?q=${encodeURIComponent(`Explain ${l.reference.split(' - ')[0]} of the ${l.title} in simple words and how it relates to my ${doc.documentType || 'document'}`)}`}>Ask LegalMate about this <ArrowRight size={14} /></Link>
                        </p>
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          </section>}

          <section className="card an-card">
            <h3 className="an-side-title"><ListChecks size={19} /> Recommended Actions</h3>
            <ul className="rec-actions">
              {a.recommendedActions.map(x => <li key={x}><FileCheck2 size={16} />{x}<ChevronRight size={16} className="rec-chev" /></li>)}
            </ul>
            <button className="btn btn-orange btn-lg btn-block" onClick={() => navigate(`/case-briefs/new?fromAnalysis=${encodeURIComponent(a.id)}`)}><FileText size={19} /> Generate Case Brief</button>
          </section>
        </div>
      </div>
    </div>
  )
}
