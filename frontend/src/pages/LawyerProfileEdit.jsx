import { useEffect, useState } from 'react'
import { CalendarClock, Loader2, Monitor, Phone, Plus, Save, ShieldCheck, ShieldQuestion, ShieldX, X, Users2 } from 'lucide-react'
import { Breadcrumb, Select } from '../components/common'
import { useUI } from '../components/UIContext'
import { PageSkeleton, ErrorState } from '../components/States'
import { useAuth } from '../context/AuthContext'
import { useQuery } from '../hooks/useApi'
import { lawyerService } from '../api/services/lawyerService'
import { pkr } from '../utils/format'

const CITIES = ['Islamabad', 'Rawalpindi', 'Lahore', 'Karachi']
const MODE_ICON = { video: Monitor, phone: Phone, in_person: Users2 }
const MODE_LABEL = { video: 'Video call', phone: 'Phone call', in_person: 'In-person' }
const ALL_MODES = ['video', 'phone', 'in_person']
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const VERIFIED = {
  verified: { label: 'Verified', tone: 'green', icon: ShieldCheck },
  pending: { label: 'Verification pending', tone: 'amber', icon: ShieldQuestion },
  rejected: { label: 'Rejected', tone: 'red', icon: ShieldX },
}

export default function LawyerProfileEdit() {
  const { user } = useAuth()
  const { toast } = useUI()
  const query = useQuery(signal => lawyerService.getLawyer(user.lawyerId, signal), [user.lawyerId])
  const [form, setForm] = useState(null)
  const [newSlot, setNewSlot] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (query.data && !form) {
      setForm({
        bio: query.data.bio, fee: query.data.fee, city: query.data.city,
        specializations: query.data.specializations.join(', '), languages: query.data.languages.join(', '), modes: query.data.modes,
        availableDays: query.data.availableDays || [], slotTimes: query.data.slotTimes || [],
      })
    }
  }, [query.data, form])

  const toggleMode = m => setForm(f => ({ ...f, modes: f.modes.includes(m) ? f.modes.filter(x => x !== m) : [...f.modes, m] }))
  const toggleDay = d => setForm(f => ({ ...f, availableDays: f.availableDays.includes(d) ? f.availableDays.filter(x => x !== d) : [...f.availableDays, d].sort() }))
  const addSlot = () => {
    const t = newSlot.trim()
    if (!t || form.slotTimes.includes(t)) return
    setForm(f => ({ ...f, slotTimes: [...f.slotTimes, t] }))
    setNewSlot('')
  }
  const removeSlot = t => setForm(f => ({ ...f, slotTimes: f.slotTimes.filter(x => x !== t) }))

  const submit = async e => {
    e.preventDefault()
    setBusy(true)
    try {
      await lawyerService.updateProfile(user.lawyerId, {
        bio: form.bio, fee: Number(form.fee), city: form.city, modes: form.modes,
        specializations: form.specializations.split(',').map(s => s.trim()).filter(Boolean),
        languages: form.languages.split(',').map(s => s.trim()).filter(Boolean),
        availableDays: form.availableDays, slotTimes: form.slotTimes,
      })
      toast('Your profile has been updated.')
    } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }

  if (!query.data || !form) {
    if (query.loading) return <PageSkeleton cards={0} rows={1} />
    return <ErrorState error={query.error} onRetry={query.reload} />
  }
  const s = VERIFIED[query.data.verified] || VERIFIED.pending

  return (
    <div className="lp">
      <Breadcrumb items={[{ label: 'Lawyer Portal', to: '/lawyer' }, { label: 'My Profile' }]} />
      <h1 className="page-title">My Profile</h1>
      <p className="page-sub">This is what clients see when they search for a lawyer on LegalMate.</p>

      <div className="lp-profile-grid">
        <form className="card card-pad lp-form" onSubmit={submit}>
          <div className="lp-form-row">
            <label className="field"><span className="field-label">Consultation fee (PKR, per 30 min)</span><input className="input" type="number" min="0" required value={form.fee} onChange={e => setForm(f => ({ ...f, fee: e.target.value }))} /></label>
            <label className="field"><span className="field-label">City</span><Select value={form.city} onChange={v => setForm(f => ({ ...f, city: v }))} options={CITIES} /></label>
          </div>

          <label className="field">
            <span className="field-label">Specializations</span>
            <input className="input" required value={form.specializations} onChange={e => setForm(f => ({ ...f, specializations: e.target.value }))} placeholder="e.g. Contract Law, Corporate Law" />
            <span className="muted small">Separate with commas.</span>
          </label>

          <label className="field">
            <span className="field-label">Languages</span>
            <input className="input" required value={form.languages} onChange={e => setForm(f => ({ ...f, languages: e.target.value }))} placeholder="e.g. Urdu, English" />
          </label>

          <label className="field">
            <span className="field-label">About / Bio</span>
            <textarea className="textarea" rows={5} required value={form.bio} onChange={e => setForm(f => ({ ...f, bio: e.target.value }))} />
          </label>

          <div className="field">
            <span className="field-label">Consultation modes</span>
            <div className="mk-modes">
              {ALL_MODES.map(m => { const Icon = MODE_ICON[m]; return <button type="button" key={m} className={`pill pill-gray mk-mode mk-mode-btn ${form.modes.includes(m) ? 'active' : ''}`} onClick={() => toggleMode(m)}><Icon size={14} /> {MODE_LABEL[m]}</button> })}
            </div>
          </div>

          <p className="lp-fee-preview">Clients will see: <b>{pkr(Number(form.fee) || 0)}</b> / 30 min</p>

          <button className="btn btn-orange btn-lg lp-save-btn" disabled={busy}>{busy ? <Loader2 size={18} className="spin" /> : <Save size={18} />} Save Changes</button>
        </form>

        <aside className="lp-sidebar">
          <div className="card card-pad lp-status">
            <span className={`icon-tile tile-${s.tone} tile-md`}><s.icon /></span>
            <div>
              <span className={`pill pill-${s.tone}`}>{s.label}</span>
              <p className="small muted">Verification is reviewed by the LegalMate team and can't be changed from here.</p>
            </div>
          </div>

          <div className="card card-pad lp-avail">
            <h3 className="card-title lp-avail-title"><CalendarClock size={18} /> Availability</h3>
            <p className="small muted lp-avail-sub">Clients can only book slots on the days and times you set here.</p>

            <span className="field-label lp-avail-label">Available days</span>
            <div className="lp-days">
              {WEEKDAYS.map((w, i) => (
                <button type="button" key={w} className={`lp-day ${form.availableDays.includes(i) ? 'active' : ''}`} onClick={() => toggleDay(i)}>{w}</button>
              ))}
            </div>

            <span className="field-label lp-avail-label">Time slots</span>
            <div className="lp-slots">
              {form.slotTimes.map(t => (
                <span key={t} className="pill pill-orange lp-slot">{t}<button type="button" onClick={() => removeSlot(t)} aria-label={`Remove ${t}`}><X size={12} /></button></span>
              ))}
              {!form.slotTimes.length && <p className="small muted">No time slots yet.</p>}
            </div>
            <div className="lp-add-slot">
              <input className="input" value={newSlot} onChange={e => setNewSlot(e.target.value)} placeholder="e.g. 4:00 PM" onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addSlot())} />
              <button type="button" className="btn btn-outline btn-sm" onClick={addSlot}><Plus size={14} /> Add</button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
