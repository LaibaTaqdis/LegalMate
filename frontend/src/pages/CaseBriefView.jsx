import { useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  CheckCircle2, Copy, Download, FilePlus2, FileText, Folder, Link2, Lock, MessageCircleMore, MoreHorizontal,
  MoreVertical, Pencil, Printer, RefreshCw, Send, Share2, UserRoundSearch, Users, X, Loader2, Clock3
} from 'lucide-react'
import { Breadcrumb, Modal, Select, Toggle } from '../components/common'
import { FileIcon } from '../components/Icons'
import { useUI } from '../components/UIContext'
import { ErrorState, PageSkeleton, QueryBoundary } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { caseBriefService } from '../api/services/caseBriefService'
import { formatBytes, formatDate, formatDateTime } from '../utils/format'

const fileSlug = title => title.replace(/\s+/g, '_')
const initialsOf = v => v.replace(/[^a-zA-Z]/g, '').slice(0, 2).toUpperCase() || '#'

/** Renders the brief's content blocks: p | kv | ol | ul */
function Blocks({ blocks }) {
  return blocks.map((b, i) => {
    if (b.type === 'kv') return <p key={i}><b>{b.label}:</b> {b.text}</p>
    if (b.type === 'ol') return <ol key={i}>{b.items.map(x => <li key={x}>{x}</li>)}</ol>
    if (b.type === 'ul') return <ul key={i}>{b.items.map(x => <li key={x}>{x}</li>)}</ul>
    return <p key={i}>{b.text}</p>
  })
}

function ShareModal({ brief, open, onClose }) {
  const { toast } = useUI()
  const [tab, setTab] = useState('invite')
  const [recipient, setRecipient] = useState('')
  const [perm, setPerm] = useState('View')
  const [people, setPeople] = useState(brief.sharing?.invites || [])
  const [msg, setMsg] = useState('')
  const [sending, setSending] = useState(false)
  const [link, setLink] = useState(brief.sharing?.link || { enabled: false, url: '', expiresIn: '7 days', requirePassword: false })
  const [format, setFormat] = useState('pdf')
  const [exporting, setExporting] = useState(false)

  const add = () => {
    const v = recipient.trim()
    if (!v) return
    if (!/^\S+@\S+\.\S+$/.test(v) && !/^\+?\d[\d\s-]{8,}$/.test(v)) return toast('Enter a valid email address or phone number', 'info')
    if (people.some(p => p.contact === v)) return toast('Already added', 'info')
    setPeople([...people, { id: `new_${Date.now()}`, contact: v, permission: perm, isNew: true }])
    setRecipient('')
  }

  const send = async () => {
    if (!people.length) return toast('Add at least one recipient', 'info')
    setSending(true)
    try {
      await caseBriefService.invite(brief.id, { recipients: people.map(p => ({ contact: p.contact, permission: p.permission })), message: msg })
      onClose()
      toast(`Invitation sent to ${people.length} recipient${people.length > 1 ? 's' : ''}`)
    } catch (e) { toast(e.message, 'info') } finally { setSending(false) }
  }

  // Link settings are saved as soon as they change.
  const updateLink = async patch => {
    const prev = link
    setLink(l => ({ ...l, ...patch }))
    try { setLink(await caseBriefService.updateShareLink(brief.id, { ...prev, ...patch })) } catch (e) { setLink(prev); toast(e.message, 'info') }
  }

  const exportFile = async () => {
    setExporting(true)
    const name = `${fileSlug(brief.title)}.${format}`
    try { await caseBriefService.export(brief.id, format, name); onClose(); toast(`Downloading ${name}`) } catch (e) { toast(e.message, 'info') } finally { setExporting(false) }
  }

  return (
    <Modal open={open} onClose={onClose} className="share-modal">
      <div className="share-head">
        <div><h2>Share Case Brief</h2><p>Share securely with others or export a copy.</p></div>
        <button className="icon-btn-plain" onClick={onClose} aria-label="Close"><X size={24} /></button>
      </div>
      <div className="share-file">
        <FileIcon type="pdf" size={40} />
        <div><b>{brief.title}</b><span>Case Brief (AI Generated) • {brief.pages} pages • {formatBytes(brief.sizeBytes)}</span></div>
      </div>
      <div className="share-box">
        <div className="share-tabs">
          <button className={tab === 'invite' ? 'active' : ''} onClick={() => setTab('invite')}><Users size={19} /> Invite People</button>
          <button className={tab === 'link' ? 'active' : ''} onClick={() => setTab('link')}><Link2 size={19} /> Secure Link</button>
          <button className={tab === 'export' ? 'active' : ''} onClick={() => setTab('export')}><FileText size={19} /> Export</button>
        </div>
        <div className="share-body">
          {tab === 'invite' && (
            <>
              <h3>Invite People</h3>
              <p className="share-sub">Share this case brief with specific people via email or phone.</p>
              <p className="share-label">Recipients</p>
              <div className="share-add">
                <input className="input" value={recipient} onChange={e => setRecipient(e.target.value)} onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), add())} placeholder="Enter email address or phone number..." />
                <Select value={perm} onChange={setPerm} options={['View', 'Comment', 'Edit']} className="share-perm" />
                <button className="btn share-add-btn" onClick={add}>Add</button>
              </div>
              <div className="share-people">
                {people.map(p => (
                  <span key={p.id} className="share-person">
                    <span className="share-init">{initialsOf(p.contact)}</span>{p.contact}
                    <button className="share-p-perm" onClick={() => setPeople(people.map(x => (x.id === p.id ? { ...x, permission: x.permission === 'View' ? 'Edit' : 'View' } : x)))}>{p.permission}</button>
                    <button onClick={() => setPeople(people.filter(x => x.id !== p.id))} aria-label={`Remove ${p.contact}`}><X size={16} /></button>
                  </span>
                ))}
              </div>
              <p className="share-label">Optional Message</p>
              <div className="cb-ta share-msg"><textarea className="textarea" rows={3} maxLength={500} value={msg} onChange={e => setMsg(e.target.value)} placeholder="Add a message (optional)..." /><span>{msg.length}/500</span></div>
              <div className="share-info"><Users size={22} /> Recipients will receive an email with a secure link to access this case brief.</div>
              <div className="share-actions">
                <button className="btn btn-outline btn-lg" onClick={onClose}>Cancel</button>
                <button className="btn btn-orange btn-lg" onClick={send} disabled={sending}>{sending ? <Loader2 size={19} className="spin" /> : <Send size={19} />} Send Invitation</button>
              </div>
            </>
          )}
          {tab === 'link' && (
            <>
              <h3>Secure Link</h3>
              <p className="share-sub">Anyone with this link can view the brief. You can disable it at any time.</p>
              <div className="share-row"><span><b>Link sharing</b><small>{link.enabled ? 'Anyone with the link can view' : 'Link is disabled'}</small></span><Toggle checked={link.enabled} onChange={v => updateLink({ enabled: v })} label="Link sharing" /></div>
              <div className={`share-link ${link.enabled ? '' : 'disabled'}`}>
                <Link2 size={18} /><input className="input" readOnly value={link.url || ''} />
                <button className="btn btn-navy" disabled={!link.enabled || !link.url} onClick={() => { navigator.clipboard?.writeText(link.url); toast('Secure link copied') }}><Copy size={17} /> Copy</button>
              </div>
              <div className="share-row"><span><b>Link expires in</b><small>After this the link stops working</small></span><Select value={link.expiresIn} onChange={v => updateLink({ expiresIn: v })} options={['24 hours', '7 days', '30 days', 'Never']} className="share-expiry" /></div>
              <div className="share-row"><span><b>Require password</b><small>Recipients must enter a password to open</small></span><Toggle checked={link.requirePassword} onChange={v => updateLink({ requirePassword: v })} label="Require password" /></div>
              <div className="share-actions"><button className="btn btn-outline btn-lg" onClick={onClose}>Done</button></div>
            </>
          )}
          {tab === 'export' && (
            <>
              <h3>Export</h3>
              <p className="share-sub">Download a copy of this case brief.</p>
              <div className="share-formats">
                {[{ v: 'pdf', t: 'PDF Document', d: 'Best for printing and sharing', type: 'pdf' }, { v: 'docx', t: 'Word Document', d: 'Editable DOCX file', type: 'docx' }].map(o => (
                  <button key={o.v} className={`depth ${format === o.v ? 'active' : ''}`} onClick={() => setFormat(o.v)}>
                    <FileIcon type={o.type} size={34} /><div><b>{o.t}</b><span>{o.d}</span></div>
                  </button>
                ))}
              </div>
              <div className="share-actions">
                <button className="btn btn-outline btn-lg" onClick={onClose}>Cancel</button>
                <button className="btn btn-orange btn-lg" onClick={exportFile} disabled={exporting}>{exporting ? <Loader2 size={19} className="spin" /> : <Download size={19} />} Export {format.toUpperCase()}</button>
              </div>
            </>
          )}
          <div className="share-conf"><Lock size={26} /><div><b>Keep it confidential</b><span>Only share confidential legal information with trusted recipients.</span></div></div>
        </div>
      </div>
    </Modal>
  )
}

export default function CaseBriefView() {
  const { id } = useParams()
  const query = useQuery(signal => caseBriefService.get(id, signal), [id], { pollInterval: 3000, shouldPoll: b => b?.status === 'generating' })
  return (
    <QueryBoundary query={query} skeleton={<PageSkeleton cards={2} rows={1} />}>
      {brief => {
        if (brief.status === 'failed') return <ErrorState error={{ message: 'The brief could not be generated. Please edit the details and try again.' }} />
        if (brief.status === 'generating') {
          return <div className="card state-box"><Loader2 size={32} className="spin" /><b>Generating your case brief…</b><p>This usually takes less than a minute.</p></div>
        }
        return <BriefView brief={brief} setBrief={query.setData} />
      }}
    </QueryBoundary>
  )
}

function BriefView({ brief, setBrief }) {
  const navigate = useNavigate()
  const { toast } = useUI()
  const [params, setParams] = useSearchParams()
  const [busy, setBusy] = useState(null)
  const shareOpen = params.get('share') === '1'
  const setShare = v => setParams(v ? { share: '1' } : {}, { replace: true })
  const hearingIn = brief.nextHearing ? Math.ceil((new Date(`${brief.nextHearing.date}T00:00:00`) - new Date()) / 86400000) : null

  const run = async (key, fn, success) => {
    setBusy(key)
    try { await fn(); if (success) toast(success) } catch (e) { toast(e.message, 'info') } finally { setBusy(null) }
  }
  const regenerate = () => run('regen', async () => setBrief(await caseBriefService.regenerate(brief.id)), 'Brief regenerated')
  const downloadPdf = () => run('download', () => caseBriefService.export(brief.id, 'pdf', `${fileSlug(brief.title)}.pdf`), `Downloading ${fileSlug(brief.title)}.pdf`)

  return (
    <div className="cbv">
      <div className="page-head cbv-head">
        <div>
          <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Case Briefs', to: '/case-briefs' }, { label: brief.title }]} />
          <h1 className="page-title cbv-title">{brief.title} <span className="pill pill-green cbv-gen"><CheckCircle2 size={15} fill="#22a45a" color="#fff" /> Generated</span></h1>
          <p className="page-sub cbv-sub">{brief.caseNumber} <i>•</i> {brief.court}</p>
        </div>
        <div className="cbv-actions">
          <button className="btn btn-outline btn-lg" onClick={() => navigate('/case-briefs/new')}><Pencil size={18} /> Edit</button>
          <button className="btn btn-outline btn-lg" onClick={regenerate} disabled={busy === 'regen'}>
            <RefreshCw size={18} className={busy === 'regen' ? 'spin' : ''} /> Regenerate
          </button>
          <button className="btn btn-outline btn-lg" onClick={downloadPdf} disabled={busy === 'download'}><Download size={18} /> Download</button>
          <button className="btn btn-outline btn-lg" onClick={() => setShare(true)}><Share2 size={18} /> Share</button>
          <button className="icon-btn cbv-more" aria-label="More" onClick={() => toast('More options coming soon', 'info')}><MoreHorizontal size={19} /></button>
        </div>
      </div>

      <div className="cbv-grid">
        <article className={`card cbv-doc ${busy === 'regen' ? 'is-refreshing' : ''}`}>
          {brief.sections.map(s => (
            <section key={s.number} className="cbv-sec">
              <h2><span>{s.number}</span> {s.title}</h2>
              <div className="cbv-body"><Blocks blocks={s.blocks} /></div>
            </section>
          ))}
        </article>
        <aside className="cbv-side">
          <section className="card card-pad">
            <h3 className="cbv-h3"><FileText size={20} /> Document Information</h3>
            <dl className="dv-dl cbv-dl">
              <dt>Type</dt><dd>Case Brief (AI Generated)</dd>
              <dt>Created</dt><dd>{formatDateTime(brief.createdAt)}</dd>
              <dt>Last Modified</dt><dd>{formatDateTime(brief.updatedAt)}</dd>
              <dt>Pages</dt><dd>{brief.pages}</dd>
              <dt>Size</dt><dd>{formatBytes(brief.sizeBytes)}</dd>
            </dl>
          </section>
          <section className="card card-pad">
            <h3 className="cbv-h3"><FileText size={20} /> Related Documents</h3>
            <ul className="cbv-related">
              {brief.relatedDocuments.map(r => (
                <li key={r.id + r.name} onClick={() => navigate(`/vault/document/${r.id}`)}>
                  <FileIcon type={r.fileType} size={32} /><div><b>{r.name}</b><span>{formatBytes(r.sizeBytes)}</span></div>
                  <button className="icon-btn-plain" onClick={e => { e.stopPropagation(); toast(`Options for ${r.name}`, 'info') }} aria-label="Options"><MoreVertical size={18} /></button>
                </li>
              ))}
            </ul>
          </section>
          <section className="card card-pad">
            <h3 className="cbv-h3"><Users size={20} /> Quick Actions</h3>
            <div className="cbv-qa">
              <button onClick={() => navigate(`/chat?q=${encodeURIComponent(`Help me understand my case: ${brief.title} (${brief.caseNumber})`)}`)}><MessageCircleMore size={19} /> Ask LegalMate about this case</button>
              <button onClick={() => navigate('/case-briefs/new')}><FilePlus2 size={19} /> Create new brief from this case</button>
              <button onClick={() => navigate('/legal-aid')}><UserRoundSearch size={19} /> Find a lawyer</button>
              <button onClick={() => run('vault', () => caseBriefService.saveToVault(brief.id), 'Added to Legal Vault')}><Folder size={19} /> Add to Legal Vault</button>
              <button onClick={() => window.print()}><Printer size={19} /> Print document</button>
            </div>
          </section>
          {brief.nextHearing && hearingIn >= 0 && (
            <section className="card card-pad cbv-hearing">
              <Clock3 size={20} /><div><b>Next hearing in {hearingIn} days</b><span>{formatDate(brief.nextHearing.date)} · {brief.nextHearing.court}</span></div>
            </section>
          )}
        </aside>
      </div>

      {shareOpen && <ShareModal brief={brief} open={shareOpen} onClose={() => setShare(false)} />}
    </div>
  )
}
