import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle, ListChecks, FileText, Loader2, MessageCircleMore, Pencil, RotateCcw, Star, Trash2 } from 'lucide-react'
import { Breadcrumb, Modal } from '../components/common'
import { VaultActivity, VaultNotes } from '../components/VaultParts'
import { useUI } from '../components/UIContext'
import { QueryBoundary, PageSkeleton } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { vaultService } from '../api/services/vaultService'
import { answerText } from '../utils/answerText'
import { formatDateTime } from '../utils/format'
import { AnalysisResult } from './Analysis'

const KIND_LABEL = { answer: 'Chat answer', analysis: 'Analysis', brief: 'Case brief' }

/** The model's rich text ([text, {b}, {cite}]) with citation chips that jump to the source below. */
function Segs({ parts, onCite }) {
  if (typeof parts === 'string') return parts
  return (parts || []).map((p, i) => {
    if (typeof p === 'string') return <span key={i}>{p}</span>
    if (p.b) return <b key={i}>{p.b}</b>
    if (p.cite) return <button key={i} type="button" className="vi-cite" onClick={() => onCite(p.cite)}>{p.cite}</button>
    return null
  })
}

function SavedAnswer({ content }) {
  const a = content.answer || {}
  const T = answerText(a.language)
  const [flash, setFlash] = useState(null)
  const cite = n => {
    setFlash(n)
    document.getElementById(`vsrc-${n}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    setTimeout(() => setFlash(null), 1600)
  }
  const dir = a.language === 'ur' ? 'rtl' : 'ltr'
  return (
    <>
      {content.question && <section className="card vi-q"><small>Your question</small><p dir="auto">{content.question}</p></section>}
      <section className="card vi-answer-card answer" dir={dir}>
        <p><Segs parts={a.intro} onCite={cite} /></p>
        {a.law?.length > 0 && <><h4><FileText size={19} /> {a.lawTitle}</h4><p><Segs parts={a.law} onCite={cite} /></p></>}
        {a.steps?.length > 0 && (
          <>
            <h4><ListChecks size={19} /> {T.steps}</h4>
            <ol className="answer-steps">{a.steps.map((s, i) => <li key={i}><span>{i + 1}</span><p><Segs parts={s} onCite={cite} /></p></li>)}</ol>
          </>
        )}
        {a.important && <div className="answer-important"><AlertTriangle size={22} /><div><b>{T.important}</b><p>{a.important}</p></div></div>}
        {a.outro && <p>{a.outro}</p>}
        {a.disclaimer && <p className="muted small">{a.disclaimer}</p>}
      </section>
      {a.sources?.length > 0 && (
        <section className="card vi-sources">
          <h3>{T.sources} ({a.sources.length})</h3>
          {a.sources.map(s => (
            <div key={s.id} id={`vsrc-${s.id}`} className={`vi-source ${flash === s.id ? 'flash' : ''}`}>
              <b>{s.id}</b>
              <div>
                <strong>{s.title}</strong>
                <span>{[s.section, s.pages, s.jurisdiction].filter(Boolean).join(' · ')}</span>
                {s.quote && s.quote !== '“”' && <blockquote>{s.quote}</blockquote>}
                {s.note && <span className="source-flag"><AlertTriangle size={14} /> {s.note}</span>}
              </div>
            </div>
          ))}
        </section>
      )}
    </>
  )
}

export default function SavedItem() {
  const { id } = useParams()
  const query = useQuery(signal => vaultService.getItem(id, signal), [id])
  return <QueryBoundary query={query} skeleton={<PageSkeleton cards={2} rows={2} />}>{item => <Item item={item} reload={() => query.reload({ silent: true })} setItem={query.setData} />}</QueryBoundary>
}

function Item({ item, reload, setItem }) {
  const navigate = useNavigate()
  const { toast } = useUI()
  const [renaming, setRenaming] = useState(null)
  const [busy, setBusy] = useState(null)
  const [version, setVersion] = useState(0)
  const trashed = !!item.trashedAt
  const run = async (key, fn, msg, after) => {
    setBusy(key)
    try { await fn(); if (msg) toast(msg); setVersion(v => v + 1); after ? after() : reload() } catch (e) { toast(e.message, 'info') } finally { setBusy(null) }
  }
  const fav = () => { setItem(i => ({ ...i, favourite: !i.favourite })); run('fav', () => vaultService.setFavourite(item.id, !item.favourite)) }
  const rename = async e => {
    e.preventDefault()
    const title = renaming.trim()
    if (!title) return
    await run('rename', () => vaultService.rename(item.id, title), 'Renamed')
    setRenaming(null)
  }

  return (
    <div className="vi-page">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Legal Vault', to: '/vault' }, { label: item.title.length > 50 ? item.title.slice(0, 50) + '…' : item.title }]} />
      <div className="vi-top">
        <div>
          <h1 dir="auto">{item.title} <span className="pill pill-blue">{KIND_LABEL[item.kind] || item.kind}</span></h1>
          <p>Saved {formatDateTime(item.savedAt)}{item.tag ? ` • ${item.tag}` : ''}</p>
        </div>
        <div className="vi-actions">
          {!trashed && (
            <>
              <button className="btn btn-outline" onClick={fav} disabled={busy === 'fav'}><Star size={17} fill={item.favourite ? '#f59e0b' : 'none'} color={item.favourite ? '#f59e0b' : 'currentColor'} /> {item.favourite ? 'Favourite' : 'Add to favourites'}</button>
              <button className="btn btn-outline" onClick={() => setRenaming(item.title)}><Pencil size={17} /> Rename</button>
              {item.kind === 'answer' && item.conversationId && <Link to={`/chat/${item.conversationId}`} className="btn btn-outline"><MessageCircleMore size={17} /> Open the chat</Link>}
              <button className="btn btn-outline" onClick={() => run('trash', () => vaultService.trash(item.id), 'Moved to Trash', () => navigate('/vault'))} disabled={busy === 'trash'}><Trash2 size={17} /> Move to Trash</button>
            </>
          )}
        </div>
      </div>

      {trashed && (
        <div className="vi-banner" role="status">
          <Trash2 size={18} /> This item is in the Trash. It will be deleted for good 30 days after it was moved here.
          <button className="btn btn-orange btn-sm" onClick={() => run('restore', () => vaultService.restore(item.id), 'Restored')} disabled={busy === 'restore'}><RotateCcw size={16} /> Restore</button>
        </div>
      )}

      {item.kind === 'answer' && item.content && <SavedAnswer content={item.content} />}
      {item.kind === 'analysis' && item.content && <AnalysisResult a={item.content} snapshot />}
      {item.kind === 'analysis' && !item.content && <section className="card vi-q"><p>{item.summary}</p></section>}

      <div className="vi-two">
        <VaultNotes id={item.id} locked={trashed} onChanged={() => setVersion(v => v + 1)}
          api={{ list: vaultService.listNotes, add: vaultService.addNote, remove: vaultService.deleteNote }} />
        <VaultActivity id={item.id} version={version} load={vaultService.listActivity} />
      </div>

      <Modal open={renaming !== null} onClose={() => setRenaming(null)} className="modal-sm">
        <form className="confirm" onSubmit={rename}>
          <span className="icon-tile tile-blue tile-lg"><Pencil /></span>
          <h3>Rename</h3>
          <input autoFocus className="input" maxLength={160} value={renaming || ''} onChange={e => setRenaming(e.target.value)} placeholder="Title" />
          <div className="confirm-actions">
            <button type="button" className="btn btn-outline" onClick={() => setRenaming(null)}>Cancel</button>
            <button className="btn btn-orange" disabled={busy === 'rename' || !(renaming || '').trim()}>{busy === 'rename' && <Loader2 size={16} className="spin" />} Save</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
