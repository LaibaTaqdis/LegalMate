import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Loader2, Monitor, Phone, Users2 } from 'lucide-react'
import { Logo, Select } from '../components/common'
import { useUI } from '../components/UIContext'
import { useAuth } from '../context/AuthContext'
import { lawyerService } from '../api/services/lawyerService'

const CITIES = ['Islamabad', 'Rawalpindi', 'Lahore', 'Karachi']
const MODE_ICON = { video: Monitor, phone: Phone, in_person: Users2 }
const MODE_LABEL = { video: 'Video call', phone: 'Phone call', in_person: 'In-person' }
const ALL_MODES = ['video', 'phone', 'in_person']

export default function LawyerApply() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const { toast } = useUI()
  const [form, setForm] = useState({
    name: '', email: '', phone: '', city: 'Islamabad', fee: '', experienceYears: '',
    specializations: '', languages: '', modes: ['video'], bio: '',
  })
  const [busy, setBusy] = useState(false)
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))
  const toggleMode = m => setForm(f => ({ ...f, modes: f.modes.includes(m) ? f.modes.filter(x => x !== m) : [...f.modes, m] }))

  const submit = async e => {
    e.preventDefault()
    setBusy(true)
    try {
      await lawyerService.apply({
        ...form,
        specializations: form.specializations.split(',').map(s => s.trim()).filter(Boolean),
        languages: form.languages.split(',').map(s => s.trim()).filter(Boolean),
      })
      await login({ identifier: form.email, password: '', remember: true, role: 'lawyer' })
      toast("Application submitted. We'll review it shortly.")
      navigate('/lawyer', { replace: true })
    } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }

  return (
    <div className="apply">
      <div className="apply-card">
        <Logo variant="dark" to="/" />
        <h1 className="apply-title">Apply to join as a lawyer</h1>
        <p className="apply-sub">Tell us about your practice. Your profile goes live on LegalMate once the LegalMate team reviews and approves your application.</p>

        <form className="apply-form" onSubmit={submit}>
          <div className="apply-row">
            <label className="field"><span className="field-label">Full name</span><input className="input" required value={form.name} onChange={set('name')} placeholder="e.g. Ayesha Malik" /></label>
            <label className="field"><span className="field-label">Email</span><input className="input" type="email" required value={form.email} onChange={set('email')} placeholder="name@example.com" /></label>
          </div>
          <div className="apply-row">
            <label className="field"><span className="field-label">Phone number</span><input className="input" required value={form.phone} onChange={set('phone')} placeholder="+92 3XX XXXXXXX" /></label>
            <label className="field"><span className="field-label">City</span><Select value={form.city} onChange={v => setForm(f => ({ ...f, city: v }))} options={CITIES} /></label>
          </div>
          <div className="apply-row">
            <label className="field"><span className="field-label">Consultation fee (PKR, per 30 min)</span><input className="input" type="number" min="0" required value={form.fee} onChange={set('fee')} placeholder="e.g. 3000" /></label>
            <label className="field"><span className="field-label">Years of experience</span><input className="input" type="number" min="0" required value={form.experienceYears} onChange={set('experienceYears')} placeholder="e.g. 5" /></label>
          </div>
          <label className="field"><span className="field-label">Specializations</span><input className="input" required value={form.specializations} onChange={set('specializations')} placeholder="e.g. Contract Law, Corporate Law" /><span className="muted small">Separate with commas.</span></label>
          <label className="field"><span className="field-label">Languages</span><input className="input" required value={form.languages} onChange={set('languages')} placeholder="e.g. Urdu, English" /></label>
          <label className="field"><span className="field-label">About / Bio</span><textarea className="textarea" rows={4} required value={form.bio} onChange={set('bio')} placeholder="Tell clients about your practice and experience." /></label>

          <div className="field">
            <span className="field-label">Consultation modes</span>
            <div className="mk-modes">
              {ALL_MODES.map(m => { const Icon = MODE_ICON[m]; return <button type="button" key={m} className={`pill pill-gray mk-mode mk-mode-btn ${form.modes.includes(m) ? 'active' : ''}`} onClick={() => toggleMode(m)}><Icon size={14} /> {MODE_LABEL[m]}</button> })}
            </div>
          </div>

          <button className="btn btn-orange btn-lg btn-block apply-submit" disabled={busy}>{busy ? <Loader2 size={18} className="spin" /> : null} Submit Application {!busy && <ArrowRight size={18} />}</button>
          <p className="auth-switch">Already applied? <Link to="/login">Sign in</Link></p>
        </form>
      </div>
    </div>
  )
}
