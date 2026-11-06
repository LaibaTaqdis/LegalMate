import { Check, Globe, X } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { useUI } from '../components/UIContext'
import { PageSkeleton, ErrorState, EmptyState } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { adminService } from '../api/services/adminService'
import { pkr, initials } from '../utils/format'

const MODE_LABEL = { video: 'Video call', phone: 'Phone call', in_person: 'In-person' }

export default function AdminLawyerApplications() {
  const { toast } = useUI()
  const query = useQuery(signal => adminService.lawyers(signal), [])

  const decide = async (l, status) => {
    query.setData(d => ({ ...d, items: d.items.map(x => (x.id === l.id ? { ...x, verified: status } : x)) }))
    try {
      await adminService.setLawyerStatus(l.id, status)
      toast(status === 'verified' ? `${l.name} has been approved and is now live on LegalMate.` : `${l.name}'s application was rejected.`)
    } catch (err) { query.reload(); toast(err.message, 'info') }
  }

  if (!query.data) {
    if (query.error) return <ErrorState error={query.error} onRetry={query.reload} />
    return <PageSkeleton cards={0} rows={2} />
  }
  const pending = query.data.items.filter(l => l.verified === 'pending')

  return (
    <div className="adm">
      <Breadcrumb items={[{ label: 'Admin', to: '/admin' }, { label: 'Lawyers', to: '/admin/lawyers' }, { label: 'Pending Applications' }]} />
      <h1 className="page-title">Pending Applications</h1>
      <p className="page-sub">New lawyer sign-ups awaiting review before they go live on LegalMate.</p>

      {!pending.length && <EmptyState title="No pending applications" text="New lawyer sign-ups will show up here for review." />}

      <div className="adm-app-list">
        {pending.map(l => (
          <div key={l.id} className="card card-pad adm-app-card">
            <div className="adm-app-head">
              <span className="avatar mk-avatar mk-avatar-lg">{initials(l.name)}</span>
              <div className="adm-app-main">
                <b>{l.name}</b>
                <span className="muted small">{l.title} &middot; {l.city} &middot; {pkr(l.fee)} / 30 min</span>
                <p>{l.bio}</p>
                <div className="mk-tags adm-app-tags">{l.specializations.map(sp => <span key={sp} className="pill pill-blue">{sp}</span>)}</div>
                <p className="adm-app-meta"><Globe size={14} /> {l.languages.join(', ')} <i>&middot;</i> {l.modes.map(m => MODE_LABEL[m]).join(', ')}</p>
              </div>
              <div className="adm-app-actions">
                <button className="btn btn-green-soft btn-sm" onClick={() => decide(l, 'verified')}><Check size={14} /> Approve</button>
                <button className="btn btn-danger-soft btn-sm" onClick={() => decide(l, 'rejected')}><X size={14} /> Reject</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
