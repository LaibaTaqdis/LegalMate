import { useState } from 'react'
import { CheckCheck, Monitor, Phone, Users2 } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { useUI } from '../components/UIContext'
import { PageSkeleton, ErrorState, EmptyState } from '../components/States'
import { useAuth } from '../context/AuthContext'
import { useQuery } from '../hooks/useApi'
import { lawyerService } from '../api/services/lawyerService'
import { pkr, initials } from '../utils/format'

const MODE_ICON = { video: Monitor, phone: Phone, in_person: Users2 }
const MODE_LABEL = { video: 'Video call', phone: 'Phone call', in_person: 'In-person' }
const PAY_PILL = { unpaid: 'pill-gray', cash_pending: 'pill-orange', bank_pending_verification: 'pill-amber', paid: 'pill-green' }
const PAY_LABEL = { unpaid: 'Unpaid', cash_pending: 'Cash at appointment', bank_pending_verification: 'Awaiting verification', paid: 'Paid' }
const TABS = ['Upcoming', 'Completed']

export default function LawyerConsultations() {
  const { user } = useAuth()
  const { toast } = useUI()
  const [tab, setTab] = useState('Upcoming')
  const query = useQuery(signal => lawyerService.consultationsFor(user.lawyerId, signal), [user.lawyerId])

  const complete = async b => {
    query.setData(d => ({ ...d, items: d.items.map(x => (x.id === b.id ? { ...x, status: 'completed', paymentStatus: x.paymentMethod === 'cash' ? 'paid' : x.paymentStatus } : x)) }))
    try {
      await lawyerService.completeBooking(b.id)
      toast(`Marked your consultation with ${b.clientName} as completed.`)
    } catch (err) { query.reload(); toast(err.message, 'info') }
  }

  if (!query.data) {
    if (query.error) return <ErrorState error={query.error} onRetry={query.reload} />
    return <PageSkeleton cards={0} rows={2} />
  }
  const bookings = query.data.items
    .filter(b => (tab === 'Upcoming' ? b.status === 'confirmed' : b.status === 'completed'))
    .sort((a, b) => new Date(`${a.date}T00:00`) - new Date(`${b.date}T00:00`))

  return (
    <div className="lp">
      <Breadcrumb items={[{ label: 'Lawyer Portal', to: '/lawyer' }, { label: 'Consultations' }]} />
      <h1 className="page-title">Consultations</h1>
      <p className="page-sub">Your upcoming and past bookings with clients.</p>

      <div className="seg adm-seg">
        {TABS.map(t => <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>{t}</button>)}
      </div>

      {!bookings.length && <EmptyState title={`No ${tab.toLowerCase()} consultations`} />}

      <div className="lp-consult-list">
        {bookings.map(b => {
          const Icon = MODE_ICON[b.type]
          return (
            <div key={b.id} className="card lp-consult-card">
              <span className="avatar mk-avatar">{initials(b.clientName)}</span>
              <div className="lp-consult-main">
                <b>{b.clientName}</b>
                <span><Icon size={14} /> {MODE_LABEL[b.type]} <i>&middot;</i> {b.date} &middot; {b.time}</span>
              </div>
              <div className="lp-consult-side">
                <span className="lp-consult-fee">{pkr(b.fee)}</span>
                <span className={`pill ${PAY_PILL[b.paymentStatus]}`}>{PAY_LABEL[b.paymentStatus]}</span>
              </div>
              {tab === 'Upcoming' && <button className="btn btn-green-soft btn-sm" onClick={() => complete(b)}><CheckCheck size={14} /> Mark Completed</button>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
