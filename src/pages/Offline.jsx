import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bookmark, BookOpen, Bot, Calculator, ChevronRight, Clock3, Database, FileSearch, FileText, Link2,
  Lightbulb, MessagesSquare, MoreHorizontal, RefreshCw, Settings, ShieldCheck, Users, WifiOff, X, BriefcaseBusiness,
  Wifi, CheckCircle2
} from 'lucide-react'
import { Breadcrumb, Toggle } from '../components/common'
import { useUI } from '../components/UIContext'
import { useQuery } from '../hooks/useApi'
import { useOnline } from '../hooks/useOnline'
import { USE_MOCKS } from '../api/config'
import { offlineQueue, offlineService } from '../api/services/offlineService'
import { settingsService } from '../api/services/settingsService'
import { formatBytes, formatDate, formatDateTime } from '../utils/format'

// Counts come from the local offline cache (offlineService.getAvailable)
const AVAILABLE = [
  { key: 'documents', icon: FileText, title: 'Downloaded Documents', unit: 'documents available', to: '/vault' },
  { key: 'briefs', icon: BriefcaseBusiness, title: 'Saved Case Briefs', unit: 'briefs available', to: '/case-briefs/ahmad-khan-vs-state' },
  { key: 'conversations', icon: MessagesSquare, title: 'Recent Chat History', unit: 'conversations', to: '/chat/tenant-rights' },
  { key: 'guides', icon: BookOpen, title: 'Saved Legal Guides', unit: 'guides available', to: '/dashboard' },
]

// Queued operation type -> icon
const OP_ICONS = { 'note.create': FileText, 'brief.update': BriefcaseBusiness, 'calculation.save': Calculator, 'bookmark.create': Bookmark }
const opTime = iso => {
  const d = new Date(iso)
  return `${d.toDateString() === new Date().toDateString() ? 'Today' : formatDate(iso)}, ${d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`
}

const UNAVAILABLE = [
  { icon: Bot, title: 'New AI chats' },
  { icon: FileSearch, title: 'Document analysis' },
  { icon: Link2, title: 'Live citations' },
  { icon: Users, title: 'Legal-aid availability' },
]

const TIPS = ['Download important documents while online.', 'Your recent chats are saved automatically.', 'Changes will sync when you’re back online.', 'Keep enough device storage for offline files.', 'Enable automatic downloads for seamless access.']

export default function Offline() {
  const navigate = useNavigate()
  const { toast } = useUI()
  const browserOnline = useOnline()
  const [banner, setBanner] = useState(true)
  const [trying, setTrying] = useState(false)
  // The design shows this page in its offline state; it switches to online after a successful sync.
  const [online, setOnline] = useState(!USE_MOCKS && browserOnline)
  const [pending, setPending] = useState(() => offlineQueue.list())
  const [lastSync, setLastSync] = useState(() => offlineService.lastSync())
  const available = useQuery(() => offlineService.getAvailable(), [])
  const storage = useQuery(() => offlineService.storageEstimate(), [])
  const prefs = useQuery(signal => settingsService.getPreferences(signal), [])
  const auto = prefs.data?.offline?.autoDownload ?? true

  const tryAgain = async () => {
    setTrying(true)
    try {
      if (!navigator.onLine) return toast('Still offline. We’ll keep trying automatically.', 'info')
      const { synced, failed, syncedAt } = await offlineService.sync()
      setOnline(true)
      setPending(offlineQueue.list())
      setLastSync(syncedAt)
      toast(failed.length ? `${synced} synced, ${failed.length} failed` : `Back online - ${synced} item${synced === 1 ? '' : 's'} synced successfully`)
    } catch (e) {
      toast(e.message || 'Sync failed. Please try again.', 'info')
    } finally {
      setTrying(false)
    }
  }

  const setAuto = async v => {
    prefs.setData(p => ({ ...p, offline: { ...p?.offline, autoDownload: v } }))
    try { await settingsService.updatePreferences({ offline: { autoDownload: v } }); toast(v ? 'Automatic downloads enabled' : 'Automatic downloads disabled') } catch (e) { toast(e.message, 'info'); prefs.reload({ silent: true }) }
  }

  const dropOp = op => {
    offlineQueue.remove(op.id)
    setPending(offlineQueue.list())
    toast(`“${op.title}” removed from sync queue`, 'info')
  }

  // React to real connectivity changes (auto-sync when the connection returns).
  useEffect(() => {
    if (!browserOnline) { setOnline(false); setBanner(true) } else if (!USE_MOCKS && pending.length) tryAgain()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [browserOnline])

  const pct = storage.data ? Math.round((storage.data.usedBytes / storage.data.quotaBytes) * 100) : 0

  return (
    <div className="off">
      {banner && !online && (
        <div className="off-banner">
          <WifiOff size={28} />
          <p><b>You're offline.</b> Some features are unavailable, but saved documents remain accessible.</p>
          <button onClick={() => setBanner(false)} aria-label="Dismiss"><X size={22} /></button>
        </div>
      )}

      <div className="page-head off-head">
        <div>
          <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Offline Access' }]} />
          <h1 className="page-title">Offline Access</h1>
          <p className="page-sub">Access your saved content and continue your legal work<br />without an internet connection.</p>
        </div>
        <div className={`off-status ${online ? 'is-online' : ''}`}>
          <div className="off-status-main">{online ? <Wifi size={40} /> : <WifiOff size={40} />}<div><span>Connection Status</span><b>{online ? 'Online' : 'Offline'}</b></div></div>
          <div className="off-status-sync"><Clock3 size={22} /><div><span>Last successful sync</span><b>{lastSync ? formatDateTime(lastSync) : 'Never'}</b></div></div>
          <button className="btn btn-orange btn-lg off-try" onClick={tryAgain} disabled={trying}><RefreshCw size={20} className={trying ? 'spin' : ''} /> {trying ? 'Connecting…' : 'Try Again'}</button>
        </div>
      </div>

      <div className="off-cols">
        <section className="card off-col">
          <div className="off-col-head"><span className="off-circle green"><ShieldCheck size={24} /></span><div><h2>Available Offline</h2><p>These features and items are available on your device.</p></div></div>
          {AVAILABLE.map(a => (
            <button key={a.title} className="off-item off-avail" onClick={() => navigate(a.to)}>
              <span className="icon-tile tile-green tile-md"><a.icon /></span>
              <div><b>{a.title}</b><span>{available.data ? `${available.data[a.key]} ${a.unit}` : '…'}</span></div>
              <ChevronRight size={20} />
            </button>
          ))}
        </section>

        <section className="card off-col">
          <div className="off-col-head"><span className="off-circle orange"><RefreshCw size={24} /></span><div><h2>Pending Sync</h2><p>These items will be synced when you're back online.</p></div></div>
          {pending.map(p => {
            const Icon = OP_ICONS[p.type] || FileText
            return (
              <div key={p.id} className="off-item off-pending">
                <Icon size={24} />
                <div><b>{p.title}</b><span>{p.subtitle}</span><span>{opTime(p.createdAt)}</span></div>
                <span className="pill pill-amber">Waiting to sync</span>
                <button className="icon-btn-plain" onClick={() => dropOp(p)} aria-label="Remove from sync queue"><MoreHorizontal size={20} /></button>
              </div>
            )
          })}
          {!pending.length && <div className="off-synced"><CheckCircle2 size={34} /><b>All changes synced</b><span>Nothing waiting to upload.</span></div>}
        </section>

        <section className="card off-col">
          <div className="off-col-head"><span className="off-circle gray"><WifiOff size={24} /></span><div><h2>Unavailable Offline</h2><p>These features require an internet connection.</p></div></div>
          {UNAVAILABLE.map(u => (
            <div key={u.title} className={`off-item off-unavail ${online ? 'ok' : ''}`}>
              <u.icon size={30} strokeWidth={1.5} />
              <div><b>{u.title}</b><span>{online ? 'Available now' : 'Requires internet connection'}</span></div>
            </div>
          ))}
        </section>
      </div>

      <div className="off-bottom">
        <section className="card off-settings">
          <div className="off-set-head"><Settings size={30} strokeWidth={1.6} /><div><b>Offline Settings</b><span>Manage your offline preferences and storage.</span></div></div>
          <div className="off-toggle"><Toggle checked={auto} onChange={setAuto} label="Automatically download recent documents" /><div><b>Automatically download recent documents for offline use</b><span>This will keep your latest documents, case briefs and guides available offline.</span></div></div>
          <div className="off-storage">
            <Database size={22} />
            <b>Device Storage</b>
            <div className="progress"><span style={{ width: `${pct}%`, background: '#f59e0b' }} /></div>
            <span>{storage.data ? `${formatBytes(storage.data.usedBytes)} used of ${formatBytes(storage.data.quotaBytes).replace('.0 ', ' ')}` : '…'}</span>
            <button className="link" onClick={() => navigate('/settings')}>Manage Storage</button>
          </div>
        </section>
        <section className="card off-tips">
          <h3><Lightbulb size={24} /> Tips for Offline Use</h3>
          <ol>{TIPS.map(t => <li key={t}>{t}</li>)}</ol>
        </section>
      </div>
    </div>
  )
}
