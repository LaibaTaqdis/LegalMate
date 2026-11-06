import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  AlertTriangle, ArrowRight, Bookmark, Briefcase, CalendarDays, CheckCircle2, ChevronDown, Copy, FileText,
  Flag, Globe, House, Info, ListChecks, Loader2, MessageCircleMore, MessageSquare, Mic, MoreHorizontal, MoreVertical,
  Paperclip, Plus, Search, SendHorizontal, Share, ShoppingCart, SlidersHorizontal, ThumbsDown, ThumbsUp,
  UserRound, UserRoundSearch, Users, X, ScrollText, NotebookText, Trash2, Pin
} from 'lucide-react'
import { Ring, useClickOutside } from '../components/common'
import { ErrorState, Skeleton } from '../components/States'
import { useUI } from '../components/UIContext'
import { useAuth } from '../context/AuthContext'
import { USE_MOCKS } from '../api/config'
import { chatService } from '../api/services/chatService'
import { TOPIC_CARDS } from '../api/mocks/chat'
import { formatDate, formatTime } from '../utils/format'

/* ---------------- normalisers: accept both mock shapes and API shapes ---------------- */
const isToday = d => new Date(d).toDateString() === new Date().toDateString()
function groupFor(iso) {
  if (!iso) return 'Today'
  const days = (Date.now() - new Date(iso).getTime()) / 86400000
  return isToday(iso) ? 'Today' : days <= 7 ? 'Previous 7 Days' : 'Older'
}
const normConv = c => ({
  ...c,
  group: c.group || (c.pinned ? 'Today' : groupFor(c.updatedAt)),
  time: c.time || (c.updatedAt ? (isToday(c.updatedAt) ? formatTime(c.updatedAt) : new Date(c.updatedAt).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })) : ''),
})
const normMsg = m => {
  const kind = m.kind || (m.role === 'user' ? 'user' : 'answer')
  const time = m.time || formatTime(m.createdAt)
  return { ...m, kind, text: m.text ?? m.content, time, doneTime: m.doneTime || time }
}

/* ---------------- shared chat store (survives route changes, hydrated from the API) ---------------- */
const store = {
  convs: null, convsError: null, loadingConvs: false,
  msgs: {}, loading: {}, errors: {},
  listeners: new Set(), version: 0,
  emit() { this.version++; this.listeners.forEach(l => l()) },
}
const subscribe = l => { store.listeners.add(l); return () => store.listeners.delete(l) }
const useStore = () => { useSyncExternalStore(subscribe, () => store.version); return store }

async function loadConversations(force = false) {
  if ((store.convs && !force) || store.loadingConvs) return
  store.loadingConvs = true
  store.convsError = null
  store.emit()
  try {
    const { items } = await chatService.listConversations()
    store.convs = items.map(normConv)
  } catch (e) {
    store.convsError = e
  } finally {
    store.loadingConvs = false
    store.emit()
  }
}

async function loadMessages(id, force = false) {
  if ((store.msgs[id] && !force) || store.loading[id]) return
  store.loading[id] = true
  store.errors[id] = null
  store.emit()
  try {
    const { conversation, messages } = await chatService.getConversation(id)
    store.msgs[id] = messages.map(normMsg)
    if (conversation && store.convs && !store.convs.some(c => c.id === id)) store.convs = [normConv(conversation), ...store.convs]
  } catch (e) {
    store.errors[id] = e
  } finally {
    store.loading[id] = false
    store.emit()
  }
}

function upsertConv(conv) {
  const c = normConv(conv)
  store.convs = [c, ...(store.convs || []).filter(x => x.id !== c.id)]
}

const now = () => new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })

const CONV_ICONS = { chat: MessageCircleMore, briefcase: Briefcase, doc: ScrollText, home: House, message: MessageSquare, file: FileText, person: UserRound }
const CARD_ICONS = { home: House, briefcase: Briefcase, users: Users, cart: ShoppingCart }

/* ---------------- rich text with citation chips ---------------- */
function Rich({ parts, onCite }) {
  if (typeof parts === 'string') return parts
  return (parts || []).map((p, i) => {
    if (typeof p === 'string') return <span key={i}>{p}</span>
    if (p.b) return <b key={i}>{p.b}</b>
    if (p.cite) return <button key={i} className="cite" onClick={() => onCite(p.cite)}>[{p.cite}]</button>
    return null
  })
}

/* ---------------- Conversations sidebar ---------------- */
function ConversationList({ activeId }) {
  const s = useStore()
  const navigate = useNavigate()
  const { toast } = useUI()
  const [q, setQ] = useState('')
  const [menu, setMenu] = useState(null)
  const closeMenu = useMemo(() => () => setMenu(null), [])
  const ref = useClickOutside(closeMenu)
  const list = (s.convs || []).filter(c => (c.title + c.preview).toLowerCase().includes(q.toLowerCase()))
  const groups = ['Today', 'Previous 7 Days', 'Older']

  const remove = async id => {
    const prev = store.convs
    store.convs = store.convs.filter(c => c.id !== id)
    store.emit()
    setMenu(null)
    if (id === activeId) navigate('/chat?new=1')
    try {
      await chatService.deleteConversation(id)
      delete store.msgs[id]
      toast('Conversation deleted')
    } catch (e) {
      store.convs = prev
      store.emit()
      toast(e.message || 'Could not delete the conversation', 'info')
    }
  }
  const pin = async id => {
    const c = store.convs.find(x => x.id === id)
    store.convs = [{ ...c, group: 'Today', pinned: true }, ...store.convs.filter(x => x.id !== id)]
    store.emit()
    setMenu(null)
    try { await chatService.pinConversation(id, true); toast('Conversation pinned to Today') } catch (e) { toast(e.message, 'info'); loadConversations(true) }
  }

  return (
    <aside className="card conv-panel" ref={ref}>
      <div className="conv-head">
        <h2>Conversations</h2>
        <button className="icon-btn-plain" aria-label="Filter conversations" onClick={() => toast('Showing all conversations', 'info')}><SlidersHorizontal size={20} /></button>
      </div>
      <Link to="/chat?new=1" className="btn btn-orange btn-block conv-new"><Plus size={20} /> New Chat</Link>
      <label className="conv-search"><Search size={17} /><input value={q} onChange={e => setQ(e.target.value)} placeholder="Search conversations..." /></label>
      <div className="conv-scroll">
        {!s.convs && s.loadingConvs && Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} h={46} style={{ margin: '10px 0' }} />)}
        {s.convsError && !s.convs && <ErrorState compact error={s.convsError} onRetry={() => loadConversations(true)} />}
        {groups.map(g => {
          const items = list.filter(c => c.group === g)
          if (!items.length) return null
          return (
            <div key={g} className="conv-group">
              <p className="conv-group-title">{g}</p>
              {items.map(c => {
                const Icon = CONV_ICONS[c.icon] || MessageSquare
                return (
                  <div key={c.id} className={`conv-item ${c.id === activeId ? 'active' : ''}`} onClick={() => navigate(`/chat/${c.id}`)}>
                    <span className="conv-icon"><Icon size={18} /></span>
                    <div className="conv-text"><b>{c.title}</b><span>{c.preview}</span></div>
                    <span className="conv-time">{c.time}</span>
                    <button className="icon-btn-plain conv-kebab" aria-label="Conversation options" onClick={e => { e.stopPropagation(); setMenu(menu === c.id ? null : c.id) }}><MoreVertical size={17} /></button>
                    {menu === c.id && (
                      <div className="popover conv-menu" onClick={e => e.stopPropagation()}>
                        <button className="popover-item" onClick={() => pin(c.id)}><Pin size={15} />Pin to top</button>
                        <button className="popover-item danger" onClick={() => remove(c.id)}><Trash2 size={15} />Delete</button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )
        })}
        {s.convs && !list.length && <p className="conv-empty">No conversations found.</p>}
      </div>
    </aside>
  )
}

/* ---------------- Composer ---------------- */
function Composer({ onSend, placeholder, big, disabled }) {
  const { toast, language } = useUI()
  const [text, setText] = useState('')
  const [lang, setLang] = useState(language === 'English' ? 'اردو' : language)
  const [langOpen, setLangOpen] = useState(false)
  const [recording, setRecording] = useState(false)
  const [files, setFiles] = useState([]) // { id, name, uploading }
  const fileRef = useRef(null)
  const langRef = useClickOutside(() => setLangOpen(false))

  const attach = async list => {
    for (const file of Array.from(list)) {
      const temp = { id: `tmp_${file.name}`, name: file.name, uploading: true }
      setFiles(f => [...f, temp])
      try {
        const doc = await chatService.uploadAttachment(file)
        setFiles(f => f.map(x => (x.id === temp.id ? { id: doc.id, name: doc.name || file.name } : x)))
      } catch (e) {
        setFiles(f => f.filter(x => x.id !== temp.id))
        toast(`${file.name}: ${e.message || 'upload failed'}`, 'info')
      }
    }
  }

  const send = () => {
    if (disabled) return
    if (files.some(f => f.uploading)) return toast('Please wait for attachments to finish uploading', 'info')
    if (!text.trim() && !files.length) return
    onSend(text.trim() || `Please review the attached file: ${files[0].name}`, {
      attachmentIds: files.map(f => f.id),
      language: lang === 'English' ? 'en' : 'ur',
    })
    setText('')
    setFiles([])
  }

  return (
    <div className={`composer ${big ? 'composer-big' : ''}`}>
      {files.length > 0 && (
        <div className="composer-files">
          {files.map(f => <span key={f.id} className="pill pill-blue">{f.uploading ? <Loader2 size={13} className="spin" /> : <Paperclip size={13} />}{f.name}<button onClick={() => setFiles(files.filter(x => x.id !== f.id))} aria-label="Remove"><X size={13} /></button></span>)}
        </div>
      )}
      <textarea value={text} maxLength={4000} onChange={e => setText(e.target.value)} placeholder={placeholder}
        rows={big ? 2 : 1}
        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} />
      <div className="composer-bar">
        <input ref={fileRef} type="file" hidden multiple accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" onChange={e => { attach(e.target.files); e.target.value = '' }} />
        <button className="composer-tool" onClick={() => fileRef.current.click()}><Paperclip size={20} /> Attach</button>
        <button className={`composer-tool ${recording ? 'rec' : ''}`} onClick={() => { setRecording(r => !r); toast(recording ? 'Voice input stopped' : 'Listening… speak your question', 'info') }}><Mic size={20} /> {recording ? 'Listening…' : 'Voice'}</button>
        <div className="composer-lang" ref={langRef}>
          <button className="composer-tool" onClick={() => setLangOpen(o => !o)}><Globe size={20} /> <span className={lang === 'اردو' ? 'urdu' : ''}>{lang}</span> <ChevronDown size={15} /></button>
          {langOpen && (
            <div className="popover popover-sm composer-lang-menu">
              {['English', 'اردو'].map(l => <button key={l} className={`popover-item ${l === lang ? 'active' : ''}`} onClick={() => { setLang(l); setLangOpen(false) }}>{l}</button>)}
            </div>
          )}
        </div>
        {big && <span className="composer-count">{text.length}/4000</span>}
        <button className="composer-send" onClick={send} disabled={disabled} aria-label="Send"><SendHorizontal size={22} /></button>
      </div>
    </div>
  )
}

/* ---------------- Answer bubble ---------------- */
function Answer({ m, onCite, onPanel, panel }) {
  const { toast } = useUI()
  const navigate = useNavigate()
  const [vote, setVote] = useState(m.feedback || null)
  const [saving, setSaving] = useState(false)

  const copy = () => {
    const text = [m.intro, m.law].flat().filter(x => typeof x === 'string').join('')
    navigator.clipboard?.writeText(text)
    toast('Answer copied to clipboard')
  }
  const rate = async v => {
    const prev = vote
    setVote(v)
    try {
      await chatService.feedback(m.id, v)
      toast(v === 'up' ? 'Thanks for your feedback!' : 'Thanks - we’ll use this to improve.', v === 'up' ? 'success' : 'info')
    } catch (e) { setVote(prev); toast(e.message, 'info') }
  }
  const save = async () => {
    setSaving(true)
    try { await chatService.saveToVault(m.id); toast('Answer saved to your Legal Vault') } catch (e) { toast(e.message, 'info') } finally { setSaving(false) }
  }

  return (
    <div className="msg-bot">
      <span className="msg-bot-avatar"><img src="/assets/img/logo-mark-gold.png" alt="" /></span>
      <div className="msg-bot-body">
        <p className="msg-meta"><b>LegalMate</b> {m.time}</p>
        <div className="answer">
          <p><Rich parts={m.intro} onCite={onCite} /></p>
          {m.lawTitle && <h4><FileText size={20} /> {m.lawTitle}</h4>}
          {m.law && <p><Rich parts={m.law} onCite={onCite} /></p>}
          {m.steps?.length > 0 && (
            <>
              <h4><ListChecks size={20} /> Steps you can take</h4>
              <ol className="answer-steps">
                {m.steps.map((s, i) => <li key={i}><span>{i + 1}</span><p><Rich parts={s} onCite={onCite} /></p></li>)}
              </ol>
            </>
          )}
          {m.important && (
            <div className="answer-important">
              <AlertTriangle size={22} />
              <div><b>Important</b><p>{m.important}</p></div>
            </div>
          )}
          {m.outro && <p>{m.outro}</p>}
        </div>
        <p className="msg-done">{m.doneTime}</p>
        <div className="answer-actions">
          <button className={`chip-btn chip-sources ${panel === 'sources' ? 'on' : ''}`} onClick={() => onPanel('sources')}><NotebookText size={16} /> Sources: {m.sources?.length || 0} <ChevronDown size={15} /></button>
          {m.confidence && <button className={`chip-btn chip-conf ${panel === 'confidence' ? 'on' : ''}`} onClick={() => onPanel('confidence')}><CheckCircle2 size={16} /> {m.confidence.score}% Confidence</button>}
          <button className="chip-btn" onClick={save} disabled={saving}>{saving ? <Loader2 size={16} className="spin" /> : <Bookmark size={16} />} Save to Vault</button>
          <button className="chip-btn" onClick={() => navigate(`/case-briefs/new?fromMessage=${encodeURIComponent(m.id)}`)}><FileText size={16} /> Create Case Brief</button>
        </div>
        <div className="answer-feedback">
          <button className={vote === 'up' ? 'on' : ''} onClick={() => rate('up')} aria-label="Helpful"><ThumbsUp size={19} /></button>
          <button className={vote === 'down' ? 'on' : ''} onClick={() => rate('down')} aria-label="Not helpful"><ThumbsDown size={19} /></button>
          <button onClick={copy} aria-label="Copy"><Copy size={19} /></button>
          <button onClick={() => toast('More options coming soon', 'info')} aria-label="More"><MoreHorizontal size={19} /></button>
        </div>
      </div>
    </div>
  )
}

/* ---------------- Right panels ---------------- */
function SourcesPanel({ message, onClose, highlight }) {
  const { toast } = useUI()
  const [vote, setVote] = useState(null)
  const refs = useRef({})
  const sources = message?.sources || []
  useEffect(() => {
    if (highlight) refs.current[highlight.id]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [highlight])

  const report = async () => {
    try {
      await chatService.reportSource({ messageId: message?.id, sourceId: highlight?.id ?? sources[0]?.id, reason: 'user_report' })
      toast('Thanks - our team will review this source.', 'info')
    } catch (e) { toast(e.message, 'info') }
  }
  const rate = v => { setVote(v); if (message?.id) chatService.feedback(message.id, v, 'sources').catch(() => {}) }

  return (
    <aside className="card side-panel">
      <div className="side-panel-head">
        <div><h2>Sources and Citations</h2><p>Click on a citation to view the source and relevant details.</p></div>
        <button className="icon-btn-plain" onClick={onClose} aria-label="Close"><X size={22} /></button>
      </div>
      <div className="side-panel-scroll">
        {sources.map(s => (
          <div key={s.id} ref={el => (refs.current[s.id] = el)} className={`source-card ${highlight?.id === s.id ? 'flash' : ''}`}>
            <div className="source-top">
              <span className="source-num">{s.id}</span>
              <div><b>{s.title}</b><span>{s.section}</span></div>
              <span className={`pill ${s.type === 'Rule' ? 'pill-purple' : s.type === 'Judgment' ? 'pill-purple' : 'pill-blue'}`}>{s.type}</span>
            </div>
            <blockquote>{s.quote}</blockquote>
            {s.url
              ? <a className="link small" href={s.url} target="_blank" rel="noreferrer">View full source <ArrowRight size={15} /></a>
              : <button className="link small" onClick={() => toast(`Opening ${s.title} - ${s.section}`, 'info')}>View full source <ArrowRight size={15} /></button>}
          </div>
        ))}
        {!sources.length && <p className="conv-empty">No sources for this answer.</p>}
        <div className="helpful">
          <span>Was this helpful?</span>
          <button className={vote === 'up' ? 'on' : ''} onClick={() => rate('up')} aria-label="Yes"><ThumbsUp size={18} /></button>
          <button className={vote === 'down' ? 'on' : ''} onClick={() => rate('down')} aria-label="No"><ThumbsDown size={18} /></button>
        </div>
        <button className="report" onClick={report}><Flag size={17} /> Report an issue with this source</button>
      </div>
    </aside>
  )
}

function ConfidencePanel({ c, onClose, onSources }) {
  const navigate = useNavigate()
  const label = c.score >= 80 ? 'High Confidence' : c.score >= 60 ? 'Medium Confidence' : 'Low Confidence'
  const factors = [
    { label: 'Source relevance', v: c.relevance, color: '#22a45a' },
    { label: 'Source agreement', v: c.agreement, color: '#1d4ed8' },
    { label: 'Information recency', v: c.recency, color: '#7c3aed' },
  ]
  const verifiedDate = c.verified || formatDate(c.verifiedAt)
  const verifiedTime = c.verifiedTime || formatTime(c.verifiedAt)
  return (
    <aside className="card side-panel conf-panel">
      <div className="side-panel-head">
        <h2 className="conf-title">Answer Confidence</h2>
        <button className="icon-btn-plain" onClick={onClose} aria-label="Close"><X size={24} /></button>
      </div>
      <div className="side-panel-scroll">
        <div className="conf-ring">
          <Ring value={c.score} size={150} stroke={13} color={c.score >= 80 ? '#22a45a' : '#f59e0b'}><b className="conf-score">{c.score}%</b></Ring>
          <span className={`pill ${c.score >= 80 ? 'pill-green' : 'pill-orange'} conf-label`}>{label}</span>
        </div>
        <p className="conf-desc">This score reflects source relevance, agreement and recency. While the answer is well supported by legal sources, you should always verify important matters or consult a qualified lawyer.</p>
        <div className="conf-divider" />
        <h3 className="conf-h3">Confidence factors <Info size={16} /></h3>
        {factors.map(f => (
          <div key={f.label} className="conf-factor">
            <span>{f.label} <Info size={14} /></span>
            <div className="conf-bar-row"><div className="progress"><span style={{ width: `${f.v}%`, background: f.color }} /></div><b style={{ color: f.color }}>{f.v}%</b></div>
          </div>
        ))}
        <div className="conf-stats">
          <div><FileText size={24} /><span>Sources checked<b>{c.checked}</b></span></div>
          <div><CalendarDays size={24} /><span>Last verified<b>{verifiedDate}<br />{verifiedTime}</b></span></div>
        </div>
        <div className="conf-warn">
          <AlertTriangle size={26} />
          <div><b>Confidence does not replace advice from a qualified lawyer.</b><p>Legal situations can be complex and facts may change. Please consider consulting a licensed legal professional for specific advice.</p></div>
        </div>
        <button className="btn btn-navy btn-block btn-lg" onClick={onSources}>Review Sources <ArrowRight size={18} /></button>
        <button className="btn btn-outline-navy btn-block btn-lg conf-lawyer" onClick={() => navigate('/legal-aid')}><UserRoundSearch size={19} /> Find a Lawyer</button>
      </div>
    </aside>
  )
}

/* ---------------- Page ---------------- */
export default function Chat() {
  const { id } = useParams()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const { toast } = useUI()
  const { user } = useAuth()
  const s = useStore()
  const [banner, setBanner] = useState(true)
  const [typing, setTyping] = useState(false)
  const [highlight, setHighlight] = useState(null)
  const scrollRef = useRef(null)

  useEffect(() => { loadConversations() }, [])
  useEffect(() => { if (id) loadMessages(id) }, [id])

  const isNew = params.get('new') === '1'
  const conv = id ? s.convs?.find(c => c.id === id) : null
  const messages = id ? s.msgs[id] || [] : []
  const lastAnswer = [...messages].reverse().find(m => m.kind === 'answer')
  const defaultPanel = id === 'tenant-rights' ? 'sources' : null
  const panel = params.get('panel') ?? defaultPanel
  const setPanel = p => setParams(prev => { const n = new URLSearchParams(prev); n.set('panel', p || 'none'); return n }, { replace: true })
  const activePanel = panel === 'none' ? null : panel

  // Scroll to the newest message only when the conversation grows, not when it is first opened.
  const seen = useRef({ id, len: messages.length })
  useEffect(() => {
    if (seen.current.id !== id) { seen.current = { id, len: messages.length }; scrollRef.current?.scrollTo({ top: 0 }); return }
    if (messages.length > seen.current.len || typing) scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
    seen.current.len = messages.length
  }, [id, messages.length, typing])

  const reply = async (convId, text, opts = {}) => {
    setTyping(true)
    try {
      const answer = normMsg(await chatService.sendMessage(convId, { content: text, ...opts }))
      store.msgs[convId] = [...(store.msgs[convId] || []), answer]
      const c = store.convs?.find(x => x.id === convId)
      if (c) upsertConv({ ...c, preview: `${text.slice(0, 32)}...`, time: now(), group: 'Today' })
      store.emit()
    } catch (e) {
      toast(e.message || 'LegalMate could not answer right now. Please try again.', 'info')
    } finally {
      setTyping(false)
    }
  }

  const startConversation = async (text, opts = {}) => {
    try {
      const { conversation } = await chatService.createConversation({ firstMessage: text, topic: opts.topic })
      upsertConv(conversation)
      store.msgs[conversation.id] = [normMsg({ id: `local_${Date.now()}`, kind: 'user', text, time: now() })]
      store.emit()
      navigate(`/chat/${conversation.id}`)
      reply(conversation.id, text, opts)
    } catch (e) {
      toast(e.message || 'Could not start a conversation', 'info')
    }
  }

  // Search from the top bar lands here with ?q=
  useEffect(() => {
    const q = params.get('q')
    if (q) { setParams({}, { replace: true }); startConversation(q) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Mock mode opens the seeded demo conversations; with a backend a topic card starts a new conversation.
  const openTopic = card => {
    if (USE_MOCKS && store.convs?.some(c => c.id === card.key)) return navigate(`/chat/${card.key}`)
    startConversation(card.starter, { topic: card.key })
  }

  const sendFollowUp = (text, opts) => {
    store.msgs[id] = [...messages, normMsg({ id: `local_${Date.now()}`, kind: 'user', text, time: now() })]
    store.emit()
    reply(id, text, opts)
  }

  const onCite = n => {
    setPanel('sources')
    setHighlight({ id: n, t: Date.now() })
  }

  const share = () => { navigator.clipboard?.writeText(window.location.href); toast('Link copied to clipboard') }

  /* ----- Empty state (screen 6) ----- */
  if (!id || (!conv && s.convs && !s.loading[id] && !s.msgs[id])) {
    // The design shows the "Tenant rights in Pakistan" header on the empty state; with a real backend it is a fresh chat.
    const designHeader = USE_MOCKS && !isNew && !id
    return (
      <div className="chat-page">
        <ConversationList activeId={designHeader ? 'tenant-rights' : null} />
        <section className="card chat-main">
          <header className="chat-head">
            <div>
              <h1>{designHeader ? 'Tenant rights in Pakistan' : 'New conversation'} <span className="pill pill-blue">{designHeader ? 'Property Law' : 'General'}</span></h1>
              <p>{designHeader ? 'Started today, 10:24 AM' : 'Started just now'}</p>
            </div>
            <div className="chat-head-actions">
              <button onClick={share}><Share size={19} /> Share</button>
              <button onClick={() => toast('Conversation saved')}><Bookmark size={19} /> Save</button>
              <button aria-label="More" onClick={() => toast('More options coming soon', 'info')}><MoreHorizontal size={20} /></button>
            </div>
          </header>
          {banner && (
            <div className="chat-banner"><Info size={20} /><span>LegalMate provides general legal information based on Pakistani laws and reliable sources. This is not formal legal advice.</span><button onClick={() => setBanner(false)} aria-label="Dismiss"><X size={18} /></button></div>
          )}
          <div className="chat-empty">
            <div className="chat-empty-center">
              <img src="/assets/img/robot.png" alt="LegalMate assistant" className="chat-robot" />
              <h2>What legal matter can I <i>help</i> you understand?</h2>
              <p>Ask me anything about Pakistani laws, your rights, or legal procedures.<br />Get clear, simple and source-backed answers.</p>
              <div className="topic-grid">
                {TOPIC_CARDS.map(t => {
                  const Icon = CARD_ICONS[t.icon]
                  return (
                    <button key={t.key} className="topic-card" onClick={() => openTopic(t)}>
                      <Icon size={30} strokeWidth={1.6} />
                      <b>{t.title}</b>
                      <span>{t.text}</span>
                      <span className="circle-btn topic-arrow"><ArrowRight size={18} /></span>
                    </button>
                  )
                })}
              </div>
              <div className="chat-or"><span>or ask your own question</span></div>
            </div>
            <Composer big placeholder="Type your legal question here..." onSend={startConversation} />
            <div className="chat-foot"><span>LegalMate provides information, not formal legal representation.</span><span>Press Enter to send  •  Shift + Enter for new line</span></div>
          </div>
        </section>
      </div>
    )
  }

  /* ----- Conversation (screens 7 & 8) ----- */
  const loadingMsgs = s.loading[id] && !s.msgs[id]
  return (
    <div className={`chat-page ${activePanel ? 'with-panel' : ''}`}>
      <ConversationList activeId={id} />
      <section className="card chat-main">
        <header className="chat-head chat-head-compact">
          <div>
            <h1>{conv?.title || 'Conversation'} {conv?.tag && <span className="pill pill-blue">{conv.tag}</span>}</h1>
            <p>Today, {messages[0]?.time || ''}</p>
          </div>
          <div className="chat-head-actions">
            {!activePanel && <button onClick={share}><Share size={19} /> Share</button>}
            <button aria-label="More" onClick={() => toast('More options coming soon', 'info')}><MoreHorizontal size={20} /></button>
          </div>
        </header>
        <div className="chat-scroll" ref={scrollRef}>
          {loadingMsgs && <><Skeleton h={60} w="60%" style={{ alignSelf: 'flex-end' }} /><Skeleton h={320} /></>}
          {s.errors[id] && !s.msgs[id] && <ErrorState error={s.errors[id]} onRetry={() => loadMessages(id, true)} />}
          {messages.map(m => m.kind === 'user' ? (
            <div key={m.id} className="msg-user">
              <div className="msg-user-bubble"><p>{m.text}</p><span>{m.time}</span></div>
              <span className="avatar msg-user-avatar">{user?.initials}</span>
            </div>
          ) : (
            <Answer key={m.id} m={m} onCite={onCite} panel={activePanel} onPanel={p => setPanel(activePanel === p ? null : p)} />
          ))}
          {typing && (
            <div className="msg-bot">
              <span className="msg-bot-avatar"><img src="/assets/img/logo-mark-gold.png" alt="" /></span>
              <div className="typing"><i /><i /><i /></div>
            </div>
          )}
        </div>
        <div className="chat-compose-wrap">
          <Composer placeholder="Type a follow-up question..." onSend={sendFollowUp} disabled={typing} />
          <div className="chat-foot"><span>LegalMate provides information, not formal legal representation.</span><span>Press Enter to send  •  Shift + Enter for new line</span></div>
        </div>
      </section>
      {activePanel === 'sources' && lastAnswer && <SourcesPanel message={lastAnswer} highlight={highlight} onClose={() => setPanel(null)} />}
      {activePanel === 'confidence' && lastAnswer?.confidence && <ConfidencePanel c={lastAnswer.confidence} onClose={() => setPanel(null)} onSources={() => setPanel('sources')} />}
    </div>
  )
}
