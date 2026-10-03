import { useState } from 'react'
import { Ban, CheckCircle2 } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { useUI } from '../components/UIContext'
import { PageSkeleton, ErrorState } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { adminService } from '../api/services/adminService'
import { formatDate, initials } from '../utils/format'

const TABS = ['All', 'Client', 'Lawyer']
const ROLE_PILL = { client: 'pill-blue', lawyer: 'pill-purple' }

export default function AdminUsers() {
  const { toast } = useUI()
  const [tab, setTab] = useState('All')
  const query = useQuery(signal => adminService.users(signal), [])

  const toggleStatus = async u => {
    const next = u.status === 'active' ? 'suspended' : 'active'
    query.setData(d => ({ ...d, items: d.items.map(x => (x.id === u.id ? { ...x, status: next } : x)) }))
    try {
      await adminService.setUserStatus(u.id, next)
      toast(next === 'active' ? `${u.name}'s account is active again.` : `${u.name}'s account has been suspended.`)
    } catch (err) { query.reload(); toast(err.message, 'info') }
  }

  if (!query.data) {
    if (query.error) return <ErrorState error={query.error} onRetry={query.reload} />
    return <PageSkeleton cards={0} rows={2} />
  }
  const rows = query.data.items.filter(u => tab === 'All' || u.role === tab.toLowerCase())

  return (
    <div className="adm">
      <Breadcrumb items={[{ label: 'Admin', to: '/admin' }, { label: 'Users' }]} />
      <h1 className="page-title">Users</h1>
      <p className="page-sub">Manage client and lawyer accounts on the platform.</p>

      <div className="seg adm-seg">
        {TABS.map(t => <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>{t}</button>)}
      </div>

      <div className="card adm-table">
        <div className="adm-row adm-row-head adm-row-users">
          <span>User</span><span>Role</span><span>Joined</span><span>Status</span><span>Actions</span>
        </div>
        {rows.map(u => (
          <div key={u.id} className="adm-row adm-row-users">
            <span className="adm-who"><span className="avatar mk-avatar">{initials(u.name)}</span><div><b>{u.name}</b><span className="adm-email">{u.email}</span></div></span>
            <span><span className={`pill ${ROLE_PILL[u.role]}`}>{u.role === 'client' ? 'Client' : 'Lawyer'}</span></span>
            <span className="muted">{formatDate(u.joinedAt)}</span>
            <span><span className={`pill ${u.status === 'active' ? 'pill-green' : 'pill-red'}`}>{u.status === 'active' ? 'Active' : 'Suspended'}</span></span>
            <span className="adm-actions">
              {u.status === 'active'
                ? <button className="btn btn-danger-soft btn-sm" onClick={() => toggleStatus(u)}><Ban size={14} /> Suspend</button>
                : <button className="btn btn-green-soft btn-sm" onClick={() => toggleStatus(u)}><CheckCircle2 size={14} /> Activate</button>}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
