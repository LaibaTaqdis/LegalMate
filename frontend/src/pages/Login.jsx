import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { AlertCircle, ArrowRight, Briefcase, ChevronDown, Eye, EyeOff, Globe, Loader2, Lock, Mail, ShieldCheck, User, Users } from 'lucide-react'
import { Checkbox, Logo, useClickOutside } from '../components/common'
import { GoogleIcon } from '../components/Icons'
import { useUI } from '../components/UIContext'
import { homeFor, useAuth } from '../context/AuthContext'
import { authService } from '../api/services/authService'
import { USE_MOCKS } from '../api/config'

const ROLES = [
  { key: 'client', label: 'Client', icon: User },
  { key: 'lawyer', label: 'Lawyer', icon: Briefcase },
  { key: 'admin', label: 'Admin', icon: ShieldCheck },
]

export function LanguagePicker() {
  const { language, setLanguage } = useUI()
  const [open, setOpen] = useState(false)
  const ref = useClickOutside(() => setOpen(false))
  return (
    <div className="auth-lang" ref={ref}>
      <button onClick={() => setOpen(o => !o)}><Globe size={18} /> {language} <ChevronDown size={15} /></button>
      {open && (
        <div className="popover popover-sm">
          {['English', 'اردو'].map(l => (
            <button key={l} className={`popover-item ${l === language ? 'active' : ''}`} onClick={() => { setLanguage(l); setOpen(false) }}>{l}</button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Login() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { login, loginWithGoogle } = useAuth()
  const { toast } = useUI()
  const [role, setRole] = useState('client')
  const [show, setShow] = useState(false)
  const [remember, setRemember] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const next = params.get('next') || homeFor(role)

  const submit = async e => {
    e.preventDefault()
    // Mock mode lets any input through; with a backend, empty credentials are rejected up front.
    if (!USE_MOCKS && (!email.trim() || !password)) return setError('Enter your email or phone number and password.')
    setBusy(true)
    setError('')
    try {
      const u = await login({ identifier: email.trim(), password, remember, role })
      navigate(params.get('next') || homeFor(u.role), { replace: true })
    } catch (err) {
      setError(err.message || 'Could not log in. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const google = async () => {
    try { await loginWithGoogle(); navigate(next, { replace: true }) } catch (err) { setError(err.message) }
  }

  const forgot = async () => {
    if (!email.trim()) return setError('Enter your email or phone number first, then tap “Forgot password?”.')
    await authService.forgotPassword(email.trim()).catch(() => {})
    setError('')
    toast('If an account exists, we have sent password reset instructions.', 'info')
  }

  return (
    <div className="auth">
      <aside className="auth-panel auth-panel-login">
        <img className="auth-panel-bg" src="/assets/img/login-panel.jpg" alt="" />
        <div className="auth-panel-content">
          <Logo variant="light" to="/" size="lg" />
          <h1 className="auth-hero">Legal guidance<br />when <span>you need it</span></h1>
          <p className="auth-hero-sub">Get clear answers, analyse your documents and securely manage your legal records - all in one place.</p>
          <ul className="auth-badges">
            <li><span><ShieldCheck size={17} /></span>Secure</li>
            <li><span><Lock size={16} /></span>Confidential</li>
            <li><span><Users size={17} /></span>Easy to understand</li>
          </ul>
        </div>
        <div className="auth-panel-foot">
          <p>Secure <i>•</i> Confidential <i>•</i> Easy to understand</p>
        </div>
      </aside>

      <section className="auth-form-side">
        <LanguagePicker />
        <form className="auth-form login-form" onSubmit={submit}>
          <p className="auth-kicker">WELCOME BACK</p>
          <h2 className="auth-title">Welcome back</h2>
          <p className="auth-sub">Log in to continue to LegalMate.</p>

          <div className="auth-roles" role="radiogroup" aria-label="Sign in as">
            {ROLES.map(r => (
              <button type="button" key={r.key} role="radio" aria-checked={role === r.key} className={role === r.key ? 'active' : ''} onClick={() => setRole(r.key)}>
                <r.icon size={16} /> {r.label}
              </button>
            ))}
          </div>

          <label className="field">
            <span className="field-label">Email or phone number</span>
            <span className="input-wrap auth-input"><Mail size={19} /><input value={email} onChange={e => setEmail(e.target.value)} placeholder="name@example.com or 03XX XXXXXXX" autoComplete="username" /></span>
          </label>
          <label className="field">
            <span className="field-label">Password</span>
            <span className="input-wrap auth-input">
              <Lock size={19} />
              <input type={show ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter your password" autoComplete="current-password" />
              <button type="button" className="icon-btn-plain eye" onClick={() => setShow(s => !s)} aria-label={show ? 'Hide password' : 'Show password'}>
                {show ? <EyeOff size={19} /> : <Eye size={19} />}
              </button>
            </span>
          </label>

          <div className="auth-row">
            <Checkbox checked={remember} onChange={setRemember}>Remember me</Checkbox>
            <button type="button" className="auth-link" onClick={forgot}>Forgot password?</button>
          </div>

          {error && <p className="form-error" role="alert"><AlertCircle size={16} /> {error}</p>}

          <button className="btn btn-orange btn-lg btn-block auth-submit" disabled={busy}>
            {busy ? <Loader2 size={18} className="spin" /> : null} Log In {!busy && <ArrowRight size={18} />}
          </button>

          <div className="auth-or"><span>or continue with</span></div>

          <button type="button" className="btn btn-outline btn-lg btn-block auth-google" onClick={google}>
            <GoogleIcon size={22} /> Continue with Google
          </button>

          <p className="auth-switch">Don't have an account? <Link to="/signup">Sign up</Link></p>
          <p className="auth-switch">Are you a lawyer? <Link to="/lawyer/apply">Apply to join LegalMate</Link></p>
        </form>
        <p className="auth-terms">By continuing, you agree to our <a href="#terms">Terms of Service</a> and <a href="#privacy">Privacy Policy.</a></p>
      </section>
    </div>
  )
}
