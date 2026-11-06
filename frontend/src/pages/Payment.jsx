import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Banknote, CheckCircle2, Landmark, Loader2 } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { useUI } from '../components/UIContext'
import { PageSkeleton, ErrorState } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { lawyerService } from '../api/services/lawyerService'
import { pkr } from '../utils/format'

const MODE_LABEL = { video: 'Video call', phone: 'Phone call', in_person: 'In-person' }
const BANK = { bank: 'Meezan Bank', accountTitle: 'LegalMate (Private) Limited', accountNumber: '0110-1234567-89', iban: 'PK36 MEZN 0001 1012 3456 789' }

const METHODS = [
  { key: 'cash', icon: Banknote, label: 'Cash', text: "Pay the lawyer directly, in person, at the time of your consultation." },
  { key: 'bank_transfer', icon: Landmark, label: 'Bank Transfer', text: 'Transfer to our account and confirm here — we verify it before your consultation.' },
]

export default function Payment() {
  const { id, bookingId } = useParams()
  const { toast } = useUI()
  const query = useQuery(signal => lawyerService.getBooking(bookingId, signal), [bookingId])
  const [method, setMethod] = useState(null)
  const [busy, setBusy] = useState(false)

  if (!query.data) {
    if (query.loading) return <PageSkeleton cards={0} rows={1} />
    return <ErrorState error={query.error} onRetry={query.reload} />
  }
  const booking = query.data
  const paid = booking.paymentStatus !== 'unpaid'

  const confirm = async () => {
    setBusy(true)
    try {
      await lawyerService.payBooking(bookingId, { method })
      query.setData(b => ({ ...b, paymentMethod: method, paymentStatus: method === 'cash' ? 'cash_pending' : 'bank_pending_verification', status: 'confirmed' }))
      toast(method === 'cash' ? 'Booking confirmed. Pay the lawyer directly at your appointment.' : "Thanks — we'll verify your transfer and confirm your booking shortly.")
    } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }

  return (
    <div className="mk">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Find a Lawyer', to: '/legal-aid' }, { label: booking.lawyerName, to: `/find-a-lawyer/${id}` }, { label: 'Payment' }]} />
      <h1 className="page-title mk-profile-title">Payment</h1>
      <p className="page-sub">Choose how you'd like to pay {booking.lawyerName} for this consultation. No card is required.</p>

      <div className="mk-profile-grid">
        <section className="card card-pad mk-pay-main">
          {paid ? (
            <div className="mk-pay-done">
              <span className="icon-tile tile-green tile-lg"><CheckCircle2 /></span>
              <h3>Booking confirmed</h3>
              <p>{booking.paymentMethod === 'cash' ? `Pay ${pkr(booking.total)} directly to ${booking.lawyerName} at the time of your consultation.` : "We're verifying your bank transfer — you'll be notified as soon as it's confirmed."}</p>
              <Link to="/dashboard" className="btn btn-navy btn-lg">Back to Dashboard</Link>
            </div>
          ) : (
            <>
              <h3 className="mk-book-h3">Payment method</h3>
              <div className="mk-methods">
                {METHODS.map(m => (
                  <button type="button" key={m.key} className={`card mk-method ${method === m.key ? 'active' : ''}`} onClick={() => setMethod(m.key)}>
                    <span className="icon-tile tile-blue tile-md"><m.icon /></span>
                    <div><b>{m.label}</b><span>{m.text}</span></div>
                  </button>
                ))}
              </div>

              {method === 'cash' && (
                <div className="mk-cash-note">
                  <p>You'll pay <b>{pkr(booking.total)}</b> directly to {booking.lawyerName} when your consultation happens. Your slot is reserved as soon as you confirm below.</p>
                </div>
              )}

              {method === 'bank_transfer' && (
                <div className="mk-bank">
                  <dl>
                    <div><dt>Bank</dt><dd>{BANK.bank}</dd></div>
                    <div><dt>Account title</dt><dd>{BANK.accountTitle}</dd></div>
                    <div><dt>Account number</dt><dd>{BANK.accountNumber}</dd></div>
                    <div><dt>IBAN</dt><dd>{BANK.iban}</dd></div>
                    <div><dt>Reference</dt><dd>{booking.id}</dd></div>
                  </dl>
                  <p className="mk-bank-note">Transfer <b>{pkr(booking.total)}</b> with the reference above, then confirm below. We verify transfers before your consultation and will notify you once it's confirmed.</p>
                </div>
              )}

              <button className="btn btn-orange btn-lg btn-block mk-pay-btn" disabled={!method || busy} onClick={confirm}>
                {busy ? <Loader2 size={18} className="spin" /> : null} {method === 'bank_transfer' ? "I've Sent the Payment" : 'Confirm Booking'}
              </button>
            </>
          )}
        </section>

        <aside className="card card-pad mk-summary">
          <h3 className="card-title">Order summary</h3>
          <div className="mk-sum-row"><span>Lawyer</span><b>{booking.lawyerName}</b></div>
          <div className="mk-sum-row"><span>Consultation</span><b>{MODE_LABEL[booking.type]}</b></div>
          <div className="mk-sum-row"><span>Date &amp; time</span><b>{booking.date} &middot; {booking.time}</b></div>
          <div className="mk-sum-sep" />
          <div className="mk-sum-row"><span>Consultation fee</span><b>{pkr(booking.fee)}</b></div>
          <div className="mk-sum-row"><span>Platform fee</span><b>{pkr(booking.platformFee)}</b></div>
          <div className="mk-sum-row mk-sum-total"><span>Total</span><b>{pkr(booking.total)}</b></div>
        </aside>
      </div>
    </div>
  )
}
