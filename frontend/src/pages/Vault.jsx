import { useSearchParams } from 'react-router-dom'
import { Bookmark, FolderOpen } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import FilesTab from './vault/FilesTab'
import SavedTab from './vault/SavedTab'

const TABS = [
  { key: 'saved', label: 'Saved', sub: 'Answers and analyses', icon: Bookmark },
  { key: 'files', label: 'My Files', sub: 'Your own documents', icon: FolderOpen },
]

/** The Legal Vault has two independent parts: what you saved from LegalMate, and your own files. */
export default function Vault() {
  const [params, setParams] = useSearchParams()
  const tab = TABS.some(t => t.key === params.get('tab')) ? params.get('tab') : 'saved'
  const choose = key => setParams(key === 'saved' ? {} : { tab: key }, { replace: true })
  return (
    <div className="vault">
      <div className="vault-head">
        <div>
          <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Legal Vault' }]} />
          <h1 className="page-title">Legal Vault</h1>
          <p className="page-sub vault-sub">Everything you want to keep, in one private place.</p>
        </div>
      </div>
      <div className="vault-tabs" role="tablist">
        {TABS.map(t => (
          <button key={t.key} role="tab" aria-selected={tab === t.key} className={tab === t.key ? 'active' : ''} onClick={() => choose(t.key)}>
            <t.icon size={19} /><span><b>{t.label}</b><small>{t.sub}</small></span>
          </button>
        ))}
      </div>
      {tab === 'saved' ? <SavedTab /> : <FilesTab />}
    </div>
  )
}
