import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Bell, Camera, ChevronRight, Database, Download, Eye, EyeOff, Globe, KeyRound, Laptop, Loader2, Lock, LogOut,
  Mail, MapPin, Monitor, Phone, Shield, ShieldCheck, Smartphone, Trash2, User, IdCard, Link2, Palette, Moon, Sun
} from 'lucide-react'
import { Breadcrumb, Modal, Select, Toggle } from '../components/common'
import { PakFlag, WhatsAppIcon, GoogleIcon } from '../components/Icons'
import { useUI } from '../components/UIContext'
import { ErrorState, Skeleton } from '../components/States'
import { useAuth } from '../context/AuthContext'
import { useQuery } from '../hooks/useApi'
import { settingsService } from '../api/services/settingsService'
import { formatBytes } from '../utils/format'

const TABS = [
  { k: 'profile', icon: User, label: 'Profile', sub: 'Personal information' },
  { k: 'security', icon: Shield, label: 'Account & Security', sub: 'Password, 2FA, sessions' },
  { k: 'notifications', icon: Bell, label: 'Notifications', sub: 'Email, SMS, WhatsApp' },
  { k: 'language', icon: Globe, label: 'Language & Region', sub: 'Language, date format' },
  { k: 'privacy', icon: Lock, label: 'Privacy & Data', sub: 'Data, storage, export' },
  { k: 'apps', icon: Link2, label: 'Connected Apps', sub: 'WhatsApp, Google' },
  { k: 'appearance', icon: Palette, label: 'Appearance', sub: 'Theme and display' },
]
const DEVICE_ICONS = { laptop: Laptop, phone: Smartphone, desktop: Monitor }
const PROFILE_FIELDS = ['name', 'email', 'phone', 'city', 'address']

function Row({ title, sub, children }) {
  return (
    <div className="st-row">
      <div><b>{title}</b>{sub && <span>{sub}</span>}</div>
      <div className="st-row-ctl">{children}</div>
    </div>
  )
}

const CardSkeleton = () => <div className="card st-card"><Skeleton w={200} h={22} /><Skeleton h={160} style={{ marginTop: 16 }} /></div>

export default function Settings() {
  const navigate = useNavigate()
  const { toast, language, setLanguage } = useUI()
  const { user, logout, updateUser } = useAuth()
  const [tab, setTab] = useState('profile')
  const [profile, setProfile] = useState(null)
  const [savingProfile, setSavingProfile] = useState(false)
  const [showPw, setShowPw] = useState(false)
  const [pw, setPw] = useState({ current: '', next: '' })
  const [pwBusy, setPwBusy] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [busy, setBusy] = useState(null)
  const avatarRef = useRef(null)

  const profileQ = useQuery(signal => settingsService.getProfile(signal), [])
  const prefs = useQuery(signal => settingsService.getPreferences(signal), [])
  const security = useQuery(signal => settingsService.getSecurity(signal), [], { enabled: tab === 'security' })
  const sessions = useQuery(signal => settingsService.listSessions(signal), [], { enabled: tab === 'security' })
  const storage = useQuery(signal => settingsService.getStorage(signal), [], { enabled: tab === 'privacy' })
  const apps = useQuery(signal => settingsService.listIntegrations(signal), [], { enabled: tab === 'apps' })

  useEffect(() => { if (profileQ.data && !profile) setProfile(profileQ.data) }, [profileQ.data, profile])
  const setP = k => e => setProfile(p => ({ ...p, [k]: e.target.value }))

  const saveProfile = async () => {
    setSavingProfile(true)
    try {
      const patch = Object.fromEntries(PROFILE_FIELDS.map(k => [k, profile[k]]))
      const saved = await settingsService.updateProfile(patch)
      profileQ.setData(saved)
      updateUser({ name: saved.name, email: saved.email, firstName: undefined })
      toast('Profile updated')
    } catch (e) { toast(e.message, 'info') } finally { setSavingProfile(false) }
  }

  const changeAvatar = async file => {
    if (!file) return
    if (file.size > 2 * 1024 * 1024) return toast('Please choose an image up to 2 MB', 'info')
    setBusy('avatar')
    try { const { avatarUrl } = await settingsService.uploadAvatar(file); setProfile(p => ({ ...p, avatarUrl })); updateUser({ avatarUrl }); toast('Profile photo updated') } catch (e) { toast(e.message, 'info') } finally { setBusy(null) }
  }

  const changePassword = async () => {
    if (!pw.current || pw.next.length < 8) return toast('Enter your current password and a new password of 8+ characters', 'info')
    setPwBusy(true)
    try { await settingsService.changePassword({ currentPassword: pw.current, newPassword: pw.next }); setPw({ current: '', next: '' }); toast('Password updated') } catch (e) { toast(e.message, 'info') } finally { setPwBusy(false) }
  }

  /** Optimistically updates a preference group and persists it (PATCH /users/me/preferences). */
  const setPref = async (group, key, value) => {
    const prev = prefs.data
    prefs.setData(p => ({ ...p, [group]: { ...p[group], [key]: value } }))
    try { await settingsService.updatePreferences({ [group]: { [key]: value } }) } catch (e) { prefs.setData(prev); toast(e.message, 'info') }
  }

  const setSecurity = async (key, value, msg) => {
    const prev = security.data
    security.setData(s => ({ ...s, [key]: value }))
    try { await settingsService.updateSecurity({ [key]: value }); if (msg) toast(msg) } catch (e) { security.setData(prev); toast(e.message, 'info') }
  }

  const revoke = async s => {
    sessions.setData(d => ({ ...d, items: d.items.filter(x => x.id !== s.id) }))
    try { await settingsService.revokeSession(s.id); toast(`Signed out of ${s.device}`) } catch (e) { toast(e.message, 'info'); sessions.reload({ silent: true }) }
  }

  const run = async (key, fn, msg, type) => {
    setBusy(key)
    try { await fn(); if (msg) toast(msg, type) } catch (e) { toast(e.message, 'info') } finally { setBusy(null) }
  }

  const toggleApp = a => run(`app_${a.provider}`, async () => {
    if (a.connected) await settingsService.disconnectIntegration(a.provider)
    else {
      const r = await settingsService.connectIntegration(a.provider)
      if (r?.redirectUrl) { window.location.href = r.redirectUrl; return }
    }
    apps.reload({ silent: true })
  }, a.connected ? `${a.provider === 'google' ? 'Google' : 'WhatsApp'} disconnected` : 'Google account connected')

  const signOut = async () => { await logout(); navigate('/login', { replace: true }) }

  const n = prefs.data?.notifications
  const region = prefs.data?.region
  const priv = prefs.data?.privacy
  const appearance = prefs.data?.appearance
  const st = storage.data?.storage
  const pct = st ? Math.round((st.usedBytes / st.quotaBytes) * 100) : 0
  const avatar = profile?.avatarUrl ? <img className="avatar st-avatar-lg" src={profile.avatarUrl} alt="" /> : <span className="avatar st-avatar-lg">{user?.initials}</span>

  return (
    <div className="st">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Settings' }]} />
      <h1 className="page-title">Settings</h1>
      <p className="page-sub">Manage your account, preferences and privacy.</p>

      <div className="st-grid">
        <aside className="card st-nav">
          <div className="st-user">
            {user?.avatarUrl ? <img className="avatar st-avatar" src={user.avatarUrl} alt="" /> : <span className="avatar st-avatar">{user?.initials}</span>}
            <div><b>{user?.name}</b><span>{user?.roleLabel}</span></div>
          </div>
          <ul>
            {TABS.map(t => (
              <li key={t.k}>
                <button className={tab === t.k ? 'active' : ''} onClick={() => setTab(t.k)}>
                  <t.icon size={20} />
                  <span><b>{t.label}</b><small>{t.sub}</small></span>
                  <ChevronRight size={17} />
                </button>
              </li>
            ))}
          </ul>
          <button className="st-logout" onClick={signOut}><LogOut size={18} /> Log out</button>
        </aside>

        <section className="st-main">
          {tab === 'profile' && (!profile ? (profileQ.error ? <ErrorState error={profileQ.error} onRetry={profileQ.reload} /> : <CardSkeleton />) : (
            <div className="card st-card">
              <div className="st-card-head"><h2>Profile</h2><p>This information is used across LegalMate and on your case briefs.</p></div>
              <div className="st-photo">
                {avatar}
                <div><b>Profile photo</b><span>JPG or PNG, up to 2 MB.</span></div>
                <input ref={avatarRef} type="file" hidden accept="image/png,image/jpeg" onChange={e => { changeAvatar(e.target.files[0]); e.target.value = '' }} />
                <button className="btn btn-outline" onClick={() => avatarRef.current.click()} disabled={busy === 'avatar'}>{busy === 'avatar' ? <Loader2 size={17} className="spin" /> : <Camera size={17} />} Change</button>
              </div>
              <div className="st-form">
                <label className="field"><span className="field-label">Full name</span><span className="input-wrap"><User size={18} /><input value={profile.name} onChange={setP('name')} /></span></label>
                <label className="field"><span className="field-label">CNIC</span><span className="input-wrap"><IdCard size={18} /><input value={profile.cnic} readOnly title="Contact support to change your CNIC" /></span>{profile.cnicVerified && <span className="su-help"><ShieldCheck size={14} /> Verified with NADRA</span>}</label>
                <label className="field"><span className="field-label">Email address</span><span className="input-wrap"><Mail size={18} /><input value={profile.email} onChange={setP('email')} /></span></label>
                <label className="field"><span className="field-label">Phone number</span><span className="input-wrap"><Phone size={18} /><span className="su-cc"><PakFlag width={20} /> +92</span><input value={profile.phone} onChange={setP('phone')} /></span></label>
                <label className="field"><span className="field-label">City</span><span className="input-wrap"><MapPin size={18} /><input value={profile.city} onChange={setP('city')} /></span></label>
                <label className="field"><span className="field-label">Address</span><span className="input-wrap"><MapPin size={18} /><input value={profile.address} onChange={setP('address')} /></span></label>
              </div>
              <div className="st-actions">
                <button className="btn btn-outline btn-lg" onClick={() => { setProfile(profileQ.data); toast('Changes discarded', 'info') }}>Cancel</button>
                <button className="btn btn-orange btn-lg" onClick={saveProfile} disabled={savingProfile}>{savingProfile && <Loader2 size={18} className="spin" />} Save Changes</button>
              </div>
            </div>
          ))}

          {tab === 'security' && (
            <>
              <div className="card st-card">
                <div className="st-card-head"><h2>Change Password</h2><p>Use at least 8 characters with a number and a special character.</p></div>
                <div className="st-form">
                  <label className="field"><span className="field-label">Current password</span><span className="input-wrap"><Lock size={18} /><input type={showPw ? 'text' : 'password'} value={pw.current} onChange={e => setPw({ ...pw, current: e.target.value })} placeholder="Enter current password" /><button className="icon-btn-plain" onClick={() => setShowPw(s => !s)} type="button">{showPw ? <EyeOff size={18} /> : <Eye size={18} />}</button></span></label>
                  <label className="field"><span className="field-label">New password</span><span className="input-wrap"><KeyRound size={18} /><input type={showPw ? 'text' : 'password'} value={pw.next} onChange={e => setPw({ ...pw, next: e.target.value })} placeholder="Create a new password" /></span></label>
                </div>
                <div className="st-actions"><button className="btn btn-navy btn-lg" onClick={changePassword} disabled={pwBusy}>{pwBusy && <Loader2 size={18} className="spin" />} Update Password</button></div>
              </div>
              {security.data ? (
                <div className="card st-card">
                  <Row title="Two-factor authentication" sub="Require a one-time code sent to your phone when logging in."><Toggle checked={security.data.twoFactorEnabled} onChange={v => setSecurity('twoFactorEnabled', v, v ? '2FA enabled' : '2FA disabled')} label="Two-factor authentication" /></Row>
                  <Row title="Login alerts" sub="Get notified of new sign-ins to your account."><Toggle checked={security.data.loginAlerts} onChange={v => setSecurity('loginAlerts', v)} label="Login alerts" /></Row>
                </div>
              ) : <CardSkeleton />}
              <div className="card st-card">
                <div className="st-card-head"><h2>Active Sessions</h2><p>Devices currently signed in to your account.</p></div>
                {!sessions.data && <Skeleton h={120} />}
                {sessions.data?.items.map(s => {
                  const Icon = DEVICE_ICONS[s.deviceType] || Monitor
                  return (
                    <div key={s.id} className="st-session"><Icon size={22} /><div><b>{s.device} {s.current && <span className="pill pill-green">This device</span>}</b><span>{s.location} · {s.lastActiveLabel}</span></div>{!s.current && <button className="link small" onClick={() => revoke(s)}>Sign out</button>}</div>
                  )
                })}
              </div>
            </>
          )}

          {tab === 'notifications' && (!n ? <CardSkeleton /> : (
            <div className="card st-card">
              <div className="st-card-head"><h2>Notifications</h2><p>Choose how and when LegalMate contacts you.</p></div>
              <h3 className="st-h3">Channels</h3>
              <Row title="Email" sub={user?.email}><Toggle checked={n.email} onChange={v => setPref('notifications', 'email', v)} label="Email" /></Row>
              <Row title="SMS" sub={`+92 ${user?.phone || ''}`}><Toggle checked={n.sms} onChange={v => setPref('notifications', 'sms', v)} label="SMS" /></Row>
              <Row title="WhatsApp" sub="Receive updates via LegalMate on WhatsApp"><Toggle checked={n.whatsapp} onChange={v => setPref('notifications', 'whatsapp', v)} label="WhatsApp" /></Row>
              <h3 className="st-h3">Alerts</h3>
              <Row title="Deadline reminders" sub="Court hearings, submissions and legal notices"><Toggle checked={n.deadlines} onChange={v => setPref('notifications', 'deadlines', v)} label="Deadline reminders" /></Row>
              <Row title="Document analysis complete" sub="When an uploaded document has been analysed"><Toggle checked={n.analysis} onChange={v => setPref('notifications', 'analysis', v)} label="Analysis complete" /></Row>
              <Row title="Legal updates & tips" sub="Occasional updates about new laws and features"><Toggle checked={n.news} onChange={v => setPref('notifications', 'news', v)} label="Legal updates" /></Row>
            </div>
          ))}

          {tab === 'language' && (!region ? <CardSkeleton /> : (
            <div className="card st-card">
              <div className="st-card-head"><h2>Language & Region</h2><p>Set your preferred language and regional formats.</p></div>
              <Row title="App language" sub="Language used across LegalMate"><Select value={language} onChange={v => { setLanguage(v); setPref('region', 'language', v) }} options={['English', 'اردو']} className="st-select" /></Row>
              <Row title="Province" sub="Used to apply provincial laws and rates"><Select value={region.province} onChange={v => setPref('region', 'province', v)} options={['Punjab', 'Sindh', 'Khyber Pakhtunkhwa', 'Balochistan', 'Islamabad Capital Territory', 'Gilgit-Baltistan', 'Azad Jammu & Kashmir']} className="st-select" /></Row>
              <Row title="Date format"><Select value={region.dateFormat} onChange={v => setPref('region', 'dateFormat', v)} options={['DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD']} className="st-select" /></Row>
              <Row title="Time zone"><Select value={region.timezone} onChange={v => setPref('region', 'timezone', v)} options={['(GMT+05:00) Pakistan Standard Time', '(GMT+04:00) Gulf Standard Time', '(GMT+00:00) London']} className="st-select" /></Row>
            </div>
          ))}

          {tab === 'privacy' && (
            <>
              {!priv ? <CardSkeleton /> : (
                <div className="card st-card">
                  <div className="st-card-head"><h2>Privacy & Data</h2><p>You are in control of your legal information.</p></div>
                  <Row title="Save chat history" sub="Keep your conversations for future reference"><Toggle checked={priv.saveChatHistory} onChange={v => setPref('privacy', 'saveChatHistory', v)} label="Save chat history" /></Row>
                  <Row title="Help improve LegalMate" sub="Share anonymised usage data. Your documents are never shared."><Toggle checked={priv.shareUsageData} onChange={v => setPref('privacy', 'shareUsageData', v)} label="Help improve" /></Row>
                  <Row title="Auto-delete chats" sub="Automatically delete conversations older than"><Select value={priv.autoDeleteChats} onChange={v => setPref('privacy', 'autoDeleteChats', v)} options={['3 months', '6 months', '12 months', 'Never']} className="st-select" /></Row>
                </div>
              )}
              <div className="card st-card">
                <div className="st-storage"><Database size={24} /><div><b>Legal Vault storage</b><span>{st ? `${formatBytes(st.usedBytes)} of ${formatBytes(st.quotaBytes).replace('.0 ', ' ')} used` : '…'}</span><div className="progress"><span style={{ width: `${pct}%`, background: '#1d5fd6' }} /></div></div><Link to="/vault" className="btn btn-outline">Manage</Link></div>
                <Row title="Download your data" sub="Get a copy of your documents, briefs and chats"><button className="btn btn-outline" onClick={() => run('export', settingsService.requestExport, 'We’ll email you a download link within 24 hours')} disabled={busy === 'export'}>{busy === 'export' ? <Loader2 size={17} className="spin" /> : <Download size={17} />} Request Export</button></Row>
                <Row title="Delete account" sub="Permanently delete your account and all data"><button className="btn btn-danger-soft" onClick={() => setConfirmDelete(true)}><Trash2 size={17} /> Delete Account</button></Row>
              </div>
            </>
          )}

          {tab === 'apps' && (
            <div className="card st-card">
              <div className="st-card-head"><h2>Connected Apps</h2><p>Services linked to your LegalMate account.</p></div>
              {!apps.data && <Skeleton h={100} />}
              {apps.data?.items.map(a => a.provider === 'whatsapp' ? (
                <div key={a.provider} className="st-app"><WhatsAppIcon filled size={40} /><div><b>WhatsApp</b><span>{a.connected ? `${a.account} · Connected` : 'Not connected'}</span></div><Link to="/whatsapp" className="btn btn-outline">Manage</Link></div>
              ) : (
                <div key={a.provider} className="st-app"><span className="st-g"><GoogleIcon size={26} /></span><div><b>Google</b><span>{a.connected ? `${a.account} · Connected` : 'Not connected'}</span></div>
                  <button className="btn btn-outline" onClick={() => toggleApp(a)} disabled={busy === `app_${a.provider}`}>{busy === `app_${a.provider}` && <Loader2 size={16} className="spin" />} {a.connected ? 'Disconnect' : 'Connect'}</button></div>
              ))}
            </div>
          )}

          {tab === 'appearance' && (!appearance ? <CardSkeleton /> : (
            <div className="card st-card">
              <div className="st-card-head"><h2>Appearance</h2><p>Customise how LegalMate looks.</p></div>
              <div className="st-themes">
                {[{ k: 'light', icon: Sun, l: 'Light' }, { k: 'dark', icon: Moon, l: 'Dark (coming soon)' }, { k: 'system', icon: Monitor, l: 'System' }].map(t => (
                  <button key={t.k} className={`depth ${appearance.theme === t.k ? 'active' : ''}`} onClick={() => { if (t.k === 'dark') return toast('Dark mode is coming soon', 'info'); setPref('appearance', 'theme', t.k) }}><span className="radio" /><t.icon size={20} /><div><b>{t.l}</b></div></button>
                ))}
              </div>
              <Row title="Display density"><Select value={appearance.density} onChange={v => setPref('appearance', 'density', v)} options={['Comfortable', 'Compact']} className="st-select" /></Row>
            </div>
          ))}
        </section>
      </div>

      <Modal open={confirmDelete} onClose={() => setConfirmDelete(false)} className="modal-sm">
        <div className="confirm">
          <span className="icon-tile tile-red tile-lg"><Trash2 /></span>
          <h3>Delete your account?</h3>
          <p>This will permanently delete your documents, case briefs and chat history. This cannot be undone.</p>
          <div className="confirm-actions">
            <button className="btn btn-outline" onClick={() => setConfirmDelete(false)}>Cancel</button>
            <button className="btn btn-danger-soft" disabled={busy === 'delete'} onClick={() => run('delete', async () => { await settingsService.deleteAccount(); setConfirmDelete(false) }, 'Account deletion requested. Check your email to confirm.', 'info')}>
              {busy === 'delete' && <Loader2 size={16} className="spin" />} Delete Account
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
