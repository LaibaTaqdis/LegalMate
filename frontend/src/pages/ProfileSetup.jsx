import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AlertCircle, ArrowRight, Loader2, MapPin, ShieldCheck } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { ErrorState, Skeleton } from '../components/States'
import { useUI } from '../components/UIContext'
import { useQuery } from '../hooks/useApi'
import { PROFILE_OPTIONS as OPT, profileService } from '../api/services/profileService'

const LANGS = [{ v: 'en', label: 'English' }, { v: 'ur', label: 'اردو (Urdu)' }, { v: 'both', label: 'Both' }]

/** One question with tappable choices. `multi` lets several be selected. */
function Choice({ title, hint, options, value, onChange, multi = false, full = false }) {
  const isOn = o => (multi ? value.includes(o.v ?? o) : value === (o.v ?? o))
  const toggle = o => {
    const v = o.v ?? o
    onChange(multi ? (value.includes(v) ? value.filter(x => x !== v) : [...value, v]) : (value === v ? null : v))
  }
  return (
    <div className={`field ps-q ${full ? 'ps-full' : ''}`}>
      <span className="field-label">{title}{hint && <i className="su-opt"> {hint}</i>}</span>
      <div className="ps-chips" role={multi ? 'group' : 'radiogroup'} aria-label={title}>
        {options.map(o => (
          <button type="button" key={o.v ?? o} role={multi ? 'checkbox' : 'radio'} aria-checked={isOn(o)}
            className={`ps-chip ${isOn(o) ? 'on' : ''}`} onClick={() => toggle(o)}>{o.label ?? o}</button>
        ))}
      </div>
    </div>
  )
}

export default function ProfileSetup() {
  const navigate = useNavigate()
  const fromSettings = useSearchParams()[0].get('from') === 'settings'          // opened from Settings: go back there, not to the chat
  const { toast } = useUI()
  const q = useQuery(signal => profileService.get(signal), [])
  const [p, setP] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { if (q.data) setP({ ...q.data, roles: q.data.roles || [], interests: q.data.interests || [] }) }, [q.data])
  const set = k => v => setP(s => ({ ...s, [k]: v }))

  const save = async () => {
    setBusy(true)
    setError('')
    try {
      const { province, city, userType, employmentStatus, roles, ageBand, maritalStatus, language, interests } = p
      await profileService.save({ province, city: city?.trim() || null, userType, employmentStatus, roles, ageBand, maritalStatus, language, interests })
      toast('Saved. Your answers will now be tailored to you.', 'success')
      navigate(fromSettings ? '/settings?tab=personalise' : '/chat')
    } catch (e) {
      setError(e.message || 'Could not save. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="ps">
      <div className="page-head">
        <div>
          <Breadcrumb items={fromSettings ? [{ label: 'Home', to: '/dashboard' }, { label: 'Settings', to: '/settings?tab=personalise' }, { label: 'Personalise my answers' }]
            : [{ label: 'Home', to: '/dashboard' }, { label: 'Personalise LegalMate' }]} />
          <h1 className="page-title">Tell us about your situation</h1>
          <p className="page-sub">A minute of answers helps LegalMate pick the right laws for where you live and what you do. Everything is optional.</p>
        </div>
      </div>

      {q.loading && !p && <Skeleton h={420} />}
      {q.error && !p && <ErrorState error={q.error} onRetry={q.reload} />}
      {p && (
        <div className="card card-pad ps-card">
          <p className="ps-privacy"><ShieldCheck size={18} /> These answers never include your name, CNIC, phone or email, and only shape the explanations you get. You can change them any time.</p>

          <div className="ps-row">
            <label className="field">
              <span className="field-label">Province or territory</span>
              <select className="ps-select" value={p.province || ''} onChange={e => set('province')(e.target.value || null)}>
                <option value="">Select…</option>
                {OPT.provinces.map(x => <option key={x}>{x}</option>)}
              </select>
            </label>
            <label className="field">
              <span className="field-label">City</span>
              <span className="input-wrap"><MapPin size={18} /><input value={p.city || ''} maxLength={60} onChange={e => set('city')(e.target.value)} placeholder="e.g. Lahore" /></span>
            </label>
          </div>

          <Choice title="I am a…" options={OPT.userTypes} value={p.userType} onChange={set('userType')} />
          <Choice title="Work status" options={OPT.employment} value={p.employmentStatus} onChange={set('employmentStatus')} />
          <Choice full title="In my legal matter I am (or may be)…" hint="choose all that apply" multi options={OPT.roles} value={p.roles} onChange={set('roles')} />
          <div className="ps-row">
            <Choice title="Age" options={OPT.ageBands} value={p.ageBand} onChange={set('ageBand')} />
            <Choice title="Marital status" options={OPT.marital} value={p.maritalStatus} onChange={set('maritalStatus')} />
          </div>
          <Choice full title="Answer me in" options={LANGS} value={p.language} onChange={v => set('language')(v || 'en')} />
          <Choice full title="Topics I care about" hint="choose all that apply" multi options={OPT.interests} value={p.interests} onChange={set('interests')} />

          {error && <p className="form-error" role="alert"><AlertCircle size={16} /> {error}</p>}
          <div className="ps-actions">
            <button type="button" className="btn btn-outline btn-lg" onClick={() => navigate(fromSettings ? '/settings?tab=personalise' : '/dashboard')}>{fromSettings ? 'Cancel' : 'Skip for now'}</button>
            <button type="button" className="btn btn-orange btn-lg" onClick={save} disabled={busy}>
              {busy && <Loader2 size={18} className="spin" />} {fromSettings ? 'Save my answers' : 'Save and start chatting'} {!busy && <ArrowRight size={18} />}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
