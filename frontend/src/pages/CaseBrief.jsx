import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  CalendarDays, CheckCircle2, Circle, CloudUpload, FileText, Lightbulb, Save, Sparkles, UserRound, X,
  ClipboardList, Loader2
} from 'lucide-react'
import { Breadcrumb, Select } from '../components/common'
import { FileIcon } from '../components/Icons'
import { useUI } from '../components/UIContext'
import { PageSkeleton, QueryBoundary } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { USE_MOCKS } from '../api/config'
import { caseBriefService } from '../api/services/caseBriefService'
import { COURTS } from '../api/mocks/briefs'
import { formatBytes } from '../utils/format'

const TYPES = [
  { v: 'summary', icon: CheckCircle2, t: 'Summary', d: 'Concise overview (1–2 pages)' },
  { v: 'lawyer', icon: FileText, t: 'Lawyer-ready', d: 'Detailed and structured (3–5 pages)' },
  { v: 'personal', icon: UserRound, t: 'Personal reference', d: 'Simple and easy to understand' },
]

function DateField({ label, value, onChange }) {
  const ref = useRef(null)
  const display = value ? new Date(value).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Select date'
  return (
    <button type="button" className="cb-date" onClick={() => ref.current?.showPicker?.() || ref.current?.focus()}>
      <span><small>{label}</small><b>{display}</b></span>
      <CalendarDays size={20} />
      <input ref={ref} type="date" value={value} onChange={e => onChange(e.target.value)} tabIndex={-1} aria-label={label} />
    </button>
  )
}

export default function CaseBrief() {
  const [params] = useSearchParams()
  const fromMessage = params.get('fromMessage') || undefined
  const fromAnalysis = params.get('fromAnalysis') || undefined
  const query = useQuery(signal => caseBriefService.getDraft({ fromMessage, fromAnalysis }, signal), [fromMessage, fromAnalysis])
  return (
    <QueryBoundary query={query} skeleton={<PageSkeleton cards={2} rows={1} />}>
      {draft => <BriefForm key={draft.id} draft={draft} />}
    </QueryBoundary>
  )
}

// Form state <-> API payload
const fromDraft = d => ({
  title: d.title || '', court: d.court || '', number: d.caseNumber || '', parties: d.parties || '',
  filing: d.filingDate || '', hearing: d.nextHearingDate || '', facts: d.facts || '', issues: d.issues || '',
  type: d.briefType || 'summary',
})
const toPayload = (f, typeChosen, files) => ({
  title: f.title, court: f.court, caseNumber: f.number, parties: f.parties, filingDate: f.filing || null,
  nextHearingDate: f.hearing || null, facts: f.facts, issues: f.issues, briefType: typeChosen ? f.type : null,
  attachmentIds: files.filter(x => !x.uploading).map(x => x.id),
})

function BriefForm({ draft }) {
  const navigate = useNavigate()
  const { toast } = useUI()
  const fileRef = useRef(null)
  const [f, setF] = useState(() => fromDraft(draft))
  const [files, setFiles] = useState(draft.attachments || [])
  const [typeChosen, setTypeChosen] = useState(!!draft.briefType)
  // In the design the saved draft still needs the attachment confirmed (5 of 7 checklist); with a backend attachments count directly.
  const [attachTouched, setAttachTouched] = useState(!USE_MOCKS)
  const [savedAt, setSavedAt] = useState(draft.savedAt)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [, tick] = useState(0)
  const [mode, setMode] = useState('Preview')
  const [format, setFormat] = useState('A4 (PDF Style)')
  const [generating, setGenerating] = useState(false)
  const set = k => v => { setF(p => ({ ...p, [k]: v })); setDirty(true) }
  const savedAgo = savedAt ? Math.max(0, Math.floor((Date.now() - new Date(savedAt).getTime()) / 60000)) : null

  const saveNow = async (silent = false) => {
    setSaving(true)
    try {
      const r = await caseBriefService.saveDraft(toPayload(f, typeChosen, files))
      setSavedAt(r.savedAt)
      setDirty(false)
      if (!silent) toast('Draft saved')
    } catch (e) { if (!silent) toast(e.message, 'info') } finally { setSaving(false) }
  }

  // Autosave 1.5s after the last change.
  useEffect(() => {
    if (!dirty) return undefined
    const t = setTimeout(() => saveNow(true), 1500)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [f, files, typeChosen, dirty])

  // Refresh the "Last saved: n minutes ago" label.
  useEffect(() => {
    const t = setInterval(() => tick(x => x + 1), 30000)
    return () => clearInterval(t)
  }, [])

  const addFiles = list => {
    setAttachTouched(true)
    Array.from(list).forEach(async file => {
      const temp = { id: `tmp_${Date.now()}_${file.name}`, name: file.name, sizeBytes: file.size, uploading: true }
      setFiles(fs => [...fs, temp])
      try {
        const att = await caseBriefService.uploadAttachment(file)
        setFiles(fs => fs.map(x => (x.id === temp.id ? att : x)))
        setDirty(true)
      } catch (e) {
        setFiles(fs => fs.filter(x => x.id !== temp.id))
        toast(`${file.name}: ${e.message || 'upload failed'}`, 'info')
      }
    })
  }
  const removeFile = x => {
    setFiles(fs => fs.filter(y => y.id !== x.id))
    setDirty(true)
    if (!x.uploading) caseBriefService.removeAttachment(x.id).catch(() => {})
  }

  const checklist = [
    { label: 'Case title added', ok: !!f.title.trim() },
    { label: 'Court / jurisdiction selected', ok: !!f.court },
    { label: 'Parties involved added', ok: !!f.parties.trim() },
    { label: 'Case facts provided', ok: f.facts.trim().length > 20 },
    { label: 'Legal issues provided', ok: f.issues.trim().length > 10 },
    { label: 'At least one document attached', ok: files.length > 0 && attachTouched },
    { label: 'Select brief type', ok: typeChosen },
  ]
  const done = checklist.filter(c => c.ok).length

  const generate = async () => {
    const missing = checklist.slice(0, 5).find(c => !c.ok)
    if (missing) return toast(`Please complete: ${missing.label.toLowerCase()}`, 'info')
    if (files.some(x => x.uploading)) return toast('Please wait for attachments to finish uploading', 'info')
    setGenerating(true)
    try {
      const res = await caseBriefService.generate({ ...toPayload(f, typeChosen, files), briefType: f.type, format })
      navigate(`/case-briefs/${res.id}`)
    } catch (e) {
      toast(e.message || 'Could not generate the brief', 'info')
      setGenerating(false)
    }
  }

  return (
    <div className="cb">
      <div className="page-head">
        <div>
          <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Case Briefs', to: '/case-briefs' }, { label: 'New Brief' }]} />
          <h1 className="page-title">Create AI Case Brief</h1>
          <p className="page-sub">Turn your case details into a structured, professional brief using AI.</p>
        </div>
        <div className="cb-head-actions">
          {savedAgo !== null && <span className="cb-saved">Last saved: {savedAgo === 0 ? 'just now' : `${savedAgo} minute${savedAgo > 1 ? 's' : ''} ago`}</span>}
          {saving || dirty
            ? <span className="cb-saved"><Loader2 size={15} className="spin" style={{ display: 'inline', verticalAlign: -3 }} /> Saving…</span>
            : <span className="cb-draft"><CheckCircle2 size={17} fill="#22a45a" color="#fff" /> Draft saved</span>}
          <button className="btn btn-outline btn-lg cb-save" onClick={() => saveNow(false)} disabled={saving}><Save size={18} /> Save Draft</button>
          <button className="btn btn-orange btn-lg cb-gen" onClick={generate} disabled={generating}>
            {generating ? <Loader2 size={19} className="spin" /> : <Sparkles size={19} />} {generating ? 'Generating…' : 'Generate Brief'}
          </button>
        </div>
      </div>

      <div className="cb-grid">
        <section className="card cb-form">
          <div className="card-head"><h2 className="cb-h2">Case Details</h2><span className="cb-req">Fields marked with <i>*</i> are required</span></div>

          <div className="cb-row3">
            <label className="field"><span className="field-label">Case Title<span className="req">*</span></span><input className="input" value={f.title} onChange={e => set('title')(e.target.value)} /></label>
            <div className="field"><span className="field-label">Court / Jurisdiction<span className="req">*</span></span><Select value={f.court} onChange={set('court')} options={COURTS} /></div>
            <label className="field"><span className="field-label">Case Number</span><input className="input" value={f.number} onChange={e => set('number')(e.target.value)} /></label>
          </div>

          <label className="field"><span className="field-label">Parties Involved<span className="req">*</span></span><input className="input cb-parties" value={f.parties} onChange={e => set('parties')(e.target.value)} /></label>

          <div className="field">
            <span className="field-label">Key Dates</span>
            <div className="cb-dates">
              <DateField label="Filing Date" value={f.filing} onChange={set('filing')} />
              <DateField label="Next Hearing Date" value={f.hearing} onChange={set('hearing')} />
            </div>
          </div>

          <label className="field">
            <span className="field-label">Case Facts<span className="req">*</span></span>
            <div className="cb-ta"><textarea className="textarea" rows={3} maxLength={2000} value={f.facts} onChange={e => set('facts')(e.target.value)} /><span>{f.facts.length}/2000</span></div>
          </label>
          <label className="field">
            <span className="field-label">Legal Issues<span className="req">*</span></span>
            <div className="cb-ta"><textarea className="textarea" rows={2} maxLength={1000} value={f.issues} onChange={e => set('issues')(e.target.value)} /><span>{f.issues.length}/1000</span></div>
          </label>

          <div className="field">
            <span className="field-label">Attach Supporting Documents</span>
            <div className="cb-attach">
              <button type="button" className="cb-drop" onClick={() => fileRef.current.click()}
                onDragOver={e => e.preventDefault()}
                onDrop={e => { e.preventDefault(); addFiles(e.dataTransfer.files) }}>
                <CloudUpload size={34} strokeWidth={1.5} />
                <span><b>Drag and drop files here or <u>browse</u></b><small>PDF, DOCX, JPG, PNG (Max 10 MB each)</small></span>
              </button>
              <input ref={fileRef} type="file" hidden multiple onChange={e => { addFiles(e.target.files); e.target.value = '' }} />
              <div className="cb-files">
                {files.map(x => (
                  <div key={x.id} className="cb-file">
                    <FileIcon type={x.name.split('.').pop().toLowerCase() === 'docx' ? 'docx' : 'pdf'} size={32} />
                    <span><b>{x.name}</b><small>{x.uploading ? 'Uploading…' : formatBytes(x.sizeBytes)}</small></span>
                    <button onClick={() => removeFile(x)} aria-label={`Remove ${x.name}`}>{x.uploading ? <Loader2 size={18} className="spin" /> : <X size={18} />}</button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="field">
            <span className="field-label">Brief Type<span className="req">*</span></span>
            <div className="cb-types">
              {TYPES.map(t => (
                <button key={t.v} type="button" className={`cb-type ${f.type === t.v && typeChosen ? 'active' : ''} ${f.type === t.v && !typeChosen ? 'pre' : ''}`} onClick={() => { set('type')(t.v); setTypeChosen(true); setDirty(true) }}>
                  {f.type === t.v ? <CheckCircle2 size={26} className="cb-type-check" /> : <t.icon size={24} />}
                  <span><b>{t.t}</b><small>{t.d}</small></span>
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="card cb-preview">
          <div className="cb-prev-head">
            <div><h2 className="cb-h2">Brief Preview</h2><p>Your AI-generated case brief will appear here.</p></div>
            <div className="cb-prev-tools">
              <div className="seg cb-seg">{['Preview', 'Edit'].map(m => <button key={m} className={mode === m ? 'active' : ''} onClick={() => setMode(m)}>{m}</button>)}</div>
              <Select compact value={format} onChange={setFormat} options={['A4 (PDF Style)', 'Letter', 'Plain text']} className="cb-format" />
            </div>
          </div>
          <div className="cb-prev-body">
            {mode === 'Preview' ? (
              <>
                <img src="/assets/img/case-brief-illustration.png" alt="" className="cb-illus" />
                <h3>Ready to Generate Your Case Brief?</h3>
                <p className="cb-prev-text">Fill in the case details on the left and click generate to create<br />a structured legal brief using AI.</p>
                <div className="cb-check">
                  <div className="cb-check-head"><ClipboardList size={20} /><b>Completion Checklist</b><span>{done} of {checklist.length} completed</span></div>
                  <ul>
                    {checklist.map(c => <li key={c.label} className={c.ok ? 'ok' : ''}>{c.ok ? <CheckCircle2 size={19} /> : <Circle size={19} />}{c.label}</li>)}
                  </ul>
                </div>
                <div className="cb-tip">
                  <Lightbulb size={24} />
                  <div><b>Tip</b><p>Attach relevant documents (FIR, petitions, orders, etc.) to get a more accurate and detailed brief. You can always edit the generated content.</p></div>
                </div>
                <p className="cb-quote">“Good preparation today leads to a stronger tomorrow.”<span>- LegalMate</span></p>
              </>
            ) : (
              <div className="cb-edit">
                <h3>{f.title}</h3>
                <p className="muted small">{f.number} • {f.court}</p>
                <h4>Parties</h4><p>{f.parties}</p>
                <h4>Facts</h4><p>{f.facts}</p>
                <h4>Issues</h4>{f.issues.split('\n').map((l, i) => <p key={i}>{i + 1}. {l}</p>)}
                <p className="muted small cb-edit-note">Edit the fields on the left - this draft outline updates as you type.</p>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
