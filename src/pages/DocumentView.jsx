import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, ChevronLeft, ChevronRight, Copy, Download, Folder, FolderInput, Highlighter,
  Loader2, MessageCircleMore, Minus, MoreHorizontal, Pencil, Plus, RotateCw, Scale, Search, Share2, ShieldCheck,
  Star, StickyNote, Trash2, X, CheckCircle2, Sparkles, Eye, Clock3
} from 'lucide-react'
import { Breadcrumb, Modal, Select } from '../components/common'
import { FileIcon } from '../components/Icons'
import { useUI } from '../components/UIContext'
import { PageSkeleton, QueryBoundary, Skeleton } from '../components/States'
import { useAuth } from '../context/AuthContext'
import { useQuery } from '../hooks/useApi'
import { vaultService } from '../api/services/vaultService'
import { documentService } from '../api/services/documentService'
import { formatBytes, formatDateTime } from '../utils/format'

const stripExt = name => name.replace(/\.[a-z]+$/i, '')
const ACTIVITY_ICONS = { analysed: Sparkles, verified: ShieldCheck, viewed: Eye, uploaded: Clock3 }

/* ---------- Demo page renderers used when the API does not return page HTML (mock mode) ---------- */
function TitlePage({ doc, ownerName }) {
  return (
    <>
      <h2 className="doc-h">{stripExt(doc.name).toUpperCase()}</h2>
      <p>This document was uploaded to your Legal Vault on <b>22 September 2026</b> and is stored in the <b>{doc.folderName}</b> folder.</p>
      <ol className="doc-list">
        <li><b>Summary</b><p>This {doc.category.toLowerCase()} record has been verified and encrypted. Use “Ask LegalMate” to get a plain-language explanation of its contents, obligations and any deadlines.</p></li>
        <li><b>Parties</b><p>Mr. {ownerName}, resident of Islamabad, Pakistan, and the relevant counter-party named in the original document.</p></li>
        <li><b>Key Terms</b><p>The full text of the original document follows on the next pages. Highlighted sections indicate clauses that may need your attention.</p></li>
      </ol>
    </>
  )
}

function TenancyPageOne() {
  return (
    <>
      <h2 className="doc-h">TENANCY AGREEMENT</h2>
      <p>This Tenancy Agreement ("Agreement") is made on this <b>1st day of June 2026</b>, between:</p>
      <p className="doc-party"><b>Landlord:</b><span>Mr. Ali Khan, s/o Muhammad Khan, resident of Islamabad, Pakistan</span></p>
      <p className="doc-party"><b>Tenant:</b><span>Mr. Arfah Raza, s/o Kareem Raza, resident of Rawalpindi, Pakistan</span></p>
      <ol className="doc-list">
        <li><b>Property Details</b>
          <p>The landlord agrees to rent out the residential property located at <mark><b>House No. 123, Street 5, Sector F-10, Islamabad</b> ("the Premises")</mark> to the tenant for residential purposes only.</p></li>
        <li><b>Tenancy Term</b>
          <p><mark>The tenancy shall commence on <b>1st June 2026</b> and shall continue for a period of 12 months, ending on <b>31st May 2027,</b> unless terminated earlier in accordance with the terms of this Agreement.</mark></p></li>
        <li><b>Rent and Payment</b>
          <p>The monthly rent shall be PKR 45,000 (Rupees Forty Five Thousand only), payable on or before the <b>5th day</b> of each month through bank transfer or cash. A security deposit of PKR 90,000 (Rupees Ninety Thousand only) shall be paid at the time of signing this Agreement, refundable subject to the terms herein.</p></li>
        <li><b>Maintenance</b>
          <p>The tenant shall be responsible for routine maintenance and utility bills including electricity, gas and water. Major structural repairs shall be the responsibility of the landlord.</p></li>
        <li><b>Termination</b>
          <p><mark>Either party may terminate this Agreement by giving 30 days' written notice to the other party.</mark></p></li>
      </ol>
      <p className="doc-witness">IN WITNESS WHEREOF, the parties have signed this Agreement on the date first above written.</p>
      <div className="doc-sign"><span>Landlord</span><span>Tenant</span></div>
    </>
  )
}

function GenericPage({ n, total, title }) {
  const titles = ['Use of Premises', 'Subletting', 'Utilities', 'Inspection', 'Alterations', 'Insurance', 'Dispute Resolution', 'Governing Law', 'Notices', 'Entire Agreement', 'Schedule of Fixtures']
  return (
    <>
      <p className="doc-page-head">{title} - Page {n} of {total}</p>
      <ol className="doc-list" start={4 + n}>
        {[0, 1].map(k => (
          <li key={k}><b>{titles[(n * 2 + k) % titles.length]}</b>
            <p>The tenant shall comply with all applicable laws, bye-laws and regulations in respect of the Premises and shall not use the Premises for any unlawful, commercial or immoral purpose. Any breach of this clause shall entitle the landlord to issue written notice requiring the breach to be remedied within fifteen (15) days.</p>
            <p>Nothing in this clause shall be construed as limiting the rights of either party under the Rent Act, 2009 or any other law for the time being in force in the Islamabad Capital Territory.</p>
          </li>
        ))}
      </ol>
    </>
  )
}

export default function DocumentView() {
  const { id } = useParams()
  const query = useQuery(signal => vaultService.getDocument(id, signal), [id])
  return (
    <QueryBoundary query={query} skeleton={<PageSkeleton cards={3} rows={1} />}>
      {doc => <Viewer key={doc.id} doc={doc} setDoc={query.setData} />}
    </QueryBoundary>
  )
}

function Viewer({ doc, setDoc }) {
  const navigate = useNavigate()
  const { toast } = useUI()
  const { user } = useAuth()
  const [page, setPage] = useState(1)
  const [zoom, setZoom] = useState(100)
  const [rotate, setRotate] = useState(0)
  const [tab, setTab] = useState('Details')
  const [tagDraft, setTagDraft] = useState(null)
  const [toolbar, setToolbar] = useState(true)
  const [noteDraft, setNoteDraft] = useState('')
  const [dialog, setDialog] = useState(null) // 'delete' | 'rename' | 'move'
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(null)
  const [find, setFind] = useState('')
  const viewerRef = useRef(null)
  const pageRefs = useRef({})

  const content = useQuery(signal => vaultService.getContent(doc.id, signal), [doc.id])
  const notes = useQuery(signal => vaultService.listNotes(doc.id, signal), [doc.id])
  const activity = useQuery(signal => vaultService.listActivity(doc.id, signal), [doc.id], { enabled: tab === 'Activity' })
  const analysis = useQuery(signal => documentService.getAnalysis(doc.analysisId, signal), [doc.analysisId], { enabled: tab === 'Analysis' && !!doc.analysisId })
  const folders = useQuery(signal => vaultService.listFolders(signal), [], { enabled: dialog === 'move' })

  const total = content.data?.pageCount || doc.pages || 1
  const isTenancy = doc.id === 'tenancy'
  const title = stripExt(doc.name)

  const go = n => {
    const p = Math.min(total, Math.max(1, n))
    setPage(p)
    pageRefs.current[p]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  useEffect(() => {
    const el = viewerRef.current
    if (!el) return undefined
    const onScroll = () => {
      const top = el.scrollTop + 120
      let current = 1
      for (let i = 1; i <= total; i++) if (pageRefs.current[i] && pageRefs.current[i].offsetTop <= top) current = i
      setPage(current)
    }
    el.addEventListener('scroll', onScroll)
    return () => el.removeEventListener('scroll', onScroll)
  }, [total])

  /** Runs an update against the API and merges the returned document. */
  const update = async (key, patch, success) => {
    setBusy(key)
    try {
      const updated = await vaultService.updateDocument(doc.id, patch)
      setDoc(d => ({ ...d, ...updated }))
      if (success) toast(success)
      return true
    } catch (e) { toast(e.message, 'info'); return false } finally { setBusy(null) }
  }

  const addTag = () => {
    const v = tagDraft?.trim()
    setTagDraft(null)
    if (v && !doc.tags.includes(v)) update('tags', { tags: [...doc.tags, v] })
  }
  const removeTag = t => update('tags', { tags: doc.tags.filter(x => x !== t) })

  const toggleFav = async () => {
    const next = !doc.favourite
    setDoc(d => ({ ...d, favourite: next }))
    try { await vaultService.setFavourite(doc.id, next); toast(next ? 'Added to Favourites' : 'Removed from Favourites') } catch (e) { setDoc(d => ({ ...d, favourite: !next })); toast(e.message, 'info') }
  }

  const downloadDoc = async () => {
    try { await vaultService.downloadDocument(doc.id, doc.name); toast(`Downloading ${doc.name}`) } catch (e) { toast(e.message, 'info') }
  }
  const share = () => { navigator.clipboard?.writeText(window.location.href); toast('Share link copied') }
  const copyDoc = async () => {
    setBusy('copy')
    try { const c = await vaultService.copyDocument(doc.id); toast(`Copy created: ${c.name}`) } catch (e) { toast(e.message, 'info') } finally { setBusy(null) }
  }
  const remove = async () => {
    setBusy('delete')
    try { await vaultService.deleteDocument(doc.id); toast('Moved to Trash'); navigate('/vault') } catch (e) { toast(e.message, 'info'); setBusy(null) }
  }
  const addNote = async () => {
    const text = noteDraft.trim()
    if (!text) return
    setBusy('note')
    try {
      const n = await vaultService.addNote(doc.id, text)
      notes.setData(x => ({ ...x, items: [n, ...(x?.items || [])] }))
      setNoteDraft('')
    } catch (e) { toast(e.message, 'info') } finally { setBusy(null) }
  }
  const askLegalMate = () => navigate(`/chat?q=${encodeURIComponent(`Explain my document "${doc.name}" in simple terms`)}`)

  const renderPage = i => {
    const apiPage = content.data?.pages?.[i]
    if (apiPage?.html) return <div dangerouslySetInnerHTML={{ __html: apiPage.html }} />
    if (i === 0) return isTenancy ? <TenancyPageOne /> : <TitlePage doc={doc} ownerName={user?.name} />
    return <GenericPage n={i + 1} total={total} title={title} />
  }

  return (
    <div className="docview">
      <Breadcrumb items={[{ label: 'Legal Vault', to: '/vault' }, { label: doc.folderName || 'Documents', to: '/vault' }, { label: title }]} />
      <div className="dv-toolbar">
        <button className="btn btn-outline dv-back" onClick={() => navigate(-1)}><ArrowLeft size={18} /> Back</button>
        <div className="dv-seg dv-file">
          <FileIcon type={doc.fileType} size={24} />
          <b>{doc.name}</b>
          {doc.verified && <span className="pill pill-green"><CheckCircle2 size={14} fill="#22a45a" color="#fff" /> Verified</span>}
        </div>
        <div className="dv-seg dv-pager">
          <button className="icon-btn" onClick={() => go(page - 1)} disabled={page === 1} aria-label="Previous page"><ChevronLeft size={17} /></button>
          <span><input value={page} onChange={e => go(Number(e.target.value) || 1)} aria-label="Page number" /> / {total}</span>
          <button className="icon-btn" onClick={() => go(page + 1)} disabled={page === total} aria-label="Next page"><ChevronRight size={17} /></button>
        </div>
        <div className="dv-seg dv-zoom">
          <button className="icon-btn-plain" onClick={() => setZoom(z => Math.max(50, z - 10))} aria-label="Zoom out"><Minus size={17} /></button>
          <span>{zoom}%</span>
          <button className="icon-btn-plain" onClick={() => setZoom(z => Math.min(200, z + 10))} aria-label="Zoom in"><Plus size={17} /></button>
        </div>
        <button className="icon-btn dv-rotate" onClick={() => setRotate(r => (r + 90) % 360)} aria-label="Rotate"><RotateCw size={17} /></button>
        <label className="dv-find"><Search size={17} /><input value={find} onChange={e => setFind(e.target.value)} placeholder="Search in document..." /></label>
        <div className="dv-seg dv-icons">
          <button className="icon-btn-plain" onClick={downloadDoc} aria-label="Download"><Download size={19} /></button>
          <button className="icon-btn-plain" onClick={share} aria-label="Share"><Share2 size={19} /></button>
          <button className="icon-btn-plain" onClick={() => toast('More options coming soon', 'info')} aria-label="More"><MoreHorizontal size={19} /></button>
        </div>
      </div>

      <div className="dv-grid">
        <aside className="card dv-thumbs">
          <p className="dv-thumbs-title">Pages</p>
          <div className="dv-thumbs-scroll">
            {Array.from({ length: total }).map((_, i) => (
              <button key={i} className={`dv-thumb ${page === i + 1 ? 'active' : ''}`} onClick={() => go(i + 1)}>
                <span className="mini-page mini-thumb">{i === 0 && <b>{title.toUpperCase()}</b>}{Array.from({ length: 14 }).map((_, k) => <i key={k} style={{ width: `${55 + ((k * 29 + i * 7) % 45)}%` }} />)}</span>
                <span className="dv-thumb-n">{i + 1}</span>
              </button>
            ))}
          </div>
        </aside>

        <section className="dv-viewer" ref={viewerRef}>
          {content.loading && !content.data && <Skeleton h={900} w={700} r={2} />}
          {content.data?.fileUrl && !content.data?.pages && ['jpg', 'png'].includes(doc.fileType) && <img src={content.data.fileUrl} alt={doc.name} className="doc-image" />}
          {content.data && Array.from({ length: total }).map((_, i) => (
            <div key={i} ref={el => (pageRefs.current[i + 1] = el)} className="doc-page-wrap" style={{ zoom: zoom / 100 }}>
              <article className={`doc-page ${find ? 'searching' : ''}`} style={{ transform: `rotate(${rotate}deg)` }}>
                {renderPage(i)}
                {i === 0 && isTenancy && toolbar && (
                  <div className="doc-float">
                    <button onClick={askLegalMate}><Scale size={16} /> Ask LegalMate</button>
                    <button onClick={() => { setTab('Notes'); toast('Add your note in the Notes tab', 'info') }}><StickyNote size={16} /> Add Note</button>
                    <button onClick={() => toast('Text highlighted')}><Highlighter size={16} /> Highlight</button>
                    <button onClick={() => setToolbar(false)} aria-label="Hide toolbar"><MoreHorizontal size={16} /></button>
                  </div>
                )}
              </article>
            </div>
          ))}
        </section>

        <aside className="dv-side">
          <div className="dv-tabs">
            {['Details', 'Analysis', `Notes (${notes.data?.items.length ?? 0})`, 'Activity'].map(t => {
              const key = t.split(' ')[0]
              return <button key={t} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{t}</button>
            })}
          </div>
          <div className="dv-side-scroll">
            {tab === 'Details' && (
              <>
                <section className="card dv-box">
                  <div className="dv-file-head">
                    <FileIcon type={doc.fileType} size={34} />
                    <div><b>{doc.name}</b><span className="pill pill-blue">{doc.category}</span></div>
                    <button className={`icon-btn-plain dv-star ${doc.favourite ? 'on' : ''}`} onClick={toggleFav} aria-label="Favourite"><Star size={22} /></button>
                  </div>
                  <dl className="dv-dl">
                    <dt>Size</dt><dd>{formatBytes(doc.sizeBytes)}</dd>
                    <dt>Pages</dt><dd>{doc.pages}</dd>
                    <dt>Uploaded</dt><dd>{formatDateTime(doc.uploadedAt)}</dd>
                    <dt>Last modified</dt><dd>{formatDateTime(doc.updatedAt)}</dd>
                    <dt>Location</dt><dd><Folder size={16} /> {doc.folderName}</dd>
                    <dt>Owner</dt><dd>{doc.owner || 'You'}</dd>
                  </dl>
                </section>
                <section className="card dv-box">
                  <div className="card-head"><h4>Tags</h4><button className="link small" onClick={() => setTagDraft('')}><Plus size={15} /> Add tag</button></div>
                  <div className="dv-tags">
                    {doc.tags.map(t => <span key={t} className="dv-tag">{t}<button onClick={() => removeTag(t)} aria-label={`Remove ${t}`}><X size={13} /></button></span>)}
                    {tagDraft !== null && <input autoFocus className="dv-tag-input" value={tagDraft} onChange={e => setTagDraft(e.target.value)} onBlur={addTag} onKeyDown={e => e.key === 'Enter' && addTag()} placeholder="New tag" />}
                  </div>
                </section>
                <section className="card dv-box">
                  <h4>Quick Actions</h4>
                  <div className="dv-qa">
                    <button onClick={downloadDoc}><Download size={16} /> Download</button>
                    <button onClick={share}><Share2 size={16} /> Share</button>
                    <button onClick={() => { setDraft(doc.folderId); setDialog('move') }}><FolderInput size={16} /> Move</button>
                    <button onClick={() => { setDraft(stripExt(doc.name)); setDialog('rename') }}><Pencil size={16} /> Rename</button>
                    <button onClick={copyDoc} disabled={busy === 'copy'}>{busy === 'copy' ? <Loader2 size={16} className="spin" /> : <Copy size={16} />} Make a Copy</button>
                    <button className="danger" onClick={() => setDialog('delete')}><Trash2 size={16} /> Delete</button>
                  </div>
                </section>
                <section className="card dv-box">
                  <h4>Security</h4>
                  <div className="dv-sec">
                    <ShieldCheck size={32} fill="#22a45a" color="#fff" />
                    <div><b>Encrypted storage</b><span>Your file is stored securely.</span></div>
                    <span className="pill pill-green"><CheckCircle2 size={14} /> Secure</span>
                  </div>
                </section>
              </>
            )}
            {tab === 'Analysis' && (
              <section className="card dv-box">
                <h4>Analysis summary</h4>
                {!doc.analysisId && <p className="muted small" style={{ marginBottom: 12 }}>This document has not been analysed yet.</p>}
                {analysis.loading && <Skeleton h={90} />}
                {analysis.data && (
                  <ul className="dv-analysis">
                    <li><span className="pill pill-orange">{analysis.data.overallRisk.level}</span> Overall risk</li>
                    <li><b>{analysis.data.counts.clauses}</b> key clauses identified</li>
                    <li><b>{analysis.data.counts.deadlines}</b> important deadlines</li>
                    <li><b>{analysis.data.counts.missing}</b> items need clarification</li>
                  </ul>
                )}
                {doc.analysisId
                  ? <Link to={`/documents/analysis/${doc.analysisId}`} className="btn btn-soft btn-block">Open full analysis <ArrowRight size={16} /></Link>
                  : <Link to="/documents/upload" className="btn btn-soft btn-block">Analyse this document <ArrowRight size={16} /></Link>}
              </section>
            )}
            {tab === 'Notes' && (
              <section className="card dv-box">
                <h4>Notes</h4>
                <div className="dv-note-add">
                  <textarea className="textarea" rows={3} value={noteDraft} onChange={e => setNoteDraft(e.target.value)} placeholder="Write a note about this document..." />
                  <button className="btn btn-navy btn-sm" onClick={addNote} disabled={busy === 'note'}>{busy === 'note' && <Loader2 size={14} className="spin" />} Add Note</button>
                </div>
                {notes.loading && !notes.data && <Skeleton h={60} />}
                <ul className="dv-notes">{notes.data?.items.map(n => <li key={n.id}><StickyNote size={15} /><div><p>{n.text}</p><span>{formatDateTime(n.createdAt)}</span></div></li>)}</ul>
              </section>
            )}
            {tab === 'Activity' && (
              <section className="card dv-box">
                <h4>Activity</h4>
                {activity.loading && !activity.data && <Skeleton h={120} />}
                <ul className="dv-activity">
                  {activity.data?.items.map(a => {
                    const Icon = ACTIVITY_ICONS[a.type] || Clock3
                    return <li key={a.id}><Icon size={15} /><div><p>{a.text}</p><span>{formatDateTime(a.createdAt)}</span></div></li>
                  })}
                </ul>
              </section>
            )}
            <section className="card dv-box dv-ask">
              <div className="dv-ask-head"><MessageCircleMore size={22} /><div><b>Ask about this document</b><span>Have a question about this document? Open it in Legal Chat with full context.</span></div></div>
              <button className="btn btn-orange btn-lg btn-block" onClick={askLegalMate}><Scale size={19} /> Ask LegalMate <ArrowRight size={19} className="dv-ask-arrow" /></button>
            </section>
          </div>
        </aside>
      </div>

      <Modal open={dialog === 'delete'} onClose={() => setDialog(null)} className="modal-sm">
        <div className="confirm">
          <span className="icon-tile tile-red tile-lg"><Trash2 /></span>
          <h3>Move to Trash?</h3>
          <p>“{doc.name}” will be moved to Trash. You can restore it within 30 days.</p>
          <div className="confirm-actions">
            <button className="btn btn-outline" onClick={() => setDialog(null)}>Cancel</button>
            <button className="btn btn-danger-soft" onClick={remove} disabled={busy === 'delete'}>{busy === 'delete' && <Loader2 size={16} className="spin" />} Move to Trash</button>
          </div>
        </div>
      </Modal>

      <Modal open={dialog === 'rename'} onClose={() => setDialog(null)} className="modal-sm">
        <form className="confirm" onSubmit={async e => {
          e.preventDefault()
          const ext = doc.name.match(/\.[a-z]+$/i)?.[0] || ''
          if (draft.trim() && await update('rename', { name: `${draft.trim()}${ext}` }, 'Document renamed')) setDialog(null)
        }}>
          <span className="icon-tile tile-blue tile-lg"><Pencil /></span>
          <h3>Rename document</h3>
          <input autoFocus className="input" value={draft} onChange={e => setDraft(e.target.value)} />
          <div className="confirm-actions">
            <button type="button" className="btn btn-outline" onClick={() => setDialog(null)}>Cancel</button>
            <button className="btn btn-orange" disabled={busy === 'rename'}>{busy === 'rename' && <Loader2 size={16} className="spin" />} Rename</button>
          </div>
        </form>
      </Modal>

      <Modal open={dialog === 'move'} onClose={() => setDialog(null)} className="modal-sm">
        <form className="confirm" onSubmit={async e => {
          e.preventDefault()
          const f = folders.data?.items.find(x => x.id === draft)
          if (f && await update('move', { folderId: f.id }, `Moved to ${f.name}`)) { setDoc(d => ({ ...d, folderName: f.name })); setDialog(null) }
        }}>
          <span className="icon-tile tile-blue tile-lg"><FolderInput /></span>
          <h3>Move to folder</h3>
          <div style={{ width: '100%' }}>
            <Select value={draft} onChange={setDraft} placeholder={folders.loading ? 'Loading folders…' : 'Choose a folder'}
              options={(folders.data?.items || []).map(f => ({ value: f.id, label: f.name }))} />
          </div>
          <div className="confirm-actions">
            <button type="button" className="btn btn-outline" onClick={() => setDialog(null)}>Cancel</button>
            <button className="btn btn-orange" disabled={busy === 'move'}>{busy === 'move' && <Loader2 size={16} className="spin" />} Move</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
