import { CheckCheck } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { useUI } from '../components/UIContext'
import { PageSkeleton, ErrorState } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { adminService } from '../api/services/adminService'
import { pkr } from '../utils/format'

const STATUS_PILL = { pending_payment: 'pill-gray', confirmed: 'pill-blue', completed: 'pill-green', cancelled: 'pill-red' }
const STATUS_LABEL = { pending_payment: 'Pending payment', confirmed: 'Confirmed', completed: 'Completed', cancelled: 'Cancelled' }
const PAY_PILL = { unpaid: 'pill-gray', cash_pending: 'pill-orange', bank_pending_verification: 'pill-amber', paid: 'pill-green' }
const PAY_LABEL = { unpaid: 'Unpaid', cash_pending: 'Cash at appointment', bank_pending_verification: 'Awaiting bank verification', paid: 'Paid' }

export default function AdminBookings() {
  const { toast } = useUI()
  const query = useQuery(signal => adminService.bookings(signal), [])

  const markPaid = async b => {
    query.setData(d => ({ ...d, items: d.items.map(x => (x.id === b.id ? { ...x, paymentStatus: 'paid' } : x)) }))
    try {
      await adminService.markBookingPaid(b.id)
      toast(`Marked ${b.clientName}'s payment to ${b.lawyerName} as received.`)
    } catch (err) { query.reload(); toast(err.message, 'info') }
  }

  if (!query.data) {
    if (query.error) return <ErrorState error={query.error} onRetry={query.reload} />
    return <PageSkeleton cards={0} rows={2} />
  }
  const bookings = [...query.data.items].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))

  return (
    <div className="adm">
      <Breadcrumb items={[{ label: 'Admin', to: '/admin' }, { label: 'Bookings & Payments' }]} />
      <h1 className="page-title">Bookings &amp; Payments</h1>
      <p className="page-sub">Every consultation booked on the platform, with its payment status.</p>

      <div className="card adm-table">
        <div className="adm-row adm-row-bookings adm-row-head">
          <span>Client</span><span>Lawyer</span><span>Date &amp; Time</span><span>Total</span><span>Status</span><span>Payment</span><span>Actions</span>
        </div>
        {bookings.map(b => (
          <div key={b.id} className="adm-row adm-row-bookings">
            <span><b>{b.clientName}</b></span>
            <span className="muted">{b.lawyerName}</span>
            <span className="muted">{b.date} &middot; {b.time}</span>
            <span className="muted">{pkr(b.total)}</span>
            <span><span className={`pill ${STATUS_PILL[b.status]}`}>{STATUS_LABEL[b.status]}</span></span>
            <span><span className={`pill ${PAY_PILL[b.paymentStatus]}`}>{PAY_LABEL[b.paymentStatus]}</span></span>
            <span className="adm-actions">
              {b.paymentStatus === 'bank_pending_verification' && (
                <button className="btn btn-green-soft btn-sm" onClick={() => markPaid(b)}><CheckCheck size={14} /> Mark Received</button>
              )}
            </span>
          </div>
        ))}
        {!bookings.length && <p className="muted adm-empty">No bookings yet.</p>}
      </div>
    </div>
  )
}
