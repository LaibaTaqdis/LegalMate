import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertTriangle, ArrowRight, CheckCircle2, CircleDashed, CloudUpload, FileText, Info, Loader2, ShieldAlert } from 'lucide-react'
import { Breadcrumb, Select } from '../components/common'
import { QueryBoundary, PageSkeleton } from '../components/States'
import { useUI } from '../components/UIContext'
import { useQuery } from '../hooks/useApi'
import { guidanceService } from '../api/services/guidanceService'
import { ACCEPTED_TYPES, MAX_UPLOAD_BYTES, MAX_UPLOAD_MB, documentService } from '../api/services/documentService'
import { formatBytes } from '../utils/format'

const LEVEL = { Low: ['pill-green', 'Low risk'], Medium: ['pill-orange', 'Medium risk'], High: ['pill-red', 'High risk'] }
const extOf = n => { const e = n.split('.').pop().toLowerCase(); return e === 'jpeg' ? 'jpg' : e }

export default function ContractCheck() {
  const query = useQuery(signal => guidanceService.contractCheckOptions(signal), [])
  return <QueryBoundary query={query} skeleton={<PageSkeleton cards={2} rows={2} />}>{o => <Page options={o} />}</QueryBoundary>
}

function Page({ options }) {
  const navigate = useNavigate()
  const { toast } = useUI()
  const input = useRef(null)
  const [type, setType] = useState(options.types[0].key)
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const ask = q => navigate(`/chat?q=${encodeURIComponent(q)}`)

  const pick = f => {
    if (!f) return
    if (!ACCEPTED_TYPES.includes(extOf(f.name))) { setError('Please choose a PDF, Word file (.docx) or a clear photo (JPG or PNG).'); return }
    if (f.size > MAX_UPLOAD_BYTES) { setError(`This file is larger than ${MAX_UPLOAD_MB} MB.`); return }
    setError(''); setResult(null); setFile(f)
  }
  const run = async () => {
    if (!file) return
    setBusy(true); setError(''); setResult(null); setProgress(0)
    try {
      const doc = await documentService.upload(file, { onProgress: setProgress })
      setResult(await guidanceService.checkContract(doc.id, type))
      documentService.remove(doc.id).catch(() => {})                      // the text is only needed for this check
    } catch (e) { setError(e.message || 'Could not check this file.') } finally { setBusy(false) }
  }

  const expectedMissing = result?.clauses.filter(c => c.expected && !c.found) || []
  const foundClauses = result?.clauses.filter(c => c.found) || []
  const optionalMissing = result?.clauses.filter(c => !c.expected && !c.found) || []

  return (
    <div className="ccheck">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Dashboard', to: '/dashboard' }, { label: 'Contract check' }]} />
      <div className="page-head"><div><h1 className="page-title">Contract check</h1><p className="page-sub">See which usual clauses are missing and which warning phrases are in your contract, before you sign.</p></div></div>

      <section className="card card-pad cc-form">
        <div className="field calc-field"><span className="field-label">What kind of contract is it?</span><Select value={type} onChange={setType} options={options.types.map(t => ({ value: t.key, label: t.label }))} /></div>
        <div className="field calc-field">
          <span className="field-label">Your contract (PDF, Word or photo, up to {MAX_UPLOAD_MB} MB)</span>
          <input ref={input} type="file" hidden accept=".pdf,.docx,.jpg,.jpeg,.png" onChange={e => { pick(e.target.files[0]); e.target.value = '' }} />
          <button type="button" className="cc-drop" onClick={() => input.current.click()} disabled={busy}>
            <CloudUpload size={26} /> {file ? <span><b>{file.name}</b> · {formatBytes(file.size)}</span> : <span>Choose a file</span>}
          </button>
        </div>
        {error && <div className="calc-error" role="alert"><AlertTriangle size={18} /><p>{error}</p></div>}
        <div className="calc-btns">
          <button className="btn btn-orange btn-xl calc-go" onClick={run} disabled={!file || busy}>{busy ? <Loader2 size={22} className="spin" /> : <ShieldAlert size={22} />} {busy ? (progress < 100 ? `Uploading ${Math.round(progress)}%` : 'Checking…') : 'Check my contract'}</button>
        </div>
        <p className="guide-note"><Info size={15} /> The text is read to run the check and then the uploaded copy is deleted. {options.limits}</p>
      </section>

      {result && (
        <>
          <section className="card card-pad cc-sum">
            <div><h2 className="card-title"><FileText size={20} /> {result.document.name}</h2><p className="page-sub">{result.typeLabel} · {result.words.toLocaleString('en-US')} words read</p></div>
            <div className="cc-stats">
              <span className={`pill ${LEVEL[result.level][0]}`}>{LEVEL[result.level][1]}</span>
              <span><b>{result.summary.foundExpected} of {result.summary.expected}</b> expected clauses found</span>
              <span><b>{result.summary.flags}</b> warning phrase{result.summary.flags === 1 ? '' : 's'}</span>
            </div>
          </section>

          {result.flags.length > 0 && (
            <section className="card card-pad cc-list">
              <h2 className="card-title"><ShieldAlert size={20} /> Warning phrases found</h2>
              <ul>
                {result.flags.map(f => (
                  <li key={f.key}>
                    <div className="cc-head"><b>{f.label}</b><span className={`pill ${f.severity === 'high' ? 'pill-red' : 'pill-orange'}`}>{f.severity === 'high' ? 'Look at this first' : 'Check this'}</span></div>
                    <blockquote>{f.snippet}</blockquote>
                    <p>{f.why}</p>
                    <button type="button" className="link small" onClick={() => ask(f.question)}>Ask LegalMate about this <ArrowRight size={14} /></button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="card card-pad cc-list">
            <h2 className="card-title"><AlertTriangle size={20} /> Expected clauses not found</h2>
            {expectedMissing.length ? (
              <ul>
                {expectedMissing.map(c => (
                  <li key={c.key}>
                    <div className="cc-head"><b>{c.label}</b><span className="pill pill-orange">Not found</span></div>
                    <p>{c.why}</p>
                    <button type="button" className="link small" onClick={() => ask(c.question)}>Ask LegalMate <ArrowRight size={14} /></button>
                  </li>
                ))}
              </ul>
            ) : <p className="guide-note"><CheckCircle2 size={15} /> Every clause we expect in this kind of contract was found.</p>}
            {optionalMissing.length > 0 && <p className="guide-note"><CircleDashed size={15} /> Also not found (not always needed): {optionalMissing.map(c => c.label).join('; ')}.</p>}
          </section>

          <section className="card card-pad cc-list">
            <h2 className="card-title"><CheckCircle2 size={20} /> Clauses found</h2>
            <ul>
              {foundClauses.map(c => (
                <li key={c.key}><div className="cc-head"><b>{c.label}</b><span className="pill pill-green">Found</span></div><blockquote>{c.snippet}</blockquote></li>
              ))}
            </ul>
          </section>

          <p className="guide-note"><Info size={15} /> A clause that is present can still be unfair. For a full review of the risks in plain words, <Link className="link small" to="/analysis/new">run the AI analysis</Link>, or ask a lawyer.</p>
        </>
      )}
    </div>
  )
}
