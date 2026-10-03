import { useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  AlertCircle, ArrowLeft, ArrowRight, Check, CheckCircle2, ChevronDown, Eye, EyeOff, Globe, IdCard, Loader2, Lock, Mail, Phone,
  ShieldCheck, User, Users, PartyPopper
} from 'lucide-react'
import { Checkbox, Logo } from '../components/common'
import { PakFlag } from '../components/Icons'
import { useUI } from '../components/UIContext'
import { useAuth } from '../context/AuthContext'
import { authService } from '../api/services/authService'
import { USE_MOCKS } from '../api/config'
import { LanguagePicker } from './Login'

function PasswordInput({ value, onChange, placeholder }) {
  const [show, setShow] = useState(false)
  return (
    <span className="input-wrap su-input">
      <Lock size={18} />
      <input type={show ? 'text' : 'password'} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} autoComplete="new-password" />
      <button type="button" className="icon-btn-plain eye" onClick={() => setShow(s => !s)} aria-label={show ? 'Hide password' : 'Show password'}>
        {show ? <EyeOff size={18} /> : <Eye size={18} />}
      </button>
    </span>
  )
}

function Stepper({ step }) {
  const steps = ['Personal Details', 'Verification', 'Complete']
  return (
    <ol className="su-stepper">
      {steps.map((s, i) => (
        <li key={s} className={i < step ? 'done' : i === step ? 'active' : ''}>
          <span className="su-step-dot">{i < step ? <Check size={13} strokeWidth={3} /> : i + 1}</span>
          <span className="su-step-label">{s}</span>
        </li>
      ))}
    </ol>
  )
}

function OtpInput({ value, onChange }) {
  const refs = useRef([])
  const set = (i, v) => {
    const d = v.replace(/\D/g, '').slice(-1)
    const arr = value.split('')
    arr[i] = d
    onChange(arr.join('').slice(0, 6))
    if (d && i < 5) refs.current[i + 1]?.focus()
  }
  return (
    <div className="otp">
      {Array.from({ length: 6 }).map((_, i) => (
        <input key={i} ref={el => (refs.current[i] = el)} inputMode="numeric" maxLength={1} value={value[i] || ''}
          onChange={e => set(i, e.target.value)}
          onKeyDown={e => { if (e.key === 'Backspace' && !value[i] && i > 0) refs.current[i - 1]?.focus() }}
          aria-label={`Digit ${i + 1}`} />
      ))}
    </div>
  )
}

export default function Signup() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [f, setF] = useState({ name: '', cnic: '', email: '', phone: '', lang: 'en', password: '', confirm: '', agree: false })
  const [otp, setOtp] = useState('')
  const [verification, setVerification] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const { verifyOtp } = useAuth()
  const { toast } = useUI()
  const set = k => v => setF(p => ({ ...p, [k]: v }))

  const run = async fn => {
    setBusy(true)
    setError('')
    try { await fn() } catch (err) { setError(err.message || 'Something went wrong. Please try again.') } finally { setBusy(false) }
  }

  const register = e => {
    e.preventDefault()
    if (!USE_MOCKS) {
      if (!f.name.trim() || !f.email.trim() || !f.phone.trim()) return setError('Please fill in your name, email and phone number.')
      if (!rules.every(r => r.ok)) return setError('Please choose a password that meets all the requirements.')
      if (!f.agree) return setError('Please accept the Terms of Service and Privacy Policy.')
    }
    run(async () => {
      const res = await authService.register({
        fullName: f.name.trim(), cnic: f.cnic, email: f.email.trim(), phone: `+92${f.phone.replace(/\s/g, '')}`,
        preferredLanguage: f.lang, password: f.password, acceptedTerms: f.agree,
      })
      setVerification(res)
      setStep(1)
    })
  }

  const verify = e => {
    e.preventDefault()
    if (!USE_MOCKS && otp.length !== 6) return setError('Enter the 6-digit code.')
    run(async () => { await verifyOtp({ verificationId: verification?.verificationId, code: otp }); setStep(2) })
  }

  const resend = () => run(async () => { await authService.resendOtp(verification?.verificationId); toast('A new code has been sent.') })

  const rules = useMemo(() => {
    const p = f.password
    return [
      { label: 'At least 8 characters', ok: p.length >= 8 },
      { label: 'One special character', ok: /[^A-Za-z0-9]/.test(p) },
      { label: 'One uppercase letter', ok: /[A-Z]/.test(p) },
      { label: 'Passwords match', ok: p.length > 0 && p === f.confirm },
      { label: 'One number', ok: /\d/.test(p) },
    ]
  }, [f.password, f.confirm])

  const score = f.password ? rules.filter(r => r.ok && r.label !== 'Passwords match').length : 0
  const strength = score === 0 ? '' : score <= 1 ? 'Weak' : score === 2 ? 'Fair' : score === 3 ? 'Good' : 'Strong'
  const bars = score === 4 ? 4 : score

  const formatCnic = v => {
    const d = v.replace(/\D/g, '').slice(0, 13)
    return [d.slice(0, 5), d.slice(5, 12), d.slice(12)].filter(Boolean).join('-')
  }

  return (
    <div className="auth">
      <aside className="auth-panel auth-panel-signup">
        <img className="auth-panel-bg" src="/assets/img/signup-panel.jpg" alt="" />
        <div className="auth-panel-content">
          <Logo variant="light" to="/" size="lg" />
          <h1 className="auth-hero su-hero">Your Legal<br />Companion<br />for a <span>Fairer Pakistan</span></h1>
          <p className="auth-hero-sub">Get trusted legal guidance, analyse documents and securely manage your legal records - all in one place.</p>
          <ul className="su-points">
            <li><span><User size={19} /></span><div><b>Expert-backed answers</b><small>Based on Pakistani laws and sources</small></div></li>
            <li><span><ShieldCheck size={19} /></span><div><b>Your data stays private</b><small>Encrypted and secure</small></div></li>
            <li><span><Users size={19} /></span><div><b>Made for every citizen</b><small>Simple. Clear. Accessible.</small></div></li>
          </ul>
        </div>
        <div className="su-foot">
          <span><Lock size={18} /> Secure</span><i>|</i>
          <span><ShieldCheck size={18} /> Confidential</span><i>|</i>
          <span><Users size={18} /> Easy to understand</span>
        </div>
      </aside>

      <section className="auth-form-side su-side">
        <LanguagePicker />
        <div className="su-wrap">
          <Stepper step={step} />

          {step === 0 && (
            <form className="su-form" onSubmit={register}>
              <h2 className="su-title">Create your LegalMate account</h2>
              <p className="su-sub">Join thousands of Pakistanis getting clear legal guidance.</p>

              <div className="su-grid">
                <label className="field">
                  <span className="field-label">Full name</span>
                  <span className="input-wrap su-input"><User size={18} /><input value={f.name} onChange={e => set('name')(e.target.value)} placeholder="Enter your full name" autoComplete="name" /></span>
                </label>
                <label className="field">
                  <span className="field-label">CNIC or identity number</span>
                  <span className="input-wrap su-input"><IdCard size={18} /><input value={f.cnic} onChange={e => set('cnic')(formatCnic(e.target.value))} placeholder="XXXXX-XXXXXXX-X" inputMode="numeric" /></span>
                  <span className="su-help"><ShieldCheck size={14} /> Your CNIC is used only for verification and kept private.</span>
                </label>
                <label className="field">
                  <span className="field-label">Email address</span>
                  <span className="input-wrap su-input"><Mail size={18} /><input type="email" value={f.email} onChange={e => set('email')(e.target.value)} placeholder="name@example.com" autoComplete="email" /></span>
                </label>
                <label className="field">
                  <span className="field-label">Phone number</span>
                  <span className="input-wrap su-input su-phone">
                    <Phone size={18} />
                    <span className="su-cc"><PakFlag width={20} /> +92 <ChevronDown size={14} /></span>
                    <input value={f.phone} onChange={e => set('phone')(e.target.value.replace(/[^\d ]/g, '').slice(0, 11))} placeholder="300 1234567" inputMode="tel" autoComplete="tel-national" />
                  </span>
                </label>
              </div>

              <div className="field su-lang-field">
                <span className="field-label">Preferred language</span>
                <div className="su-langs" role="radiogroup">
                  {[
                    { v: 'en', icon: <span className="su-lang-badge">EN</span>, label: 'English' },
                    { v: 'ur', icon: <span className="su-lang-badge su-lang-ur urdu">اردو</span>, label: 'Urdu' },
                    { v: 'both', icon: <span className="su-lang-badge su-lang-globe"><Globe size={17} /></span>, label: 'Both' },
                  ].map(o => (
                    <button type="button" role="radio" aria-checked={f.lang === o.v} key={o.v}
                      className={`su-lang ${f.lang === o.v ? 'active' : ''}`} onClick={() => set('lang')(o.v)}>
                      {o.icon}{o.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="su-grid">
                <label className="field">
                  <span className="field-label">Password</span>
                  <PasswordInput value={f.password} onChange={set('password')} placeholder="Create a password" />
                </label>
                <label className="field">
                  <span className="field-label">Confirm password</span>
                  <PasswordInput value={f.confirm} onChange={set('confirm')} placeholder="Confirm your password" />
                </label>
              </div>

              <div className="su-strength">
                <div className="su-bars">{[0, 1, 2, 3].map(i => <span key={i} className={i < bars ? `on s${bars}` : ''} />)}</div>
                <p>Password strength: <b className={`s${bars}`}>{strength || '-'}</b></p>
                <ul className="su-rules">
                  {rules.map(r => (
                    <li key={r.label} className={r.ok ? 'ok' : ''}><CheckCircle2 size={15} />{r.label}</li>
                  ))}
                </ul>
              </div>

              <Checkbox checked={f.agree} onChange={set('agree')} tone="blue">
                I agree to the <a href="#terms" className="su-link">Terms of Service</a> and <a href="#privacy" className="su-link">Privacy Policy</a>.
              </Checkbox>

              {error && <p className="form-error" role="alert"><AlertCircle size={16} /> {error}</p>}
              <button className="btn btn-orange btn-lg btn-block su-submit" disabled={busy}>{busy && <Loader2 size={18} className="spin" />} Create Account {!busy && <ArrowRight size={18} />}</button>
              <div className="su-divider" />
              <p className="auth-switch su-switch">Already have an account? <Link to="/login">Log in</Link></p>
            </form>
          )}

          {step === 1 && (
            <form className="su-form su-verify" onSubmit={verify}>
              <span className="su-verify-icon"><ShieldCheck size={30} /></span>
              <h2 className="su-title">Verify your phone number</h2>
              <p className="su-sub">We've sent a 6-digit code to <b>{verification?.maskedDestination || `+92 ${f.phone || '300 1234567'}`}</b>. Enter it below to verify your account.</p>
              <OtpInput value={otp} onChange={setOtp} />
              <p className="su-resend">Didn't receive the code? <button type="button" className="auth-link" onClick={resend} disabled={busy}>Resend code</button></p>
              {error && <p className="form-error" role="alert"><AlertCircle size={16} /> {error}</p>}
              <button className="btn btn-orange btn-lg btn-block su-submit" disabled={busy}>{busy && <Loader2 size={18} className="spin" />} Verify &amp; Continue {!busy && <ArrowRight size={18} />}</button>
              <button type="button" className="btn btn-outline btn-lg btn-block" onClick={() => setStep(0)}><ArrowLeft size={18} /> Back</button>
            </form>
          )}

          {step === 2 && (
            <div className="su-form su-verify">
              <span className="su-verify-icon su-done"><PartyPopper size={30} /></span>
              <h2 className="su-title">Welcome to LegalMate{f.name ? `, ${f.name.split(' ')[0]}` : ''}!</h2>
              <p className="su-sub">Your account is ready. You can now ask legal questions, analyse documents and keep your records safe in your Legal Vault.</p>
              <button className="btn btn-orange btn-lg btn-block su-submit" onClick={() => navigate('/dashboard')}>Go to Dashboard <ArrowRight size={18} /></button>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
