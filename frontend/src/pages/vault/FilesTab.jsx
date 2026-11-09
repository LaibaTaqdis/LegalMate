import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle, ChevronDown, ChevronLeft, ChevronRight, FileText, Folder, FolderInput, FolderOpen, FolderPlus, Gavel, Home, LayoutGrid, List, Loader2, MoreVertical,
  Pencil, Plus, RotateCcw, Search, ShieldAlert, Star, Trash2, UserRound, Users, X
} from 'lucide-react'
import { Modal, useClickOutside } from '../../components/common'
import { FileIcon, FolderIcon } from '../../components/Icons'
import { useUI } from '../../components/UIContext'
import { ErrorState, Skeleton } from '../../components/States'
import { useQuery } from '../../hooks/useApi'
import { useDebounced } from '../../hooks/useDebounced'
import { vaultService } from '../../api/services/vaultService'
import { ACCEPTED_TYPES, MAX_UPLOAD_BYTES, MAX_UPLOAD_MB } from '../../api/services/documentService'
import { formatBytes, formatDate } from '../../utils/format'

const CATEGORIES = [
  { key: 'all', label: 'All Files', icon: Folder },
  { key: 'Contracts', label: 'Contracts', icon: FileText },
  { key: 'Notices', label: 'Notices', icon: ShieldAlert },
  { key: 'Court Documents', label: 'Court Documents', icon: Gavel },
  { key: 'Property', label: 'Property', icon: Home },
  { key: 'Personal', label: 'Personal', icon: UserRound },
  { key: 'Family', label: 'Family', icon: Users },
  { key: 'Other', label: 'Other', icon: FileText },
  { key: 'favourites', label: 'Favourites', icon: Star },
  { key: 'trash', label: 'Trash', icon: Trash2 },
]
const SORTS = [['Updated (Newest)', 'updated_desc'], ['Updated (Oldest)', 'updated_asc'], ['Name (A–Z)', 'name_asc'], ['Name (Z–A)', 'name_desc'], ['Size (Largest)', 'size_desc']]
const FOLDER_COLORS = ['#0ea5e9', '#fbbf24', '#34d399', '#f472b6', '#a78bfa', '#fb923c']
const ACCEPT = '.pdf,.docx,.jpg,.jpeg,.png'
const EMPTY = {
  all: ['No files yet', 'Add a contract, notice or photo with “Upload Files”, or drop files here.'],
  favourites: ['No favourites yet', 'Tap the star on a file to keep it handy.'],
  trash: ['The Trash is empty', 'Files you delete wait here for 30 days before they are removed for good.'],
}

export default function FilesTab() {
  const navigate = useNavigate()
  const { toast } = useUI()
  const fileRef = useRef(null)
  const [view, setView] = useState('grid')
  const [cat, setCat] = useState('all')
  const [folder, setFolder] = useState(null)
  const [q, setQ] = useState('')
  const [sort, setSort] = useState(SORTS[0])
  const [sortOpen, setSortOpen] = useState(false)
  const [page, setPage] = useState(1)
  const [menu, setMenu] = useState(null)               // file id or 'folder:<id>'
  const [renaming, setRenaming] = useState(null)       // { id, name }
  const [moving, setMoving] = useState(null)           // { id, folderId }
  const [folderForm, setFolderForm] = useState(null)   // { id?, name, color }
  const [deleteFolder, setDeleteFolder] = useState(null)
  const [confirmEmpty, setConfirmEmpty] = useState(false)
  const [uploads, setUploads] = useState([])           // [{ key, name, progress }]
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const sortRef = useClickOutside(() => setSortOpen(false))
  const menuRef = useClickOutside(() => setMenu(null))
  const search = useDebounced(q, 300)

  const stats = useQuery(signal => vaultService.getStats(signal), [])
  const folders = useQuery(signal => vaultService.listFolders(signal), [])
  const list = useQuery(signal => vaultService.listFiles({ category: cat, folderId: folder?.id, q: search || undefined, sort: sort[1], page }, signal),
    [cat, folder?.id, search, sort[1], page], { pollInterval: 4000, shouldPoll: d => d?.items?.some(i => i.textStatus === 'pending') })
  useEffect(() => { setPage(1) }, [cat, folder?.id, search, sort[1]])
  const items = list.data?.items || []
  const counts = list.data?.counts
  const storage = list.data?.storage
  const pct = storage ? Math.min(100, Math.round((storage.usedBytes / storage.quotaBytes) * 100)) : 0
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.pageSize)) : 1
  const inTrash = cat === 'trash'
  const disabled = stats.data && stats.data.filesEnabled === false

  const refresh = () => { list.reload({ silent: true }); folders.reload({ silent: true }) }
  const run = async (fn, msg) => {
    setMenu(null)
    try { await fn(); if (msg) toast(msg) } catch (e) { toast(e.message, 'info') }
    refresh()
  }

  // ---- upload
  const uploadFiles = async picked => {
    const queue = Array.from(picked)
    if (!queue.length) return
    let ok = 0
    for (const file of queue) {
      const ext = file.name.split('.').pop().toLowerCase().replace('jpeg', 'jpg')
      if (!ACCEPTED_TYPES.includes(ext)) { toast(`${file.name}: please add a PDF, Word (.docx), JPG or PNG file`, 'info'); continue }
      if (file.size > MAX_UPLOAD_BYTES) { toast(`${file.name} is larger than ${MAX_UPLOAD_MB} MB`, 'info'); continue }
      const key = `${file.name}_${Date.now()}_${Math.random()}`
      setUploads(u => [...u, { key, name: file.name, progress: 0 }])
      try {
        await vaultService.uploadFile(file, { folderId: folder?.id, category: CATEGORIES.slice(1, 8).some(c => c.key === cat) ? cat : undefined, onProgress: p => setUploads(u => u.map(x => (x.key === key ? { ...x, progress: p } : x))) })
        ok++
      } catch (e) {
        toast(`${file.name}: ${e.message}`, 'info')
      } finally {
        setUploads(u => u.filter(x => x.key !== key))
      }
      refresh()
    }
    if (ok) toast(ok === 1 ? 'File added to your Vault' : `${ok} files added to your Vault`)
  }
  const onDrop = e => { e.preventDefault(); setDragging(false); if (!disabled && !inTrash) uploadFiles(e.dataTransfer.files) }

  // ---- actions
  const open = f => navigate(`/vault/file/${f.id}`)
  const download = async f => {
    setMenu(null)
    try {
      const { url } = await vaultService.getFileLink(f.id, true)
      if (url) Object.assign(document.createElement('a'), { href: url }).click()
      else toast('Download is not available in demo mode', 'info')
    } catch (e) { toast(e.message, 'info') }
  }
  const toggleFav = f => {
    list.setData(x => ({ ...x, items: x.items.map(y => (y.id === f.id ? { ...y, favourite: !y.favourite } : y)) }))
    run(() => vaultService.setFileFavourite(f.id, !f.favourite))
  }
  const submitRename = async e => {
    e.preventDefault()
    const name = renaming.name.trim()
    if (!name) return
    setBusy(true)
    try { await vaultService.updateFile(renaming.id, { name }); toast('Renamed'); setRenaming(null); refresh() } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }
  const submitMove = async e => {
    e.preventDefault()
    setBusy(true)
    try { await vaultService.updateFile(moving.id, { folderId: moving.folderId || null }); toast('Moved'); setMoving(null); refresh() } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }
  const submitFolder = async e => {
    e.preventDefault()
    const name = folderForm.name.trim()
    if (!name) return
    setBusy(true)
    try {
      if (folderForm.id) {
        const fo = await vaultService.updateFolder(folderForm.id, { name, color: folderForm.color })
        if (folder?.id === fo.id) setFolder(fo)
        toast('Folder updated')
      } else { await vaultService.createFolder({ name, color: folderForm.color }); toast(`Folder “${name}” created`) }
      setFolderForm(null); refresh()
    } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }
  const confirmDeleteFolder = async () => {
    setBusy(true)
    try { await vaultService.deleteFolder(deleteFolder.id); if (folder?.id === deleteFolder.id) setFolder(null); toast('Folder deleted. Its files were kept.'); setDeleteFolder(null); refresh() } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }
  const emptyTrash = async () => {
    setBusy(true)
    try { const r = await vaultService.emptyFilesTrash(); toast(`Trash emptied (${r?.deleted ?? 0} deleted)`); setConfirmEmpty(false); refresh() } catch (err) { toast(err.message, 'info'); setConfirmEmpty(false) } finally { setBusy(false) }
  }

  const Menu = ({ f }) => (
    <div className="top-pop" ref={menu === f.id ? menuRef : null}>
      <button className="icon-btn-plain doc-kebab" aria-label="File options" onClick={e => { e.stopPropagation(); setMenu(menu === f.id ? null : f.id) }}><MoreVertical size={19} /></button>
      {menu === f.id && (
        <div className="popover popover-sm doc-menu" onClick={e => e.stopPropagation()}>
          <button className="popover-item" onClick={() => open(f)}>Open</button>
          <button className="popover-item" onClick={() => download(f)}>Download</button>
          {inTrash ? (
            <>
              <button className="popover-item" onClick={() => run(() => vaultService.restoreFile(f.id), 'Restored')}><RotateCcw size={15} /> Restore</button>
              <button className="popover-item danger" onClick={() => run(() => vaultService.deleteFileForever(f.id), 'Deleted for good')}>Delete forever</button>
            </>
          ) : (
            <>
              <button className="popover-item" onClick={() => { setMenu(null); setRenaming({ id: f.id, name: f.name }) }}><Pencil size={15} /> Rename</button>
              <button className="popover-item" onClick={() => { setMenu(null); setMoving({ id: f.id, folderId: f.folderId || '' }) }}><FolderInput size={15} /> Move to folder</button>
              <button className="popover-item danger" onClick={() => run(() => vaultService.trashFile(f.id), 'Moved to Trash')}>Move to Trash</button>
            </>
          )}
        </div>
      )}
    </div>
  )
  const Reading = ({ f }) => (f.textStatus === 'pending' ? <span className="pill pill-gray fv-reading"><Loader2 size={12} className="spin" /> Reading text…</span> : null)

  if (disabled) {
    return (
      <div className="card vault-soon vault-off">
        <span className="icon-tile tile-orange"><AlertTriangle /></span>
        <b>File storage is not set up on this server</b>
        <p>Your saved answers and analyses still work. To keep your own files here, an administrator needs to set SUPABASE_URL and SUPABASE_SERVICE_KEY for the server.</p>
      </div>
    )
  }

  return (
    <div className="vault-tab" onDragOver={e => { e.preventDefault(); if (!inTrash) setDragging(true) }} onDragLeave={e => { if (e.currentTarget === e.target) setDragging(false) }} onDrop={onDrop}>
      <div className="vault-bar">
        <label className="vault-search"><Search size={19} /><input value={q} onChange={e => setQ(e.target.value)} placeholder="Search file names and contents..." /></label>
        <div className="view-toggle">
          <button className={view === 'grid' ? 'active' : ''} onClick={() => setView('grid')} aria-label="Grid view"><LayoutGrid size={20} /></button>
          <button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')} aria-label="List view"><List size={20} /></button>
        </div>
        <input ref={fileRef} type="file" hidden multiple accept={ACCEPT} onChange={e => { uploadFiles(e.target.files); e.target.value = '' }} />
        <button className="btn btn-orange vault-upload" onClick={() => fileRef.current.click()} disabled={inTrash}><Plus size={20} /> Upload Files</button>
      </div>

      {uploads.length > 0 && (
        <div className="card fv-uploads" aria-live="polite">
          {uploads.map(u => (
            <div key={u.key}><Loader2 size={16} className="spin" /> <span>{u.name}</span><div className="progress"><span style={{ width: `${u.progress}%`, background: '#1d5fd6' }} /></div><em>{u.progress}%</em></div>
          ))}
        </div>
      )}

      <div className="vault-grid">
        <aside className="vault-side">
          <section className="card vault-files">
            <h2 className="card-title">My Files</h2>
            <ul>
              {CATEGORIES.map(c => (
                <li key={c.key}>
                  <button className={cat === c.key ? 'active' : ''} onClick={() => { setCat(c.key); if (c.key === 'trash') setFolder(null) }}>
                    {c.key === 'favourites' ? <Star size={19} fill="#f59e0b" color="#f59e0b" /> : c.key === 'all' ? <Folder size={19} fill="#1d5fd6" color="#1d5fd6" /> : <c.icon size={19} />}
                    <span>{c.label}</span><em>{counts?.[c.key] ?? ''}</em>
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
                <div className="progress"><span style={{ width: `${pct}%`, background: pct >= 90 ? '#e5322d' : '#1d5fd6' }} /></div>
                {pct >= 90 && <p className="vs-warn">Your Vault is almost full. Delete files you no longer need and empty the Trash.</p>}
                {counts?.trash > 0 && !inTrash && <button className="link small" onClick={() => setCat('trash')}>{counts.trash} file{counts.trash > 1 ? 's' : ''} in the Trash still use space</button>}
              </>
            ) : <Skeleton h={30} />}
          </section>
        </aside>

        <div className="vault-main">
          {!inTrash && (
            <section className="card vault-folders">
              <div className="card-head">
                <h2 className="vault-h2">Folders <span>({folders.data?.items.length ?? 0})</span></h2>
                <button className="link" onClick={() => setFolderForm({ name: '', color: FOLDER_COLORS[0] })}><Plus size={19} /> New Folder</button>
              </div>
              {folders.data?.items.length === 0 && <p className="vi-empty">No folders yet. Folders help you keep related files together.</p>}
              <div className="folder-grid">
                {!folders.data && folders.loading && Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} h={110} r={10} />)}
                {folders.data?.items.map(f => (
                  <div key={f.id} className={`folder ${folder?.id === f.id ? 'active' : ''}`} onClick={() => setFolder(folder?.id === f.id ? null : f)}>
                    <FolderIcon color={f.color} size={46} />
                    <b title={f.name}>{f.name}</b>
                    <span>{f.fileCount} file{f.fileCount === 1 ? '' : 's'}</span>
                    <div className="top-pop folder-kebab" ref={menu === `folder:${f.id}` ? menuRef : null}>
                      <button className="icon-btn-plain" aria-label="Folder options" onClick={e => { e.stopPropagation(); setMenu(menu === `folder:${f.id}` ? null : `folder:${f.id}`) }}><MoreVertical size={18} /></button>
                      {menu === `folder:${f.id}` && (
                        <div className="popover popover-sm doc-menu" onClick={e => e.stopPropagation()}>
                          <button className="popover-item" onClick={() => { setMenu(null); setFolderForm({ id: f.id, name: f.name, color: f.color }) }}><Pencil size={15} /> Rename</button>
                          <button className="popover-item danger" onClick={() => { setMenu(null); setDeleteFolder(f) }}>Delete folder</button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {folders.error && <ErrorState compact error={folders.error} onRetry={folders.reload} />}
            </section>
          )}

          <section className={`card vault-docs ${dragging ? 'fv-drop' : ''}`}>
            <div className="card-head">
              <h2 className="vault-h2">{CATEGORIES.find(c => c.key === cat).label} <span>({list.data?.total ?? 0})</span>
                {folder && <button className="pill pill-blue vault-chip" onClick={() => setFolder(null)}>{folder.name} <X size={13} /></button>}</h2>
              <div className="vault-head-right">
                {inTrash && items.length > 0 && <button className="btn btn-outline btn-sm" onClick={() => setConfirmEmpty(true)}><Trash2 size={16} /> Empty Trash</button>}
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
            </div>
            {inTrash && <p className="vault-note">Files stay in the Trash for 30 days and are then deleted for good. They still count towards your storage until then.</p>}
            {dragging && <div className="fv-drop-hint">Drop files to add them to your Vault</div>}

            {list.error && !list.data && <ErrorState compact error={list.error} onRetry={list.reload} />}
            {!list.data && list.loading && <div className="doc-grid">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} h={150} r={10} />)}</div>}
            {list.data && items.length === 0 && (
              <div className="vault-empty"><FolderOpen size={40} />
                <b>{search ? 'Nothing matches your search' : (EMPTY[cat] || ['No files in this category', 'Choose “Upload Files” to add one here.'])[0]}</b>
                <p>{search ? 'Try a different word. Search looks at file names and at the text inside files.' : (EMPTY[cat] || ['', 'Choose “Upload Files” while this category is open, and the file is filed here.'])[1]}</p></div>
            )}

            {items.length > 0 && (view === 'grid' ? (
              <div className={`doc-grid ${list.loading ? 'is-refreshing' : ''}`}>
                {items.map(f => (
                  <div key={f.id} className="doc-card" onClick={() => open(f)}>
                    <div className="doc-card-top">
                      <FileIcon type={f.fileType} size={52} />
                      <div className="doc-card-info"><b dir="auto" title={f.name}>{f.name}</b><span>{f.category}{f.folderName ? ` • ${f.folderName}` : ''}</span>
                        <small>{inTrash ? `Deleted ${formatDate(f.trashedAt)}` : `Updated ${formatDate(f.updatedAt)}`} • {formatBytes(f.sizeBytes)}</small></div>
                      <Menu f={f} />
                    </div>
                    <div className="doc-card-foot">
                      <span className="fv-badges"><Reading f={f} />{f.noteCount > 0 && <span className="pill pill-gray">{f.noteCount} note{f.noteCount > 1 ? 's' : ''}</span>}</span>
                      {!inTrash && <button className={`icon-btn-plain doc-star ${f.favourite ? 'on' : ''}`} onClick={e => { e.stopPropagation(); toggleFav(f) }} aria-label="Favourite"><Star size={21} /></button>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className={`doc-table fv-table ${list.loading ? 'is-refreshing' : ''}`}>
                <div className="doc-tr doc-th"><span>Name</span><span>Category</span><span>Updated</span><span>Size</span><span /><span /></div>
                {items.map(f => (
                  <div key={f.id} className="doc-tr" onClick={() => open(f)}>
                    <span className="doc-td-name"><FileIcon type={f.fileType} size={30} /><b dir="auto">{f.name}</b><Reading f={f} /></span>
                    <span>{f.category}{f.folderName ? ` • ${f.folderName}` : ''}</span><span>{formatDate(inTrash ? f.trashedAt : f.updatedAt)}</span><span>{formatBytes(f.sizeBytes)}</span>
                    {!inTrash ? <button className={`icon-btn-plain doc-star ${f.favourite ? 'on' : ''}`} onClick={e => { e.stopPropagation(); toggleFav(f) }} aria-label="Favourite"><Star size={19} /></button> : <span />}
                    <Menu f={f} />
                  </div>
                ))}
              </div>
            ))}

            {pages > 1 && (
              <div className="vault-pager">
                <button className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}><ChevronLeft size={16} /> Previous</button>
                <span>Page {page} of {pages}</span>
                <button className="btn btn-outline btn-sm" disabled={page >= pages} onClick={() => setPage(p => p + 1)}>Next <ChevronRight size={16} /></button>
              </div>
            )}
          </section>
        </div>
      </div>

      <Modal open={renaming !== null} onClose={() => setRenaming(null)} className="modal-sm">
        <form className="confirm" onSubmit={submitRename}>
          <span className="icon-tile tile-blue tile-lg"><Pencil /></span>
          <h3>Rename file</h3>
          <input autoFocus className="input" maxLength={160} value={renaming?.name || ''} onChange={e => setRenaming(r => ({ ...r, name: e.target.value }))} placeholder="File name" />
          <div className="confirm-actions">
            <button type="button" className="btn btn-outline" onClick={() => setRenaming(null)}>Cancel</button>
            <button className="btn btn-orange" disabled={busy || !renaming?.name.trim()}>{busy && <Loader2 size={16} className="spin" />} Save</button>
          </div>
        </form>
      </Modal>

      <Modal open={moving !== null} onClose={() => setMoving(null)} className="modal-sm">
        <form className="confirm" onSubmit={submitMove}>
          <span className="icon-tile tile-blue tile-lg"><FolderInput /></span>
          <h3>Move to folder</h3>
          <select className="input" value={moving?.folderId || ''} onChange={e => setMoving(m => ({ ...m, folderId: e.target.value }))}>
            <option value="">No folder</option>
            {folders.data?.items.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
          </select>
          <div className="confirm-actions">
            <button type="button" className="btn btn-outline" onClick={() => setMoving(null)}>Cancel</button>
            <button className="btn btn-orange" disabled={busy}>{busy && <Loader2 size={16} className="spin" />} Move</button>
          </div>
        </form>
      </Modal>

      <Modal open={folderForm !== null} onClose={() => setFolderForm(null)} className="modal-sm">
        <form className="confirm" onSubmit={submitFolder}>
          <span className="icon-tile tile-blue tile-lg"><FolderPlus /></span>
          <h3>{folderForm?.id ? 'Rename folder' : 'New folder'}</h3>
          <input autoFocus className="input" maxLength={60} value={folderForm?.name || ''} onChange={e => setFolderForm(f => ({ ...f, name: e.target.value }))} placeholder="Folder name" />
          <div className="fv-colors" role="radiogroup" aria-label="Folder colour">
            {FOLDER_COLORS.map(c => <button type="button" key={c} role="radio" aria-checked={folderForm?.color === c} className={folderForm?.color === c ? 'on' : ''} style={{ background: c }} onClick={() => setFolderForm(f => ({ ...f, color: c }))} aria-label={c} />)}
          </div>
          <div className="confirm-actions">
            <button type="button" className="btn btn-outline" onClick={() => setFolderForm(null)}>Cancel</button>
            <button className="btn btn-orange" disabled={busy || !folderForm?.name.trim()}>{busy && <Loader2 size={16} className="spin" />} {folderForm?.id ? 'Save' : 'Create Folder'}</button>
          </div>
        </form>
      </Modal>

      <Modal open={deleteFolder !== null} onClose={() => setDeleteFolder(null)} className="modal-sm">
        <div className="confirm">
          <span className="icon-tile tile-red tile-lg"><Trash2 /></span>
          <h3>Delete the folder “{deleteFolder?.name}”?</h3>
          <p>The files inside are not deleted. They stay in your Vault without a folder.</p>
          <div className="confirm-actions">
            <button className="btn btn-outline" onClick={() => setDeleteFolder(null)}>Cancel</button>
            <button className="btn btn-orange" onClick={confirmDeleteFolder} disabled={busy}>{busy && <Loader2 size={16} className="spin" />} Delete folder</button>
          </div>
        </div>
      </Modal>

      <Modal open={confirmEmpty} onClose={() => setConfirmEmpty(false)} className="modal-sm">
        <div className="confirm">
          <span className="icon-tile tile-red tile-lg"><Trash2 /></span>
          <h3>Empty the Trash?</h3>
          <p>Every file in the Trash will be deleted for good, original included. This cannot be undone.</p>
          <div className="confirm-actions">
            <button className="btn btn-outline" onClick={() => setConfirmEmpty(false)}>Cancel</button>
            <button className="btn btn-orange" onClick={emptyTrash} disabled={busy}>{busy && <Loader2 size={16} className="spin" />} Delete everything</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
