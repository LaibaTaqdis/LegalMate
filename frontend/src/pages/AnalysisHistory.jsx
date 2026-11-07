import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AlertCircle, ArrowRight, CalendarDays, ChevronLeft, ChevronRight, ClipboardList, Loader2, Plus, Search, SearchX, Trash2, X } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { FileIcon } from '../components/Icons'
import { EmptyState, ErrorState, Skeleton } from '../components/States'
import { useUI } from '../components/UIContext'
import { useQuery } from '../hooks/useApi'
import { useDebounced } from '../hooks/useDebounced'
import { documentService } from '../api/services/documentService'
import { formatDate } from '../utils/format'

// Everything here is inline: filters are buttons, delete asks inside the row. No pop-up windows, no native dropdowns.
const RISK_TONE = { High: 'red', Medium: 'orange', Low: 'green' }
const GROUPS = {
  risk: { label: 'Risk', options: [['all', 'All'], ['High', 'High'], ['Medium', 'Medium'], ['Low', 'Low']] },
  status: { label: 'Status', options: [['all', 'All'], ['completed', 'Completed'], ['running', 'In progress'], ['failed', 'Failed']] },
  days: { label: 'Period', options: [['0', 'Any time'], ['7', '7 days'], ['30', '30 days'], ['90', '90 days']] },
  sort: { label: 'Sort', options: [['newest', 'Newest'], ['oldest', 'Oldest'], ['name', 'Name'], ['risk', 'Highest risk']] },
}
const DEFAULTS = { q: '', risk: 'all', status: 'all', days: '0', sort: 'newest', page: '1' }

function Chip({ on, onClick, children, count }) {
  return (
    <button type="button" className={`ah-chip ${on ? 'on' : ''}`} aria-pressed={on} onClick={onClick}>
      {children}{count !== undefined && <i>{count}</i>}
    </button>
  )
}

function Row({ a, onDelete }) {
  const [asking, setAsking] = useState(false)
  const [busy, setBusy] = useState(false)
  const running = a.status === 'processing'
  const failed = a.status === 'failed'
  const ext = (a.fileType || a.name.split('.').pop() || 'pdf').toLowerCase()
  const meta = [a.documentType, formatDate(a.createdAt), a.counts && !failed && !running ? `${a.counts.clauses} clauses · ${a.counts.deadlines} dates · ${a.counts.missing} missing` : null].filter(Boolean)

  useEffect(() => {
    if (!asking) return undefined
    const esc = e => { if (e.key === 'Escape') setAsking(false) }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [asking])

  const confirm = async () => { setBusy(true); try { await onDelete(a) } finally { setBusy(false); setAsking(false) } }
  const body = (
    <>
      <span className="ah-file"><FileIcon type={['pdf', 'docx', 'jpg', 'png'].includes(ext) ? ext : 'pdf'} size={34} /></span>
      <span className="ah-main">
        <b>{a.name}</b>
        <span className="ah-meta">{meta.join(' · ')}</span>
        {running && <span className="ah-progress" role="progressbar" aria-valuenow={a.progress}><i style={{ width: `${Math.max(8, a.progress)}%` }} /></span>}
        {failed && <span className="ah-error"><AlertCircle size={14} /> {a.error || 'This analysis did not finish.'}</span>}
      </span>
      <span className="ah-status">
        {running ? <span className="pill pill-blue"><Loader2 size={13} className="spin" /> Analysing {a.progress}%</span>
          : failed ? <span className="pill pill-gray">Failed</span>
            : <span className={`pill pill-${RISK_TONE[a.risk] || 'gray'}`}>{a.risk ? `${a.risk} risk` : 'Done'}</span>}
      </span>
    </>
  )

  return (
    <li className={`ah-row ${failed ? 'failed' : ''}`}>
      {failed ? <div className="ah-link">{body}</div> : <Link className="ah-link" to={`/analysis/${a.id}`}>{body}<ArrowRight size={18} className="ah-go" /></Link>}
      <div className="ah-actions">
        {asking ? (
          <span className="ah-ask" role="alert">
            <span>Delete this analysis and the stored text of its document?</span>
            <button type="button" className="btn btn-sm ah-danger" onClick={confirm} disabled={busy}>{busy && <Loader2 size={14} className="spin" />} Delete</button>
            <button type="button" className="btn btn-sm btn-outline" onClick={() => setAsking(false)} disabled={busy}>Keep</button>
          </span>
        ) : (
          <>
            {failed && <Link to="/analysis/new" className="btn btn-sm btn-outline">Try again</Link>}
            <button type="button" className="icon-btn-plain ah-del" onClick={() => setAsking(true)} aria-label={`Delete ${a.name}`}><Trash2 size={17} /></button>
          </>
        )}
      </div>
    </li>
  )
}

export default function AnalysisHistory() {
  const { toast } = useUI()
  const [params, setParams] = useSearchParams()
  const f = useMemo(() => ({ ...DEFAULTS, ...Object.fromEntries(params) }), [params])
  const [text, setText] = useState(f.q)
  const debounced = useDebounced(text, 350)

  const set = patch => setParams(prev => {
    const next = new URLSearchParams(prev)
    Object.entries({ page: '1', ...patch }).forEach(([k, v]) => (v === DEFAULTS[k] || v === '' ? next.delete(k) : next.set(k, v)))
    return next
  }, { replace: true })

  useEffect(() => { if (debounced !== f.q) set({ q: debounced.trim() }) }, [debounced]) // eslint-disable-line react-hooks/exhaustive-deps

  const query = useQuery(signal => documentService.listAnalyses({ q: f.q, risk: f.risk, status: f.status, days: f.days, sort: f.sort, page: f.page }, signal),
    [f.q, f.risk, f.status, f.days, f.sort, f.page], { pollInterval: 4000, shouldPoll: d => d?.items?.some(i => i.status === 'processing') })
  const data = query.data
  const counts = data?.counts
  const filtered = f.q || f.risk !== 'all' || f.status !== 'all' || f.days !== '0'
  const clear = () => { setText(''); setParams({}, { replace: true }) }

  const remove = async a => {
    try {
      await documentService.deleteAnalysis(a.id)
      toast('Analysis deleted')
      query.reload()
    } catch (e) { toast(e.message || 'Could not delete it', 'info') }
  }

  const count = (group, value) => {
    if (!counts) return undefined
    if (group === 'risk') return value === 'all' ? counts.all : counts[value]
    if (group === 'status') return value === 'all' ? counts.all : counts[value]
    return undefined
  }
  const pages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1
  const from = data && data.total ? (data.page - 1) * data.pageSize + 1 : 0
  const to = data ? Math.min(data.total, data.page * data.pageSize) : 0

  return (
    <div className="ah">
      <div className="page-head">
        <div>
          <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Analysis' }]} />
          <h1 className="page-title">Analysis</h1>
          <p className="page-sub">Your analysed documents. Open one to see its summary, risks and deadlines.</p>
        </div>
        <Link to="/analysis/new" className="btn btn-orange btn-lg"><Plus size={20} /> New Analysis</Link>
      </div>

      <section className="card ah-tools" aria-label="Filters">
        <label className="input-wrap ah-search">
          <Search size={18} />
          <input value={text} onChange={e => setText(e.target.value)} placeholder="Search by document name" maxLength={80} aria-label="Search analyses" />
          {text && <button type="button" className="icon-btn-plain" onClick={() => setText('')} aria-label="Clear search"><X size={16} /></button>}
        </label>
        <div className="ah-groups">
          {Object.entries(GROUPS).map(([key, g]) => (
            <div key={key} className="ah-group" role="group" aria-label={g.label}>
              <span className="ah-label">{g.label}</span>
              {g.options.map(([value, label]) => (
                <Chip key={value} on={f[key] === value} onClick={() => set({ [key]: value })} count={count(key, value)}>{label}</Chip>
              ))}
            </div>
          ))}
        </div>
        {filtered && <button type="button" className="link small ah-clear" onClick={clear}><X size={14} /> Clear filters</button>}
      </section>

      {query.loading && !data && <div className="card ah-list-card"><Skeleton h={72} style={{ margin: 14 }} /><Skeleton h={72} style={{ margin: 14 }} /><Skeleton h={72} style={{ margin: 14 }} /></div>}
      {query.error && !data && <ErrorState error={query.error} onRetry={query.reload} />}
      {data && (
        <section className="card ah-list-card">
          {data.items.length === 0 ? (
            counts?.all === 0 || (!filtered && data.total === 0)
              ? <EmptyState icon={ClipboardList} title="No analyses yet" text="Upload a contract, notice or other legal document and LegalMate will explain it in plain language." action={<Link to="/analysis/new" className="btn btn-orange"><Plus size={18} /> New Analysis</Link>} />
              : <EmptyState icon={SearchX} title="No analyses match" text="Try a different search, or clear the filters." action={<button type="button" className="btn btn-outline" onClick={clear}>Clear filters</button>} />
          ) : (
            <>
              <ul className="ah-list">{data.items.map(a => <Row key={a.id} a={a} onDelete={remove} />)}</ul>
              <div className="ah-foot">
                <span><CalendarDays size={15} /> Showing {from}–{to} of {data.total}</span>
                {pages > 1 && (
                  <span className="ah-pager">
                    <button type="button" className="btn btn-sm btn-outline" disabled={data.page <= 1} onClick={() => set({ page: String(data.page - 1) })}><ChevronLeft size={16} /> Previous</button>
                    <b>Page {data.page} of {pages}</b>
                    <button type="button" className="btn btn-sm btn-outline" disabled={data.page >= pages} onClick={() => set({ page: String(data.page + 1) })}>Next <ChevronRight size={16} /></button>
                  </span>
                )}
              </div>
            </>
          )}
        </section>
      )}
    </div>
  )
}
