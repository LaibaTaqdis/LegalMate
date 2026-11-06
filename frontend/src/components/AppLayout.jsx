import { useCallback, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Banknote, Bell, Calculator, ChevronDown, CircleHelp, CloudDownload, FileText, Folder, Gavel, Globe, House, LogOut,
  Menu, MessageCircleQuestion, MessagesSquare, NotebookText, Search, Settings, Siren, User, Users, X, CalendarClock, FileCheck2, MessageSquareText
} from 'lucide-react'
import { Logo, useClickOutside } from './common'
import { WhatsAppIcon } from './Icons'
import { useUI } from './UIContext'
import { useAuth } from '../context/AuthContext'
import { useQuery } from '../hooks/useApi'
import { notificationService } from '../api/services/notificationService'
import { timeAgo } from '../utils/format'
import { useOnline } from '../hooks/useOnline'

const NAV_CLIENT = [
  { to: '/dashboard', label: 'Dashboard', icon: House },
  { to: '/chat', label: 'Legal Chat', icon: MessagesSquare },
  { to: '/documents', label: 'Documents', icon: FileText },
  { to: '/vault', label: 'Legal Vault', icon: Folder },
  { to: '/case-briefs', label: 'Case Briefs', icon: NotebookText },
  { to: '/calculator', label: 'Legal Calculator', icon: Calculator },
  { to: '/legal-aid', label: 'Find a Lawyer', icon: Gavel },
  { to: '/community', label: 'Community Q&A', icon: MessageCircleQuestion },
  { to: '/emergency', label: 'Emergency Mode', icon: Siren },
  { to: '/offline', label: 'Offline Mode', icon: CloudDownload },
  { to: '/whatsapp', label: 'WhatsApp Bot', icon: WhatsAppIcon },
]

const NAV_LAWYER = [
  { to: '/lawyer', label: 'Dashboard', icon: House },
  { to: '/lawyer/profile', label: 'My Profile', icon: User },
  { to: '/lawyer/consultations', label: 'Consultations', icon: CalendarClock },
  { to: '/lawyer/payments', label: 'Payments', icon: Banknote },
]

const NAV_ADMIN = [
  { to: '/admin', label: 'Dashboard', icon: House },
  { to: '/admin/lawyers', label: 'Lawyers', icon: Gavel },
  { to: '/admin/users', label: 'Users', icon: Users },
  { to: '/admin/bookings', label: 'Bookings & Payments', icon: FileCheck2 },
]

const NAV_BY_ROLE = { client: NAV_CLIENT, lawyer: NAV_LAWYER, admin: NAV_ADMIN }

function Sidebar({ open, onClose }) {
  const { pathname } = useLocation()
  const { toast } = useUI()
  const { user } = useAuth()
  const NAV = NAV_BY_ROLE[user?.role] || NAV_CLIENT
  // Real connectivity from the browser; the Offline Mode page also shows the offline state (as in the design).
  const online = useOnline()
  const offline = !online || pathname.startsWith('/offline')
  return (
    <>
      <div className={`sidebar-scrim ${open ? 'show' : ''}`} onClick={onClose} />
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <Logo variant="light" to="/dashboard" />
          <button className="sidebar-close icon-btn-plain" onClick={onClose} aria-label="Close menu"><X size={20} /></button>
        </div>
        <nav className="sidebar-nav">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} onClick={onClose}
              className={() => `side-link ${pathname.startsWith(to) ? 'active' : ''}`}>
              <Icon size={21} strokeWidth={1.7} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="side-divider" />
          <div className="side-status"><span className={`dot ${offline ? 'dot-gray' : 'dot-green'}`} />{offline ? 'Offline' : 'Online'}</div>
          <NavLink to="/settings" onClick={onClose} className={() => `side-sub ${pathname.startsWith('/settings') ? 'active' : ''}`}>
            <Settings size={19} strokeWidth={1.7} /><span>Settings</span>
          </NavLink>
          <button className="side-sub" onClick={() => toast('Help & Support is coming soon.', 'info')}>
            <CircleHelp size={19} strokeWidth={1.7} /><span>Help &amp; Support</span>
          </button>
        </div>
        <img className="sidebar-skyline" src="/assets/img/sidebar-skyline.jpg" alt="A fairer Pakistan for all" />
      </aside>
    </>
  )
}

// Notification `type` from the API -> icon + colour
const NOTIF_STYLE = {
  deadline: { icon: CalendarClock, tone: 'red' },
  analysis: { icon: FileCheck2, tone: 'green' },
  chat: { icon: MessageSquareText, tone: 'blue' },
}

function Topbar({ onMenu }) {
  const navigate = useNavigate()
  const { language, setLanguage } = useUI()
  const { user, logout } = useAuth()
  const [menu, setMenu] = useState(null)
  const [q, setQ] = useState('')
  const close = useCallback(() => setMenu(null), [])
  const ref = useClickOutside(close)
  const notifs = useQuery(signal => notificationService.list(signal), [])
  const unread = notifs.data?.unreadCount ?? 0

  const markAll = async () => {
    notifs.setData(d => ({ ...d, unreadCount: 0, items: d.items.map(n => ({ ...n, read: true })) }))
    await notificationService.markAllRead().catch(() => notifs.reload())
  }

  const openNotif = n => {
    close()
    if (!n.read) {
      notifs.setData(d => ({ ...d, unreadCount: Math.max(0, d.unreadCount - 1), items: d.items.map(x => (x.id === n.id ? { ...x, read: true } : x)) }))
      notificationService.markRead(n.id).catch(() => {})
    }
  }

  const signOut = async () => {
    close()
    await logout()
    navigate('/login', { replace: true })
  }

  // The global search asks LegalMate; the chat page creates a new conversation from ?q=
  const submit = e => {
    e.preventDefault()
    if (!q.trim()) return
    navigate(`/chat?q=${encodeURIComponent(q.trim())}`)
    setQ('')
  }

  return (
    <header className="topbar" ref={ref}>
      <button className="icon-btn-plain menu-btn" onClick={onMenu} aria-label="Open menu"><Menu size={22} /></button>
      <form className="top-search" onSubmit={submit}>
        <Search size={18} />
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search for laws, documents, or ask anything..." aria-label="Search" />
      </form>
      <div className="top-actions">
        <div className="top-pop">
          <button className="icon-btn-plain bell" aria-label="Notifications" onClick={() => setMenu(menu === 'n' ? null : 'n')}>
            <Bell size={22} strokeWidth={1.7} />
            {unread > 0 && <span className="bell-badge">{unread}</span>}
          </button>
          {menu === 'n' && (
            <div className="popover popover-notifs">
              <div className="popover-head"><b>Notifications</b><button className="link-btn" onClick={markAll}>Mark all as read</button></div>
              {notifs.loading && !notifs.data && <p className="notif-empty">Loading…</p>}
              {notifs.data?.items.length === 0 && <p className="notif-empty">You're all caught up.</p>}
              {notifs.data?.items.map(n => {
                const s = NOTIF_STYLE[n.type] || NOTIF_STYLE.chat
                return (
                  <Link key={n.id} to={n.link || '/dashboard'} className={`notif ${n.read ? 'read' : ''}`} onClick={() => openNotif(n)}>
                    <span className={`icon-tile tile-${s.tone} tile-sm`}><s.icon /></span>
                    <span className="notif-body"><b>{n.title}</b><span>{n.text}</span></span>
                    <span className="notif-time">{n.timeLabel || timeAgo(n.createdAt)}</span>
                  </Link>
                )
              })}
            </div>
          )}
        </div>
        <div className="top-pop">
          <button className="top-lang" onClick={() => setMenu(menu === 'l' ? null : 'l')}>
            <Globe size={20} strokeWidth={1.7} /><span>{language}</span><ChevronDown size={16} />
          </button>
          {menu === 'l' && (
            <div className="popover popover-sm">
              {['English', 'اردو'].map(l => (
                <button key={l} className={`popover-item ${l === language ? 'active' : ''}`} onClick={() => { setLanguage(l); close() }}>{l}</button>
              ))}
            </div>
          )}
        </div>
        <span className="top-divider" />
        <div className="top-pop">
          <button className="top-user" onClick={() => setMenu(menu === 'u' ? null : 'u')}>
            {user?.avatarUrl ? <img className="avatar" src={user.avatarUrl} alt="" /> : <span className="avatar">{user?.initials}</span>}
            <span className="top-user-text"><b>{user?.name}</b><span>{user?.roleLabel}</span></span>
            <ChevronDown size={17} />
          </button>
          {menu === 'u' && (
            <div className="popover popover-user">
              <Link className="popover-item" to="/settings" onClick={close}><User size={16} />My Profile</Link>
              <Link className="popover-item" to="/settings" onClick={close}><Settings size={16} />Settings</Link>
              <div className="popover-sep" />
              <button className="popover-item danger" onClick={signOut}><LogOut size={16} />Log out</button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default function AppLayout() {
  const [open, setOpen] = useState(false)
  return (
    <div className="app">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="app-main">
        <Topbar onMenu={() => setOpen(true)} />
        <main className="app-content"><Outlet /></main>
      </div>
    </div>
  )
}
