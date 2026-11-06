import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link } from 'react-router-dom'
import { ArrowRight, Banknote, CalendarClock, Gavel, ShieldAlert, Users } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { PageSkeleton, ErrorState } from '../components/States'
import { useAuth } from '../context/AuthContext'
import { useQuery } from '../hooks/useApi'
import { adminService } from '../api/services/adminService'
import { pkr } from '../utils/format'

const TILES = [
  { key: 'users', label: 'Total Users', icon: Users, tone: 'blue' },
  { key: 'pendingLawyers', label: 'Pending Lawyer Applications', icon: ShieldAlert, tone: 'orange' },
  { key: 'activeBookings', label: 'Active Bookings', icon: CalendarClock, tone: 'green' },
  { key: 'revenueMonth', label: 'Revenue This Month', icon: Banknote, tone: 'purple', money: true },
]

const QUICK = [
  { to: '/admin/lawyers', label: 'Verify Lawyers', text: 'Review pending applications and manage the directory.', icon: Gavel },
  { to: '/admin/users', label: 'Manage Users', text: 'Activate or suspend client and lawyer accounts.', icon: Users },
  { to: '/admin/bookings', label: 'Bookings & Payments', text: 'See every booking and confirm bank transfers.', icon: Banknote },
]

export default function AdminDashboard() {
  const { user } = useAuth()
  const query = useQuery(signal => adminService.stats(signal), [])

  if (!query.data) {
    if (query.error) return <ErrorState error={query.error} onRetry={query.reload} />
    return <PageSkeleton cards={4} rows={2} />
  }
  const { totals, deltas, trend, recentActivity } = query.data

  return (
    <div className="adm">
      <Breadcrumb items={[{ label: 'Admin' }, { label: 'Dashboard' }]} />
      <h1 className="page-title">Welcome, {user?.firstName}</h1>
      <p className="page-sub">Track your legal operations, lawyer verification and platform activity in one place.</p>

      <div className="adm-tiles">
        {TILES.map(t => (
          <div key={t.key} className="card adm-tile">
            <span className={`icon-tile tile-${t.tone} tile-md`}><t.icon /></span>
            <div>
              <b>{t.money ? pkr(totals[t.key]) : totals[t.key]}</b>
              <span>{t.label}</span>
              {deltas[t.key === 'revenueMonth' ? 'revenue' : t.key] && <i>{deltas[t.key === 'revenueMonth' ? 'revenue' : t.key]}</i>}
            </div>
          </div>
        ))}
      </div>

      <div className="adm-mid">
        <section className="card card-pad adm-chart">
          <div className="card-head"><h2 className="card-title">Bookings This Week</h2></div>
          <div className="adm-chart-wrap">
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={trend} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <defs>
                  <linearGradient id="admBookings" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="#edf1f6" />
                <XAxis dataKey="day" tickLine={false} axisLine={false} tick={{ fontSize: 12.5, fill: '#64748b' }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12.5, fill: '#64748b' }} allowDecimals={false} width={28} />
                <Tooltip contentStyle={{ borderRadius: 10, border: '1px solid #e2e8f0', fontSize: 13 }} />
                <Area type="monotone" dataKey="bookings" stroke="#f59e0b" strokeWidth={2.5} fill="url(#admBookings)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="card card-pad adm-activity">
          <div className="card-head"><h2 className="card-title">Recent Activity</h2></div>
          <ul className="adm-activity-list">
            {recentActivity.map(a => <li key={a.id}><span>{a.text}</span><i>{a.timeLabel}</i></li>)}
          </ul>
        </section>
      </div>

      <div className="adm-quick">
        {QUICK.map(q => (
          <Link to={q.to} key={q.to} className="card adm-qcard">
            <span className="icon-tile tile-navy tile-md"><q.icon /></span>
            <div><b>{q.label}</b><span>{q.text}</span></div>
            <ArrowRight size={18} className="adm-qarrow" />
          </Link>
        ))}
      </div>
    </div>
  )
}
