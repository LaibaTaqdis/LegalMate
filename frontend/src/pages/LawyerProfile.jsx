import { useNavigate, useParams } from 'react-router-dom'
import { Globe, MessageSquare, Monitor, Phone, ShieldCheck, ShieldQuestion, Star, Users2 } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { PageSkeleton, ErrorState } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { lawyerService } from '../api/services/lawyerService'
import { pkr, initials } from '../utils/format'

const MODE_ICON = { video: Monitor, phone: Phone, in_person: Users2 }
const MODE_LABEL = { video: 'Video', phone: 'Phone', in_person: 'In-person' }
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function nextAvailable(lawyer) {
  const now = new Date()
  for (let i = 0; i < 14; i++) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + i)
    if (lawyer.availableDays.includes(d.getDay())) {
      return `${i === 0 ? 'Today' : i === 1 ? 'Tomorrow' : WEEKDAYS[d.getDay()]}, ${lawyer.slotTimes[0]}`
    }
  }
  return 'By request'
}

export default function LawyerProfile() {
  const { id } = useParams()
  const navigate = useNavigate()
  const query = useQuery(signal => lawyerService.getLawyer(id, signal), [id])

  if (!query.data) {
    if (query.loading) return <PageSkeleton cards={0} rows={2} />
    return <ErrorState error={query.error} onRetry={query.reload} />
  }
  const l = query.data

  return (
    <div className="mk">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Find a Lawyer', to: '/legal-aid' }, { label: l.name }]} />
      <h1 className="page-title mk-profile-title">Lawyer Profile</h1>
      <p className="page-sub">Verified legal counsel matched to your case, with credentials and past client feedback.</p>

      <div className="mk-profile-grid">
        <section className="card mk-profile-main">
          <div className="mk-profile-top">
            <span className="avatar mk-avatar mk-avatar-lg">{initials(l.name)}</span>
            <div>
              <h2>{l.name} {l.verified === 'verified' ? <span className="pill pill-green mk-badge"><ShieldCheck size={13} /> Verified</span> : <span className="pill pill-amber mk-badge"><ShieldQuestion size={13} /> Verification pending</span>}</h2>
              <p className="mk-meta">{l.title} <i>&middot;</i> {l.specializations[0]}</p>
              <p className="mk-rating"><Star size={18} fill="#f59e0b" color="#f59e0b" /> {l.rating.toFixed(1)} <span>({l.reviewCount} reviews)</span> {l.experienceYears} yrs experience</p>
            </div>
          </div>

          <h3>About</h3>
          <p className="mk-bio">{l.bio}</p>

          <h3>Specializations</h3>
          <div className="mk-tags">{l.specializations.map(s => <span key={s} className="pill pill-blue">{s}</span>)}</div>

          <h3>Languages &amp; Consultation Modes</h3>
          <p className="mk-meta mk-lang"><Globe size={16} /> {l.languages.join(', ')}</p>
          <div className="mk-modes">{l.modes.map(m => { const Icon = MODE_ICON[m]; return <span key={m} className="pill pill-gray mk-mode"><Icon size={14} /> {MODE_LABEL[m]}</span> })}</div>

          <h3>Credentials</h3>
          <dl className="mk-cred-list">
            {l.credentials.map(c => <div key={c.label}><dt>{c.label}</dt><dd>{c.value}</dd></div>)}
          </dl>

          <h3>Client Reviews</h3>
          <ul className="mk-reviews">
            {l.reviews.map((r, i) => (
              <li key={i}>
                <span className="mk-review-stars">{Array.from({ length: 5 }).map((_, j) => <Star key={j} size={14} fill={j < r.rating ? '#f59e0b' : 'none'} color="#f59e0b" />)}</span>
                <p><MessageSquare size={13} /> {r.text} <i>&mdash; {r.author}</i></p>
              </li>
            ))}
          </ul>
        </section>

        <aside className="card card-pad mk-book-card">
          <h3 className="card-title">Book a consultation</h3>
          <p className="mk-next-avail">Next available: <b>{nextAvailable(l)}</b></p>
          <div className="mk-modes mk-modes-book">{l.modes.map(m => { const Icon = MODE_ICON[m]; return <span key={m} className="pill pill-orange mk-mode"><Icon size={14} /> {MODE_LABEL[m]}</span> })}</div>
          <p className="mk-price"><b>{pkr(l.fee)}</b> <span>/ 30 min</span></p>
          <button className="btn btn-orange btn-lg btn-block" onClick={() => navigate(`/find-a-lawyer/${l.id}/book`)}>Book Consultation</button>
        </aside>
      </div>
    </div>
  )
}
