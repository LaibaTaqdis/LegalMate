import { Link } from 'react-router-dom'
import { ArrowRight, Banknote, CalendarClock, CheckCircle2, Hourglass, ShieldCheck, ShieldQuestion, ShieldX, User } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { PageSkeleton, ErrorState, EmptyState } from '../components/States'
import { useAuth } from '../context/AuthContext'
import { useQuery } from '../hooks/useApi'
import { lawyerService } from '../api/services/lawyerService'
import { pkr } from '../utils/format'

const MODE_LABEL = { video: 'Video call', phone: 'Phone call', in_person: 'In-person' }

const QUICK = [
  { to: '/lawyer/profile', label: 'My Profile', text: 'Update your bio, fee, specializations and availability.', icon: User },
  { to: '/lawyer/consultations', label: 'Consultations', text: 'See upcoming and past bookings.', icon: CalendarClock },
  { to: '/lawyer/payments', label: 'Payments', text: 'Track your earnings and pending payments.', icon: Banknote },
]

export default function LawyerDashboard() {
  const { user } = useAuth()
  const profileQ = useQuery(signal => lawyerService.getLawyer(user.lawyerId, signal), [user.lawyerId])
  const consultQ = useQuery(signal => lawyerService.consultationsFor(user.lawyerId, signal), [user.lawyerId])

  if (!profileQ.data || !consultQ.data) {
    if (profileQ.loading || consultQ.loading) return <PageSkeleton cards={3} rows={1} />
    return <ErrorState error={profileQ.error || consultQ.error} onRetry={() => { profileQ.reload(); consultQ.reload() }} />
  }
  const lawyer = profileQ.data
  const upcoming = consultQ.data.items.filter(b => b.status === 'confirmed').sort((a, b) => new Date(`${a.date}T00:00`) - new Date(`${b.date}T00:00`))
  const completedCount = consultQ.data.items.filter(b => b.status === 'completed').length
  const earned = consultQ.data.items.filter(b => b.paymentStatus === 'paid').reduce((s, b) => s + b.fee, 0)

  return (
    <div className="adm lp">
      <Breadcrumb items={[{ label: 'Lawyer Portal' }, { label: 'Dashboard' }]} />
      <h1 className="page-title">Welcome, {user.firstName}</h1>
      <p className="page-sub">Here's how your practice on LegalMate is doing.</p>

      {lawyer.verified === 'pending' && (
        <div className="lp-pending-banner">
          <Hourglass size={28} />
          <div><b>Your application is pending review</b><span>The LegalMate team is reviewing your profile. You can keep filling in your profile and availability while you wait — you'll be notified once you're approved and visible to clients.</span></div>
        </div>
      )}
      {lawyer.verified === 'rejected' && (
        <div className="lp-pending-banner lp-rejected-banner">
          <ShieldX size={28} />
          <div><b>Your application was not approved</b><span>Update your profile details and reach out to LegalMate support if you'd like it reconsidered.</span></div>
        </div>
      )}

      <div className="adm-tiles">
        <div className="card adm-tile">
          <span className={`icon-tile ${lawyer.verified === 'verified' ? 'tile-green' : 'tile-orange'} tile-md`}>{lawyer.verified === 'verified' ? <ShieldCheck /> : <ShieldQuestion />}</span>
          <div><b>{lawyer.verified === 'verified' ? 'Verified' : lawyer.verified === 'rejected' ? 'Rejected' : 'Pending'}</b><span>Verification status</span></div>
        </div>
        <div className="card adm-tile">
          <span className="icon-tile tile-blue tile-md"><CalendarClock /></span>
          <div><b>{upcoming.length}</b><span>Upcoming Consultations</span></div>
        </div>
        <div className="card adm-tile">
          <span className="icon-tile tile-purple tile-md"><CheckCircle2 /></span>
          <div><b>{completedCount}</b><span>Completed Consultations</span></div>
        </div>
        <div className="card adm-tile">
          <span className="icon-tile tile-green tile-md"><Banknote /></span>
          <div><b>{pkr(earned)}</b><span>Total Earned</span></div>
        </div>
      </div>

      <section className="card card-pad lp-upcoming">
        <div className="card-head"><h2 className="card-title">Upcoming Consultations</h2><Link to="/lawyer/consultations" className="link small">View All <ArrowRight size={15} /></Link></div>
        {!upcoming.length && <EmptyState title="Nothing booked yet" text="New consultations from clients will show up here." />}
        <ul className="lp-list">
          {upcoming.slice(0, 4).map(b => (
            <li key={b.id} className="lp-row">
              <span className="avatar mk-avatar">{b.clientName.split(' ').map(w => w[0]).slice(0, 2).join('')}</span>
              <div className="lp-row-main"><b>{b.clientName}</b><span>{MODE_LABEL[b.type]}</span></div>
              <span className="lp-row-time">{b.date} &middot; {b.time}</span>
            </li>
          ))}
        </ul>
      </section>

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
