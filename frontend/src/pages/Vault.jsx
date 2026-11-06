import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, CheckCircle2, ChevronDown, Crown, FileText, Filter, Folder, FolderPlus, LayoutGrid, List,
  Loader2, MoreVertical, Plus, Scale, Search, ShieldCheck, Star, Trash2, Users, X, FileArchive
} from 'lucide-react'
import { Breadcrumb, Modal, useClickOutside } from '../components/common'
import { FileIcon, FolderIcon } from '../components/Icons'
import { useUI } from '../components/UIContext'
import { ErrorState, Skeleton } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { useDebounced } from '../hooks/useDebounced'
import { vaultService } from '../api/services/vaultService'
import { formatBytes, formatDate } from '../utils/format'

const CATEGORIES = [
  { key: 'all', label: 'All Files', icon: Folder },
  { key: 'Contracts', label: 'Contracts', icon: FileText },
  { key: 'Notices', label: 'Notices', icon: FileArchive },
  { key: 'Court Documents', label: 'Court Documents', icon: Scale },
  { key: 'Case Briefs', label: 'Case Briefs', icon: FileText },
  { key: 'shared', label: 'Shared with Me', icon: Users },
  { key: 'favourites', label: 'Favourites', icon: Star },
  { key: 'trash', label: 'Trash', icon: Trash2 },
]

// Label shown in the UI -> `sort` query value sent to the API
const SORTS = [
  ['Updated (Newest)', 'updated_desc'],
  ['Updated (Oldest)', 'updated_asc'],
  ['Name (A–Z)', 'name_asc'],
  ['Name (Z–A)', 'name_desc'],
]
const STATUS_FILTERS = [['All', null], ['Analysed', 'analysed'], ['Secure', 'secure']]

export default function Vault() {
  const navigate = useNavigate()
  const { toast } = useUI()
  const fileRef = useRef(null)
  const [view, setView] = useState('grid')
  const [cat, setCat] = useState('all')
  const [q, setQ] = useState('')
  const [folder, setFolder] = useState(null) // folder object
  const [sort, setSort] = useState(SORTS[0])
  const [sortOpen, setSortOpen] = useState(false)
  const [filterOpen, setFilterOpen] = useState(false)
  const [statusFilter, setStatusFilter] = useState(STATUS_FILTERS[0])
  const [menu, setMenu] = useState(null)
  const [newFolder, setNewFolder] = useState(null)
  const [uploading, setUploading] = useState(0)
  const [creating, setCreating] = useState(false)
  const sortRef = useClickOutside(() => setSortOpen(false))
  const filterRef = useClickOutside(() => setFilterOpen(false))
  const search = useDebounced(q, 300)

  const stats = useQuery(signal => vaultService.getStats(signal), [])
  const folders = useQuery(signal => vaultService.listFolders(signal), [])
  const docs = useQuery(
    signal => vaultService.listDocuments({ category: cat, folderId: folder?.id, q: search || undefined, status: statusFilter[1] || undefined, sort: sort[1] }, signal),
    [cat, folder?.id, search, statusFilter[1], sort[1]],
  )
  const items = docs.data?.items || []

  const open = d => navigate(`/vault/document/${d.id}`)

  const toggleFav = async d => {
    docs.setData(x => ({ ...x, items: x.items.map(i => (i.id === d.id ? { ...i, favourite: !i.favourite } : i)) }))
    try { await vaultService.setFavourite(d.id, !d.favourite); stats.reload({ silent: true }) } catch (e) { toast(e.message, 'info'); docs.reload({ silent: true }) }
  }

  const remove = async d => {
    setMenu(null)
    docs.setData(x => ({ ...x, items: x.items.filter(i => i.id !== d.id), total: x.total - 1 }))
    try { await vaultService.deleteDocument(d.id); toast('Moved to Trash'); stats.reload({ silent: true }) } catch (e) { toast(e.message, 'info'); docs.reload({ silent: true }) }
  }

  const downloadDoc = async d => {
    setMenu(null)
    try { await vaultService.downloadDocument(d.id, d.name); toast(`Downloading ${d.name}`) } catch (e) { toast(e.message, 'info') }
  }

  const uploadFiles = async files => {
    const list = Array.from(files)
    if (!list.length) return
    setUploading(n => n + list.length)
    const results = await Promise.allSettled(list.map(f => vaultService.uploadDocument(f, { folderId: folder?.id })))
    setUploading(n => n - list.length)
    const ok = results.filter(r => r.status === 'fulfilled').length
    if (ok) toast(`${ok} file(s) uploaded to your vault`)
    if (ok < list.length) toast(`${list.length - ok} file(s) failed to upload`, 'info')
    docs.reload({ silent: true })
    stats.reload({ silent: true })
  }

  const createFolder = async e => {
    e.preventDefault()
    const name = newFolder.trim()
    if (!name) return
    setCreating(true)
    try {
      const f = await vaultService.createFolder({ name })
      folders.setData(x => ({ ...x, items: [...x.items, f] }))
      setNewFolder(null)
      toast(`Folder “${name}” created`)
    } catch (err) { toast(err.message, 'info') } finally { setCreating(false) }
  }

  const storage = stats.data?.storage
  const pct = storage ? Math.round((storage.usedBytes / storage.quotaBytes) * 100) : 0

  return (
    <div className="vault">
      <div className="vault-head">
        <div>
          <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Legal Vault' }]} />
          <h1 className="page-title">Legal Vault</h1>
          <p className="page-sub vault-sub">Securely store, organise and access all your legal documents.</p>
        </div>
        <div className="vault-tools">
          <label className="vault-search"><Search size={19} /><input value={q} onChange={e => setQ(e.target.value)} placeholder="Search files, folders or keywords..." /></label>
          <div className="view-toggle">
            <button className={view === 'grid' ? 'active' : ''} onClick={() => setView('grid')} aria-label="Grid view"><LayoutGrid size={20} /></button>
            <button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')} aria-label="List view"><List size={20} /></button>
          </div>
          <div className="top-pop" ref={filterRef}>
            <button className="btn btn-outline vault-filter" onClick={() => setFilterOpen(o => !o)}><Filter size={19} /> Filter{statusFilter[1] && <span className="pill pill-blue">{statusFilter[0]}</span>}</button>
            {filterOpen && (
              <div className="popover popover-sm">
                {STATUS_FILTERS.map(s => <button key={s[0]} className={`popover-item ${s[0] === statusFilter[0] ? 'active' : ''}`} onClick={() => { setStatusFilter(s); setFilterOpen(false) }}>{s[0]}</button>)}
              </div>
            )}
          </div>
          <input ref={fileRef} type="file" hidden multiple onChange={e => { uploadFiles(e.target.files); e.target.value = '' }} />
          <button className="btn btn-orange vault-upload" onClick={() => fileRef.current.click()} disabled={uploading > 0}>
            {uploading > 0 ? <Loader2 size={20} className="spin" /> : <Plus size={20} />} {uploading > 0 ? 'Uploading…' : 'Upload Document'}
          </button>
        </div>
      </div>

      <div className="vault-grid">
        <aside className="vault-side">
          <section className="card vault-files">
            <h2 className="card-title">My Files</h2>
            <ul>
              {CATEGORIES.map(c => (
                <li key={c.key}>
                  <button className={cat === c.key ? 'active' : ''} onClick={() => { setCat(c.key); setFolder(null) }}>
                    {c.key === 'favourites' ? <Star size={19} fill="#f59e0b" color="#f59e0b" /> : c.key === 'all' ? <Folder size={19} fill="#1d5fd6" color="#1d5fd6" /> : <c.icon size={19} />}
                    <span>{c.label}</span><em>{stats.data?.counts?.[c.key] ?? ''}</em>
                  </button>
                </li>
              ))}
            </ul>
          </section>
          <section className="card vault-storage">
            <h2 className="card-title">Storage Usage</h2>
            {storage ? (
              <>
                <div className="vs-row"><span><b>{formatBytes(storage.usedBytes)}</b> of {formatBytes(storage.quotaBytes).replace('.0 ', ' ')} used</span><span>{pct}%</span></div>
                <div className="progress"><span style={{ width: `${pct}%`, background: '#1d5fd6' }} /></div>
              </>
            ) : <Skeleton h={30} />}
            <button className="link vs-upgrade" onClick={() => toast('Upgrade plans coming soon', 'info')}>Upgrade Storage <ArrowRight size={17} /></button>
            <div className="vs-more">
              <div className="vs-more-head"><Crown size={24} /><div><b>Need more space?</b><span>Upgrade to store more documents and keep your legal records safe.</span></div></div>
              <button className="btn btn-outline btn-block" onClick={() => toast('Plans: Basic 5 GB (Free) · Plus 50 GB · Pro 200 GB', 'info')}>View Plans</button>
            </div>
          </section>
        </aside>

        <div className="vault-main">
          <section className="card vault-folders">
            <div className="card-head">
              <h2 className="vault-h2">Folders <span>({folders.data?.items.length ?? 0})</span></h2>
              <button className="link" onClick={() => setNewFolder('')}><Plus size={19} /> New Folder</button>
            </div>
            <div className="folder-grid">
              {!folders.data && folders.loading && Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} h={122} r={10} />)}
              {folders.data?.items.map(f => (
                <div key={f.id} className={`folder ${folder?.id === f.id ? 'active' : ''}`} onClick={() => setFolder(folder?.id === f.id ? null : f)}>
                  <FolderIcon color={f.color} size={54} />
                  <b>{f.name}</b>
                  <span>{f.fileCount} files</span>
                  <button className="icon-btn-plain folder-kebab" aria-label="Folder options" onClick={e => { e.stopPropagation(); toast(`Options for ${f.name}`, 'info') }}><MoreVertical size={18} /></button>
                </div>
              ))}
            </div>
            {folders.error && <ErrorState compact error={folders.error} onRetry={folders.reload} />}
          </section>

          <section className="card vault-docs">
            <div className="card-head">
              <h2 className="vault-h2">Documents <span>({docs.data?.total ?? 0})</span>{folder && <button className="pill pill-blue vault-chip" onClick={() => setFolder(null)}>{folder.name} <X size={13} /></button>}</h2>
              <div className="vault-sort" ref={sortRef}>
                <span>Sort by:</span>
                <button onClick={() => setSortOpen(o => !o)}>{sort[0]} <ChevronDown size={18} /></button>
                {sortOpen && (
                  <div className="popover popover-user">
                    {SORTS.map(s => <button key={s[1]} className={`popover-item ${s[1] === sort[1] ? 'active' : ''}`} onClick={() => { setSort(s); setSortOpen(false) }}>{s[0]}</button>)}
                  </div>
                )}
              </div>
            </div>

            {docs.error && !docs.data && <ErrorState compact error={docs.error} onRetry={docs.reload} />}
            {!docs.data && docs.loading && <div className="doc-grid">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} h={144} r={10} />)}</div>}
            {docs.data && items.length === 0 && <div className="vault-empty"><Folder size={40} /><p>No documents here yet.</p></div>}

            {items.length > 0 && (view === 'grid' ? (
              <div className={`doc-grid ${docs.loading ? 'is-refreshing' : ''}`}>
                {items.map(d => (
                  <div key={d.id} className="doc-card" onClick={() => open(d)}>
                    <div className="doc-card-top">
                      <FileIcon type={d.fileType} size={52} />
                      <div className="doc-card-info"><b>{d.name}</b><span>{d.category}</span><small>Updated {formatDate(d.updatedAt)} • {formatBytes(d.sizeBytes)}</small></div>
                      <div className="top-pop">
                        <button className="icon-btn-plain doc-kebab" aria-label="Document options" onClick={e => { e.stopPropagation(); setMenu(menu === d.id ? null : d.id) }}><MoreVertical size={19} /></button>
                        {menu === d.id && (
                          <div className="popover popover-sm doc-menu" onClick={e => e.stopPropagation()}>
                            <button className="popover-item" onClick={() => open(d)}>Open</button>
                            <button className="popover-item" onClick={() => downloadDoc(d)}>Download</button>
                            <button className="popover-item danger" onClick={() => remove(d)}>Delete</button>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="doc-card-foot">
                      {d.status === 'analysed'
                        ? <span className="pill pill-green doc-status"><CheckCircle2 size={16} fill="#22a45a" color="#fff" /> Analysed</span>
                        : <span className="pill pill-blue doc-status doc-secure"><ShieldCheck size={16} /> Secure</span>}
                      <button className={`icon-btn-plain doc-star ${d.favourite ? 'on' : ''}`} onClick={e => { e.stopPropagation(); toggleFav(d) }} aria-label="Favourite"><Star size={21} /></button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className={`doc-table ${docs.loading ? 'is-refreshing' : ''}`}>
                <div className="doc-tr doc-th"><span>Name</span><span>Category</span><span>Updated</span><span>Size</span><span>Status</span><span /></div>
                {items.map(d => (
                  <div key={d.id} className="doc-tr" onClick={() => open(d)}>
                    <span className="doc-td-name"><FileIcon type={d.fileType} size={30} /><b>{d.name}</b></span>
                    <span>{d.category}</span><span>{formatDate(d.updatedAt)}</span><span>{formatBytes(d.sizeBytes)}</span>
                    <span>{d.status === 'analysed' ? <span className="pill pill-green">Analysed</span> : <span className="pill pill-blue">Secure</span>}</span>
                    <button className={`icon-btn-plain doc-star ${d.favourite ? 'on' : ''}`} onClick={e => { e.stopPropagation(); toggleFav(d) }} aria-label="Favourite"><Star size={19} /></button>
                  </div>
                ))}
              </div>
            ))}
          </section>
        </div>
      </div>

      <Modal open={newFolder !== null} onClose={() => setNewFolder(null)} className="modal-sm">
        <form className="confirm" onSubmit={createFolder}>
          <span className="icon-tile tile-blue tile-lg"><FolderPlus /></span>
          <h3>New Folder</h3>
          <input autoFocus className="input" value={newFolder || ''} onChange={e => setNewFolder(e.target.value)} placeholder="Folder name" />
          <div className="confirm-actions">
            <button type="button" className="btn btn-outline" onClick={() => setNewFolder(null)}>Cancel</button>
            <button className="btn btn-orange" disabled={creating}>{creating && <Loader2 size={16} className="spin" />} Create Folder</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
