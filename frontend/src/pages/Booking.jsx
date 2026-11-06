import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Loader2, Monitor, Phone, Users2 } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { useUI } from '../components/UIContext'
import { PageSkeleton, ErrorState } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { lawyerService } from '../api/services/lawyerService'
import { pkr } from '../utils/format'

const MODE_ICON = { video: Monitor, phone: Phone, in_person: Users2 }
const MODE_LABEL = { video: 'Video call', phone: 'Phone call', in_person: 'In-person' }
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
const pad2 = n => String(n).padStart(2, '0')
const isoDate = d => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
const sameDay = (a, b) => a && b && isoDate(a) === isoDate(b)

function Calendar({ lawyer, month, setMonth, selected, onSelect }) {
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const first = new Date(month.getFullYear(), month.getMonth(), 1)
  const daysInMonth = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
  const cells = [...Array(first.getDay()).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => new Date(month.getFullYear(), month.getMonth(), i + 1))]
  const isPastMonth = month.getFullYear() === today.getFullYear() && month.getMonth() === today.getMonth()

  return (
    <div className="mk-cal">
      <div className="mk-cal-head">
        <b>{MONTHS[month.getMonth()]} {month.getFullYear()}</b>
        <div className="mk-cal-nav">
          <button type="button" className="icon-btn" disabled={isPastMonth} onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))} aria-label="Previous month"><ChevronLeft size={16} /></button>
          <button type="button" className="icon-btn" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))} aria-label="Next month"><ChevronRight size={16} /></button>
        </div>
      </div>
      <div className="mk-cal-grid mk-cal-dow">{WEEKDAYS.map(w => <span key={w}>{w}</span>)}</div>
      <div className="mk-cal-grid">
        {cells.map((d, i) => {
          if (!d) return <span key={i} />
          const available = d >= today && lawyer.availableDays.includes(d.getDay())
          return (
            <button type="button" key={i} disabled={!available} className={`mk-day ${sameDay(d, selected) ? 'active' : ''}`} onClick={() => onSelect(d)}>
              {d.getDate()}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function Booking() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast } = useUI()
  const query = useQuery(signal => lawyerService.getLawyer(id, signal), [id])
  const [month, setMonth] = useState(() => { const d = new Date(); d.setDate(1); return d })
  const [date, setDate] = useState(null)
  const [time, setTime] = useState(null)
  const [type, setType] = useState(null)
  const [busy, setBusy] = useState(false)

  const lawyer = query.data
  const totals = useMemo(() => (lawyer ? { fee: lawyer.fee, platformFee: 150, total: lawyer.fee + 150 } : null), [lawyer])

  const selectDate = d => { setDate(d); setTime(null) }

  const confirm = async () => {
    setBusy(true)
    try {
      const booking = await lawyerService.createBooking({ lawyerId: id, date: isoDate(date), time, type })
      navigate(`/find-a-lawyer/${id}/pay/${booking.id}`)
    } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }

  if (!lawyer) {
    if (query.loading) return <PageSkeleton cards={0} rows={2} />
    return <ErrorState error={query.error} onRetry={query.reload} />
  }

  return (
    <div className="mk">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Find a Lawyer', to: '/legal-aid' }, { label: lawyer.name, to: `/find-a-lawyer/${id}` }, { label: 'Booking' }]} />
      <h1 className="page-title mk-profile-title">Booking</h1>
      <p className="page-sub">Pick a slot with {lawyer.name} and choose how you'd like to meet.</p>

      <div className="mk-profile-grid">
        <section className="card card-pad mk-booking-main">
          <Calendar lawyer={lawyer} month={month} setMonth={setMonth} selected={date} onSelect={selectDate} />

          {date && (
            <>
              <h3 className="mk-book-h3">Available times &mdash; {MONTHS[date.getMonth()].slice(0, 3)} {date.getDate()}</h3>
              <div className="mk-slots">
                {lawyer.slotTimes.map(t => (
                  <button type="button" key={t} className={`mk-slot ${time === t ? 'active' : ''}`} onClick={() => setTime(t)}>{t}</button>
                ))}
              </div>
            </>
          )}

          <h3 className="mk-book-h3">Consultation type</h3>
          <div className="mk-modes">
            {lawyer.modes.map(m => { const Icon = MODE_ICON[m]; return <button type="button" key={m} className={`pill pill-gray mk-mode mk-mode-btn ${type === m ? 'active' : ''}`} onClick={() => setType(m)}><Icon size={14} /> {MODE_LABEL[m]}</button> })}
          </div>
        </section>

        <aside className="card card-pad mk-summary">
          <h3 className="card-title">Booking summary</h3>
          <div className="mk-sum-row"><span>Lawyer</span><b>{lawyer.name}</b></div>
          <div className="mk-sum-row"><span>Date</span><b>{date ? `${MONTHS[date.getMonth()].slice(0, 3)} ${date.getDate()}, ${date.getFullYear()}` : 'Select a date'}</b></div>
          <div className="mk-sum-row"><span>Time</span><b>{time || '—'}</b></div>
          <div className="mk-sum-row"><span>Duration</span><b>30 minutes</b></div>
          <div className="mk-sum-row"><span>Consultation type</span><b>{type ? MODE_LABEL[type] : '—'}</b></div>
          <div className="mk-sum-sep" />
          <div className="mk-sum-row"><span>Consultation fee</span><b>{pkr(totals.fee)}</b></div>
          <div className="mk-sum-row"><span>Platform fee</span><b>{pkr(totals.platformFee)}</b></div>
          <div className="mk-sum-row mk-sum-total"><span>Total</span><b>{pkr(totals.total)}</b></div>
          <button className="btn btn-orange btn-lg btn-block" disabled={!date || !time || !type || busy} onClick={confirm}>
            {busy ? <Loader2 size={18} className="spin" /> : null} Confirm &amp; Continue to Payment
          </button>
        </aside>
      </div>
    </div>
  )
}
