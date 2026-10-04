import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, CheckCircle2, CloudUpload, FileSignature, FileText, FolderOpen, Globe, House, Info, Lock,
  Loader2, Scale, ShieldCheck, Sparkles, Trash2, X, FileWarning
} from 'lucide-react'
import { Breadcrumb, Checkbox, Select } from '../components/common'
import { FileIcon } from '../components/Icons'
import { useUI } from '../components/UIContext'
import { USE_MOCKS } from '../api/config'
import { ACCEPTED_TYPES, MAX_UPLOAD_BYTES, documentService } from '../api/services/documentService'
import { MOCK_UPLOAD_QUEUE } from '../api/mocks/documents'
import { formatBytes } from '../utils/format'

const KINDS = [
  { icon: FileText, tone: 'blue', title: 'Contracts', text: 'Rental, employment, service agreements' },
  { icon: FileWarning, tone: 'orange', title: 'Legal notices', text: 'Notices, summons, demand letters' },
  { icon: Scale, tone: 'purple', title: 'Court documents', text: 'Judgments, orders, petitions' },
  { icon: FileSignature, tone: 'green', title: 'Agreements', text: 'NDAs, partnership, settlement agreements' },
  { icon: House, tone: 'teal', title: 'Property documents', text: 'Sale deeds, ownership records' },
]

const extOf = name => {
  const e = name.split('.').pop().toLowerCase()
  return e === 'doc' ? 'docx' : e === 'jpeg' ? 'jpg' : e
}

export default function Upload() {
  const navigate = useNavigate()
  const { toast } = useUI()
  const inputRef = useRef(null)
  const controllers = useRef({})
  const [drag, setDrag] = useState(false)
  // Queue item: { key, name, sizeBytes, type, progress, status: 'uploading'|'done'|'error', documentId, error }
  const [queue, setQueue] = useState(USE_MOCKS ? MOCK_UPLOAD_QUEUE : [])
  const [lang, setLang] = useState('auto')
  const [depth, setDepth] = useState('quick')
  const [save, setSave] = useState(true)
  const [starting, setStarting] = useState(false)

  const update = (key, patch) => setQueue(q => q.map(f => (f.key === key ? { ...f, ...patch } : f)))

  const startUpload = (key, file, startAt = 0) => {
    const ctrl = new AbortController()
    controllers.current[key] = ctrl
    documentService.upload(file, { onProgress: p => update(key, { progress: p }), signal: ctrl.signal, startAt })
      .then(doc => update(key, { progress: 100, status: 'done', documentId: doc.id }))
      .catch(e => { if (e.name !== 'AbortError') update(key, { status: 'error', error: e.message || 'Upload failed' }) })
      .finally(() => { delete controllers.current[key] })
  }

  // Mock mode: continue the design's half-finished demo upload.
  useEffect(() => {
    const demo = queue.find(f => f.key === 'demo2' && f.status === 'uploading')
    if (demo) startUpload(demo.key, { name: demo.name, size: demo.sizeBytes }, demo.progress)
    const ctrls = controllers.current
    return () => Object.values(ctrls).forEach(c => c.abort())
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const addFiles = files => {
    Array.from(files).forEach(f => {
      const type = extOf(f.name)
      if (!ACCEPTED_TYPES.includes(type)) return toast(`${f.name}: unsupported format`, 'info')
      if (f.size > MAX_UPLOAD_BYTES) return toast(`${f.name} is larger than 10 MB`, 'info')
      const key = `${Date.now()}_${Math.random()}`
      setQueue(q => [...q, { key, name: f.name, sizeBytes: f.size, type, progress: 0, status: 'uploading', documentId: null }])
      startUpload(key, f)
    })
  }

  const removeItem = f => {
    controllers.current[f.key]?.abort()
    setQueue(q => q.filter(x => x.key !== f.key))
    if (f.documentId && f.status === 'done') documentService.remove(f.documentId).catch(() => {})
  }
  const clearAll = () => queue.forEach(removeItem)

  const analyse = async () => {
    const ready = queue.filter(f => f.status === 'done')
    if (!queue.length) return toast('Add a document to analyse first', 'info')
    if (queue.some(f => f.status === 'uploading')) return toast('Please wait for uploads to finish', 'info')
    if (!ready.length) return toast('No uploaded documents to analyse', 'info')
    setStarting(true)
    try {
      const job = await documentService.startAnalysis({ documentIds: ready.map(f => f.documentId), language: lang, depth, saveToVault: save })
      navigate(`/documents/analysis/${job.id}`)
    } catch (e) {
      toast(e.message || 'Could not start the analysis', 'info')
      setStarting(false)
    }
  }

  return (
    <div className="upload">
      <div className="page-head">
        <div>
          <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Documents', to: '/documents' }, { label: 'Upload' }]} />
          <h1 className="page-title">Upload a Legal Document</h1>
          <p className="page-sub">Upload a document to identify important clauses, obligations, risks and deadlines.</p>
        </div>
        <div className="secure-note">
          <ShieldCheck size={40} fill="#13335b" color="#fff" strokeWidth={1.6} />
          <div><b>Your documents are encrypted and kept private.</b><span>We never share your files with third parties.</span></div>
        </div>
      </div>

      <div className="upload-grid">
        <div className="upload-left">
          <section className="card upload-card">
            <div className={`dropzone ${drag ? 'drag' : ''}`}
              onDragOver={e => { e.preventDefault(); setDrag(true) }}
              onDragLeave={() => setDrag(false)}
              onDrop={e => { e.preventDefault(); setDrag(false); addFiles(e.dataTransfer.files) }}>
              <CloudUpload size={64} strokeWidth={1.4} className="dz-icon" />
              <h3>Drag and drop your document here</h3>
              <span className="dz-or">or</span>
              <input ref={inputRef} type="file" hidden multiple accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" onChange={e => { addFiles(e.target.files); e.target.value = '' }} />
              <button className="btn btn-orange btn-lg dz-browse" onClick={() => inputRef.current.click()}><FolderOpen size={20} /> Browse Files</button>
              <p className="dz-formats">Supported formats: PDF, DOCX, JPG, PNG (Max size: 10 MB)</p>
              <div className="dz-trust">
                <div><span><Lock size={18} /></span><p><b>Secure Upload</b>End-to-end encryption</p></div>
                <div><span><ShieldCheck size={18} /></span><p><b>Your Data Stays Private</b>Only you can access your files</p></div>
                <div><span><FileText size={18} /></span><p><b>Used for Analysis Only</b>Your files are not shared</p></div>
              </div>
            </div>
          </section>

          <section className="card card-pad queue-card">
            <div className="card-head">
              <h2 className="card-title">Upload Queue <span className="queue-count">({queue.length} files)</span></h2>
              {queue.length > 0 && <button className="link small" onClick={clearAll}><Trash2 size={16} /> Clear All</button>}
            </div>
            <div className="queue">
              {queue.map(f => (
                <div key={f.key} className="queue-row">
                  <FileIcon type={f.type} size={36} />
                  <div className="queue-name"><b>{f.name}</b><span>{formatBytes(f.sizeBytes)}</span></div>
                  <div className="progress queue-bar"><span style={{ width: `${f.progress}%`, background: f.status === 'error' ? '#dc2626' : f.status === 'done' ? '#22a45a' : '#1d5fd6' }} /></div>
                  <span className={`queue-status ${f.status === 'done' ? 'done' : ''} ${f.status === 'error' ? 'failed' : ''}`}>
                    {f.status === 'done' ? <><CheckCircle2 size={16} /> Upload complete</> : f.status === 'error' ? (f.error || 'Upload failed') : `Uploading... ${f.progress}%`}
                  </span>
                  <button className="icon-btn-plain queue-x" onClick={() => removeItem(f)} aria-label={`Remove ${f.name}`}><X size={18} /></button>
                </div>
              ))}
              {!queue.length && <p className="queue-empty">No files yet - drop a document above to get started.</p>}
            </div>
            <div className="need-help">
              <Info size={24} fill="#1d4ed8" color="#fff" />
              <div><b>Need help?</b><span>Make sure your document is not password protected and contains readable text.</span></div>
              <button className="link small" onClick={() => toast('Upload guidelines: PDF/DOCX/JPG/PNG up to 10 MB, unprotected, clearly readable.', 'info')}>View upload guidelines <ArrowRight size={15} /></button>
            </div>
          </section>
        </div>

        <div className="upload-right">
          <section className="card card-pad">
            <h2 className="card-title">What can be analysed?</h2>
            <p className="muted small upload-sub">LegalMate can extract key information from:</p>
            <div className="kind-grid">
              {KINDS.map(k => (
                <div key={k.title} className="kind">
                  <span className={`icon-tile tile-${k.tone} tile-md`}><k.icon /></span>
                  <div><b>{k.title}</b><span>{k.text}</span></div>
                </div>
              ))}
            </div>
          </section>

          <section className="card card-pad">
            <h2 className="card-title">Analysis Options</h2>
            <p className="opt-label">Analysis language</p>
            <Select value={lang} onChange={setLang} icon={Globe} options={[
              { value: 'auto', label: 'English (Auto-detect if mixed)' },
              { value: 'en', label: 'English' },
              { value: 'ur', label: 'Urdu (اردو)' },
            ]} />
            <p className="opt-label">Analysis depth</p>
            <div className="depth-grid">
              {[
                { v: 'quick', t: 'Quick Analysis', d: 'Summary and key points (1–2 minutes)' },
                { v: 'detailed', t: 'Detailed Analysis', d: 'In-depth review with clause analysis and risk assessment (3–5 minutes)' },
              ].map(o => (
                <button key={o.v} className={`depth ${depth === o.v ? 'active' : ''}`} onClick={() => setDepth(o.v)}>
                  <span className="radio" />
                  <div><b>{o.t}</b><span>{o.d}</span></div>
                </button>
              ))}
            </div>
            <div className="save-vault">
              <Checkbox checked={save} onChange={setSave} tone="orange"><b>Save original file to Legal Vault</b></Checkbox>
              <span>Keep a secure copy of your document in your vault.</span>
            </div>
            <button className="btn btn-orange btn-xl btn-block analyse-btn" onClick={analyse} disabled={starting}>
              {starting ? <Loader2 size={20} className="spin" /> : <Sparkles size={20} />} {starting ? 'Starting analysis…' : 'Analyse Document'} {!starting && <ArrowRight size={20} />}
            </button>
          </section>
        </div>
      </div>
    </div>
  )
}
