import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Eye, Globe, ShieldCheck, ShieldX, UserRoundCheck, X } from 'lucide-react'
import { Breadcrumb, Modal } from '../components/common'
import { PageSkeleton, ErrorState, EmptyState } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { adminService } from '../api/services/adminService'
import { pkr, initials } from '../utils/format'

const STATUS = {
  verified: { label: 'Verified', tone: 'green', icon: ShieldCheck },
  rejected: { label: 'Rejected', tone: 'red', icon: ShieldX },
}
const MODE_LABEL = { video: 'Video call', phone: 'Phone call', in_person: 'In-person' }

function LawyerModal({ lawyer, onClose }) {
  if (!lawyer) return null
  const s = STATUS[lawyer.verified] || STATUS.verified
  return (
    <Modal open={!!lawyer} onClose={onClose} className="modal-sm adm-lawyer-modal">
      <div className="adm-lm-head">
        <span className="avatar mk-avatar mk-avatar-lg">{initials(lawyer.name)}</span>
        <div>
          <b>{lawyer.name}</b>
          <span className="muted small">{lawyer.title} &middot; {lawyer.city}</span>
          <span className={`pill pill-${s.tone} adm-lm-status`}><s.icon size={13} /> {s.label}</span>
        </div>
        <button type="button" className="icon-btn-plain" onClick={onClose} aria-label="Close"><X size={20} /></button>
      </div>
      <div className="adm-lm-body">
        <p>{lawyer.bio}</p>
        <div className="adm-lm-row"><span>Fee</span><b>{pkr(lawyer.fee)} / 30 min</b></div>
        <div className="adm-lm-row"><span>Specializations</span><b>{lawyer.specializations.join(', ')}</b></div>
        <div className="adm-lm-row"><span><Globe size={14} /> Languages</span><b>{lawyer.languages.join(', ')}</b></div>
        <div className="adm-lm-row"><span>Consultation modes</span><b>{lawyer.modes.map(m => MODE_LABEL[m]).join(', ')}</b></div>
        <h4>Credentials</h4>
        <dl className="mk-cred-list">
          {lawyer.credentials.map(c => <div key={c.label}><dt>{c.label}</dt><dd>{c.value}</dd></div>)}
          {!lawyer.credentials.length && <p className="muted small">No credentials on file yet.</p>}
        </dl>
      </div>
    </Modal>
  )
}

export default function AdminLawyers() {
  const query = useQuery(signal => adminService.lawyers(signal), [])
  const [viewing, setViewing] = useState(null)

  if (!query.data) {
    if (query.error) return <ErrorState error={query.error} onRetry={query.reload} />
    return <PageSkeleton cards={0} rows={2} />
  }
  const all = query.data.items
  const directory = all.filter(l => l.verified !== 'pending')
  const pendingCount = all.filter(l => l.verified === 'pending').length

  return (
    <div className="adm">
      <div className="page-head">
        <div>
          <Breadcrumb items={[{ label: 'Admin', to: '/admin' }, { label: 'Lawyers' }]} />
          <h1 className="page-title">Lawyers</h1>
          <p className="page-sub">The verified lawyer directory on LegalMate.</p>
        </div>
        <Link to="/admin/lawyers/pending" className="btn btn-orange adm-pending-btn">
          <UserRoundCheck size={17} /> Pending Applications {pendingCount > 0 && <span className="adm-pending-badge">{pendingCount}</span>}
        </Link>
      </div>

      {!directory.length && <EmptyState title="No lawyers yet" text="Onboarded lawyers will appear here once approved." />}

      <div className="card adm-table">
        {!!directory.length && (
          <div className="adm-row adm-row-head">
            <span>Lawyer</span><span>Specialization</span><span>City</span><span>Fee</span><span>Status</span><span>Actions</span>
          </div>
        )}
        {directory.map(l => {
          const s = STATUS[l.verified] || STATUS.verified
          return (
            <div key={l.id} className="adm-row">
              <span className="adm-who"><span className="avatar mk-avatar">{initials(l.name)}</span><b>{l.name}</b></span>
              <span className="muted">{l.specializations[0]}</span>
              <span className="muted">{l.city}</span>
              <span className="muted">{pkr(l.fee)}</span>
              <span className={`pill pill-${s.tone}`}><s.icon size={13} /> {s.label}</span>
              <span className="adm-actions">
                <button className="btn btn-outline btn-sm" onClick={() => setViewing(l)}><Eye size={14} /> View</button>
              </span>
            </div>
          )
        })}
      </div>

      <LawyerModal lawyer={viewing} onClose={() => setViewing(null)} />
    </div>
  )
}
