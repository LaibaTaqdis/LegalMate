import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AlertTriangle, Bookmark, Copy, Download, Info, Loader2, Mail } from 'lucide-react'
import { Breadcrumb, Select } from '../components/common'
import { QueryBoundary, PageSkeleton } from '../components/States'
import { useUI } from '../components/UIContext'
import { useQuery } from '../hooks/useApi'
import { guidanceService } from '../api/services/guidanceService'

export default function Letter() {
  const { id } = useParams()
  const query = useQuery(signal => guidanceService.letter(id, signal), [id])
  return <QueryBoundary query={query} skeleton={<PageSkeleton cards={2} rows={4} />}>{spec => <LetterPage key={spec.id} spec={spec} />}</QueryBoundary>
}

const initial = spec => Object.fromEntries(spec.fields.map(f => [f.key, f.default === 'today' ? new Date().toISOString().slice(0, 10) : f.default ?? '']))

function LetterPage({ spec }) {
  const { toast } = useUI()
  const [values, setValues] = useState(() => initial(spec))
  const [letter, setLetter] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(null)
  const [saved, setSaved] = useState(null)
  const set = k => v => setValues(p => ({ ...p, [k]: v }))
  const payload = useMemo(() => Object.fromEntries(Object.entries(values).filter(([, v]) => String(v).trim() !== '')), [values])

  const run = async (kind, fn, ok) => {
    setBusy(kind); setError('')
    try { const r = await fn(); if (ok) ok(r) } catch (e) { setError((e.message || 'Something went wrong.').replace(/^[A-Za-z ]+: (?=[A-Z])/, '')); setLetter(l => (kind === 'make' ? null : l)) } finally { setBusy(null) }
  }
  const missing = spec.fields.find(f => f.required && !String(values[f.key] ?? '').trim())
  const make = () => {
    if (missing) { setError(`${missing.label}: this field is required.`); return }
    setSaved(null)
    run('make', () => guidanceService.renderLetter(spec.id, payload), r => setLetter(r))
  }
  const copy = () => { navigator.clipboard?.writeText(letter.text); toast('Letter copied to clipboard') }
  const download = () => run('pdf', () => guidanceService.downloadLetter(spec.id, payload), () => toast('Downloading your letter (PDF)'))
  const save = () => run('save', () => guidanceService.saveLetter(spec.id, payload), r => { setSaved(r.id); toast('Letter saved to your Legal Vault') })

  return (
    <div className="letter">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Dashboard', to: '/dashboard' }, { label: spec.title }]} />
      <div className="page-head"><div><h1 className="page-title">{spec.title}</h1><p className="page-sub">{spec.summary}</p></div></div>

      <div className="letter-grid">
        <section className="card card-pad letter-form">
          {spec.fields.map(f => (
            <div key={f.key} className="field calc-field">
              <span className="field-label">{f.label}{f.required && <span className="req">*</span>}</span>
              {f.type === 'select' && <Select value={values[f.key]} onChange={set(f.key)} options={f.options} />}
              {f.type === 'textarea' && <textarea className="input letter-area" rows={3} maxLength={1500} value={values[f.key]} onChange={e => set(f.key)(e.target.value)} placeholder={f.placeholder || ''} />}
              {f.type === 'text' && <input className="input" maxLength={160} value={values[f.key]} onChange={e => set(f.key)(e.target.value)} placeholder={f.placeholder || ''} />}
              {f.type === 'number' && <input className="input" type="number" min="0" value={values[f.key]} onChange={e => set(f.key)(e.target.value)} />}
              {f.type === 'date' && <input className="input" type="date" value={values[f.key]} onChange={e => set(f.key)(e.target.value)} />}
              {f.help && <small className="calc-help-text">{f.help}</small>}
            </div>
          ))}
          <div className="calc-note"><Info size={22} fill="#13335b" color="#fff" /><p>{spec.note}</p></div>
          {error && <div className="calc-error" role="alert"><AlertTriangle size={18} /><p>{error}</p></div>}
          <div className="calc-btns">
            <button className="btn btn-orange btn-xl calc-go" onClick={make} disabled={busy === 'make'}>{busy === 'make' ? <Loader2 size={22} className="spin" /> : <Mail size={22} />} Create letter</button>
          </div>
        </section>

        <section className="card card-pad letter-out">
          {letter ? (
            <>
              <div className="letter-actions">
                <button className="btn btn-outline" onClick={copy}><Copy size={17} /> Copy</button>
                <button className="btn btn-outline" onClick={download} disabled={busy === 'pdf'}>{busy === 'pdf' ? <Loader2 size={17} className="spin" /> : <Download size={17} />} Download PDF</button>
                <button className="btn btn-outline" onClick={save} disabled={busy === 'save' || !!saved}>{busy === 'save' ? <Loader2 size={17} className="spin" /> : <Bookmark size={17} fill={saved ? 'currentColor' : 'none'} />} {saved ? 'Saved to Vault' : 'Save to Vault'}</button>
              </div>
              <pre className="letter-paper">{letter.text}</pre>
              <p className="guide-note"><Info size={15} /> Read it carefully, fix any detail, and keep a copy and proof of delivery. If you edit the facts above, press Create letter again.{saved && <> <Link className="link small" to={`/vault/item/${saved}`}>Open in Vault</Link></>}</p>
            </>
          ) : (
            <div className="calc-empty"><Mail size={44} strokeWidth={1.4} /><b>No letter yet</b><p>Fill in the form and press Create letter. Nothing is sent anywhere: the letter is only shown here.</p></div>
          )}
        </section>
      </div>
    </div>
  )
}
