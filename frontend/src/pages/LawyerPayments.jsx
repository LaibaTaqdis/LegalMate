import { Banknote, CheckCircle2, Clock3 } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { PageSkeleton, ErrorState, EmptyState } from '../components/States'
import { useAuth } from '../context/AuthContext'
import { useQuery } from '../hooks/useApi'
import { lawyerService } from '../api/services/lawyerService'
import { pkr } from '../utils/format'

const PAY_PILL = { unpaid: 'pill-gray', cash_pending: 'pill-orange', bank_pending_verification: 'pill-amber', paid: 'pill-green' }
const PAY_LABEL = { unpaid: 'Unpaid', cash_pending: 'Cash at appointment', bank_pending_verification: 'Awaiting verification', paid: 'Paid' }

export default function LawyerPayments() {
  const { user } = useAuth()
  const query = useQuery(signal => lawyerService.earningsFor(user.lawyerId, signal), [user.lawyerId])

  if (!query.data) {
    if (query.error) return <ErrorState error={query.error} onRetry={query.reload} />
    return <PageSkeleton cards={3} rows={1} />
  }
  const { totalEarned, pending, completedCount, items } = query.data
  const history = [...items].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))

  return (
    <div className="adm lp">
      <Breadcrumb items={[{ label: 'Lawyer Portal', to: '/lawyer' }, { label: 'Payments' }]} />
      <h1 className="page-title">Payments</h1>
      <p className="page-sub">Your earnings from consultations on LegalMate.</p>

      <div className="adm-tiles lp-pay-tiles">
        <div className="card adm-tile">
          <span className="icon-tile tile-green tile-md"><Banknote /></span>
          <div><b>{pkr(totalEarned)}</b><span>Total Earned</span></div>
        </div>
        <div className="card adm-tile">
          <span className="icon-tile tile-orange tile-md"><Clock3 /></span>
          <div><b>{pkr(pending)}</b><span>Pending Payments</span></div>
        </div>
        <div className="card adm-tile">
          <span className="icon-tile tile-purple tile-md"><CheckCircle2 /></span>
          <div><b>{completedCount}</b><span>Completed Consultations</span></div>
        </div>
      </div>

      <section className="card card-pad">
        <h2 className="card-title lp-history-title">Payment History</h2>
        {!history.length && <EmptyState title="No payments yet" />}
        <div className="lp-pay-list">
          {history.map(b => (
            <div key={b.id} className="lp-pay-row">
              <div><b>{b.clientName}</b><span>{b.date} &middot; {b.time}</span></div>
              <span className="lp-pay-amount">{pkr(b.fee)}</span>
              <span className={`pill ${PAY_PILL[b.paymentStatus]}`}>{PAY_LABEL[b.paymentStatus]}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
