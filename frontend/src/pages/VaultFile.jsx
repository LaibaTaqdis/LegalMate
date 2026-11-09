import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Download, ExternalLink, FolderInput, Loader2, Pencil, RotateCcw, Star, Trash2 } from 'lucide-react'
import { Breadcrumb, Modal } from '../components/common'
import { FileIcon } from '../components/Icons'
import { useUI } from '../components/UIContext'
import { ErrorState, PageSkeleton, Skeleton } from '../components/States'
import { VaultActivity, VaultNotes } from '../components/VaultParts'
import { useQuery } from '../hooks/useApi'
import { vaultService } from '../api/services/vaultService'
import { formatBytes, formatDateTime } from '../utils/format'

const CATEGORIES = ['Contracts', 'Notices', 'Court Documents', 'Property', 'Personal', 'Family', 'Other']
const TYPE_LABEL = { pdf: 'PDF document', docx: 'Word document', jpg: 'JPG image', png: 'PNG image' }

/** The file itself: a PDF or picture from a short-lived link, a Word file as the text read from it. */
function Preview({ file }) {
  const isImage = file.fileType === 'jpg' || file.fileType === 'png'
  const isPdf = file.fileType === 'pdf'
  const link = useQuery(signal => vaultService.getFileLink(file.id, false), [file.id], { enabled: isImage || isPdf })
  const text = useQuery(signal => vaultService.getFileText(file.id, signal), [file.id, file.textStatus], { enabled: file.fileType === 'docx' })
  const url = link.data?.url

  if (isImage || isPdf) {
    if (link.error) return <ErrorState compact error={link.error} onRetry={link.reload} />
    if (!link.data) return <Skeleton h={520} r={10} />
    if (!url) return <div className="fv-nopreview"><FileIcon type={file.fileType} size={64} /><p>The preview is not available in demo mode.</p></div>
    return isImage
      ? <div className="fv-image"><img src={url} alt={file.name} /></div>
      : <>
        <iframe className="fv-pdf" src={url} title={file.name} />
        <p className="fv-fallback">The preview does not show in some browsers. Use “Open in new tab” or “Download” to read the file.</p>
      </>
  }
  if (text.error) return <ErrorState compact error={text.error} onRetry={text.reload} />
  if (!text.data) return <Skeleton h={320} r={10} />
  return (
    <div className="fv-text">
      <p className="fv-text-note">Word files are shown as the text read from them. Download the file to see it exactly as it was.</p>
      {text.data.text ? <div dir="auto">{text.data.text.split(/\n{2,}/).map((para, i) => <p key={i}>{para}</p>)}</div> : <p className="vi-empty">No text could be read from this file.</p>}
      {text.data.truncated && <p className="vi-empty">Only the first part of the text is shown.</p>}
    </div>
  )
}

export default function VaultFile() {
  const { id } = useParams()
  const query = useQuery(signal => vaultService.getFile(id, signal), [id], { pollInterval: 4000, shouldPoll: f => f?.textStatus === 'pending' })
  if (query.error && !query.data) return <ErrorState error={query.error} onRetry={query.reload} />
  if (!query.data) return <PageSkeleton cards={2} rows={2} />
  return <File file={query.data} setFile={query.setData} reload={() => query.reload({ silent: true })} />
}

function File({ file, setFile, reload }) {
  const navigate = useNavigate()
  const { toast } = useUI()
  const folders = useQuery(signal => vaultService.listFolders(signal), [])
  const [renaming, setRenaming] = useState(null)
  const [moving, setMoving] = useState(null)
  const [busy, setBusy] = useState(null)
  const [version, setVersion] = useState(0)
  const trashed = !!file.trashedAt
  useEffect(() => { setVersion(v => v + 1) }, [file.textStatus])

  const run = async (key, fn, msg, after) => {
    setBusy(key)
    try { await fn(); if (msg) toast(msg); setVersion(v => v + 1); after ? after() : reload() } catch (e) { toast(e.message, 'info') } finally { setBusy(null) }
  }
  const download = () => run('download', async () => {
    const { url } = await vaultService.getFileLink(file.id, true)
    if (!url) throw new Error('Download is not available in demo mode')
    Object.assign(document.createElement('a'), { href: url }).click()
  })
  const openTab = () => run('open', async () => {
    const { url } = await vaultService.getFileLink(file.id, false)
    if (!url) throw new Error('Opening is not available in demo mode')
    window.open(url, '_blank', 'noopener')
  })
  const fav = () => { setFile(f => ({ ...f, favourite: !f.favourite })); run('fav', () => vaultService.setFileFavourite(file.id, !file.favourite)) }
  const submitRename = async e => {
    e.preventDefault()
    const name = renaming.trim()
    if (!name) return
    await run('rename', () => vaultService.updateFile(file.id, { name }), 'Renamed')
    setRenaming(null)
  }
  const submitMove = async e => {
    e.preventDefault()
    await run('move', () => vaultService.updateFile(file.id, { folderId: moving || null }), 'Moved')
    setMoving(null)
  }

  return (
    <div className="vi-page">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Legal Vault', to: '/vault?tab=files' }, { label: file.name.length > 50 ? file.name.slice(0, 50) + '…' : file.name }]} />
      <div className="vi-top">
        <div className="fv-title">
          <FileIcon type={file.fileType} size={44} />
          <div>
            <h1 dir="auto">{file.name}</h1>
            <p>{TYPE_LABEL[file.fileType]} • {formatBytes(file.sizeBytes)}{file.pages > 1 ? ` • ${file.pages} pages` : ''} • Added {formatDateTime(file.uploadedAt)}</p>
          </div>
        </div>
        <div className="vi-actions">
          <button className="btn btn-outline" onClick={download} disabled={busy === 'download'}>{busy === 'download' ? <Loader2 size={17} className="spin" /> : <Download size={17} />} Download</button>
          {file.fileType !== 'docx' && <button className="btn btn-outline" onClick={openTab} disabled={busy === 'open'}><ExternalLink size={17} /> Open in new tab</button>}
          {!trashed && (
            <>
              <button className="btn btn-outline" onClick={fav} disabled={busy === 'fav'}><Star size={17} fill={file.favourite ? '#f59e0b' : 'none'} color={file.favourite ? '#f59e0b' : 'currentColor'} /> {file.favourite ? 'Favourite' : 'Add to favourites'}</button>
              <button className="btn btn-outline" onClick={() => setRenaming(file.name)}><Pencil size={17} /> Rename</button>
              <button className="btn btn-outline" onClick={() => run('trash', () => vaultService.trashFile(file.id), 'Moved to Trash', () => navigate('/vault?tab=files'))} disabled={busy === 'trash'}><Trash2 size={17} /> Move to Trash</button>
            </>
          )}
        </div>
      </div>

      {trashed && (
        <div className="vi-banner" role="status">
          <Trash2 size={18} /> This file is in the Trash. It is deleted for good 30 days after it was moved here.
          <button className="btn btn-orange btn-sm" onClick={() => run('restore', () => vaultService.restoreFile(file.id), 'Restored')} disabled={busy === 'restore'}><RotateCcw size={16} /> Restore</button>
          <button className="btn btn-outline btn-sm" onClick={() => run('forever', () => vaultService.deleteFileForever(file.id), 'Deleted for good', () => navigate('/vault?tab=files'))} disabled={busy === 'forever'}>Delete forever</button>
        </div>
      )}

      <div className="fv-layout">
        <section className="card fv-preview"><Preview file={file} /></section>
        <aside className="card fv-details">
          <h3>Details</h3>
          <dl>
            <dt>Category</dt>
            <dd>
              {trashed ? file.category : (
                <select className="ps-select" value={file.category} onChange={e => { const category = e.target.value; setFile(f => ({ ...f, category })); run('cat', () => vaultService.updateFile(file.id, { category }), 'Category changed') }}>
                  {CATEGORIES.map(c => <option key={c}>{c}</option>)}
                </select>
              )}
            </dd>
            <dt>Folder</dt>
            <dd>{file.folderName || 'None'} {!trashed && <button className="link small" onClick={() => setMoving(file.folderId || '')}><FolderInput size={14} /> Move</button>}</dd>
            <dt>Size</dt><dd>{formatBytes(file.sizeBytes)}</dd>
            <dt>Pages</dt><dd>{file.pages}</dd>
            <dt>Added</dt><dd>{formatDateTime(file.uploadedAt)}</dd>
            <dt>Searchable text</dt>
            <dd>{file.textStatus === 'pending' ? <span className="pill pill-gray"><Loader2 size={12} className="spin" /> Reading…</span> : file.hasText ? 'Yes: you can find it by what is inside' : 'No text could be read'}</dd>
          </dl>
        </aside>
      </div>

      <div className="vi-two">
        <VaultNotes id={file.id} locked={trashed} onChanged={() => setVersion(v => v + 1)}
          api={{ list: vaultService.listFileNotes, add: vaultService.addFileNote, remove: vaultService.deleteFileNote }} />
        <VaultActivity id={file.id} version={version} load={vaultService.listFileActivity} />
      </div>

      <Modal open={renaming !== null} onClose={() => setRenaming(null)} className="modal-sm">
        <form className="confirm" onSubmit={submitRename}>
          <span className="icon-tile tile-blue tile-lg"><Pencil /></span>
          <h3>Rename file</h3>
          <input autoFocus className="input" maxLength={160} value={renaming || ''} onChange={e => setRenaming(e.target.value)} placeholder="File name" />
          <div className="confirm-actions">
            <button type="button" className="btn btn-outline" onClick={() => setRenaming(null)}>Cancel</button>
            <button className="btn btn-orange" disabled={busy === 'rename' || !(renaming || '').trim()}>{busy === 'rename' && <Loader2 size={16} className="spin" />} Save</button>
          </div>
        </form>
      </Modal>

      <Modal open={moving !== null} onClose={() => setMoving(null)} className="modal-sm">
        <form className="confirm" onSubmit={submitMove}>
          <span className="icon-tile tile-blue tile-lg"><FolderInput /></span>
          <h3>Move to folder</h3>
          <select className="input" value={moving || ''} onChange={e => setMoving(e.target.value)}>
            <option value="">No folder</option>
            {folders.data?.items.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
          </select>
          <div className="confirm-actions">
            <button type="button" className="btn btn-outline" onClick={() => setMoving(null)}>Cancel</button>
            <button className="btn btn-orange" disabled={busy === 'move'}>{busy === 'move' && <Loader2 size={16} className="spin" />} Move</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
