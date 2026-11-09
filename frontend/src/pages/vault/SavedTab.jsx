import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ChevronDown, ChevronLeft, ChevronRight, FileText, FolderOpen, Folder, LayoutGrid, List, Loader2, MessageCircleMore, MoreVertical,
  Pencil, RotateCcw, Search, Star, Trash2
} from 'lucide-react'
import { Modal, useClickOutside } from '../../components/common'
import { useUI } from '../../components/UIContext'
import { ErrorState, Skeleton } from '../../components/States'
import { useQuery } from '../../hooks/useApi'
import { useDebounced } from '../../hooks/useDebounced'
import { vaultService } from '../../api/services/vaultService'
import { formatDate } from '../../utils/format'

const CATEGORIES = [
  { key: 'all', label: 'All Saved', icon: Folder },
  { key: 'answer', label: 'Chat Answers', icon: MessageCircleMore },
  { key: 'analysis', label: 'Analyses', icon: FileText },
  { key: 'favourites', label: 'Favourites', icon: Star },
  { key: 'trash', label: 'Trash', icon: Trash2 },
]
const SORTS = [['Updated (Newest)', 'updated_desc'], ['Updated (Oldest)', 'updated_asc'], ['Name (A–Z)', 'name_asc'], ['Name (Z–A)', 'name_desc']]
const KIND_LABEL = { answer: 'Chat answer', analysis: 'Analysis', brief: 'Case brief' }
const KIND_ICON = { answer: MessageCircleMore, analysis: FileText, brief: FileText }
const RISK_PILL = { Low: 'pill-green', Medium: 'pill-orange', High: 'pill-red' }
const EMPTY = {
  all: ['Nothing saved yet', 'Use “Save to Vault” under a chat answer or on an analysis, and it will be kept here.'],
  answer: ['No saved answers', 'Use “Save to Vault” under an answer in the chat to keep it here.'],
  analysis: ['No saved analyses', 'Open a finished analysis and choose “Save to Vault”.'],
  favourites: ['No favourites yet', 'Tap the star on a saved item to keep it handy.'],
  trash: ['The Trash is empty', 'Items you delete wait here for 30 days before they are removed for good.'],
}

export default function SavedTab() {
  const navigate = useNavigate()
  const { toast } = useUI()
  const [view, setView] = useState('grid')
  const [cat, setCat] = useState('all')
  const [q, setQ] = useState('')
  const [sort, setSort] = useState(SORTS[0])
  const [sortOpen, setSortOpen] = useState(false)
  const [page, setPage] = useState(1)
  const [menu, setMenu] = useState(null)
  const [renaming, setRenaming] = useState(null)        // { id, title }
  const [busy, setBusy] = useState(false)
  const [confirmEmpty, setConfirmEmpty] = useState(false)
  const sortRef = useClickOutside(() => setSortOpen(false))
  const menuRef = useClickOutside(() => setMenu(null))
  const search = useDebounced(q, 300)

  const list = useQuery(signal => vaultService.listItems({ category: cat, q: search || undefined, sort: sort[1], page }, signal), [cat, search, sort[1], page])
  useEffect(() => { setPage(1) }, [cat, search, sort[1]])
  const items = list.data?.items || []
  const counts = list.data?.counts
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.pageSize)) : 1

  const refresh = () => list.reload({ silent: true })
  const run = async (fn, msg) => {
    setMenu(null)
    try { await fn(); if (msg) toast(msg) ; refresh() } catch (e) { toast(e.message, 'info'); refresh() }
  }
  const toggleFav = i => {
    list.setData(x => ({ ...x, items: x.items.map(y => (y.id === i.id ? { ...y, favourite: !y.favourite } : y)) }))
    run(() => vaultService.setFavourite(i.id, !i.favourite))
  }
  const rename = async e => {
    e.preventDefault()
    const title = renaming.title.trim()
    if (!title) return
    setBusy(true)
    try { await vaultService.rename(renaming.id, title); toast('Renamed'); setRenaming(null); refresh() } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }
  const emptyTrash = async () => {
    setBusy(true)
    try { const r = await vaultService.emptyTrash(); toast(`Trash emptied (${r?.deleted ?? 0} deleted)`); setConfirmEmpty(false); refresh() } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }

  const open = i => navigate(`/vault/item/${i.id}`)
  const inTrash = cat === 'trash'
  const [emptyTitle, emptyText] = EMPTY[cat]

  const Menu = ({ i }) => (
    <div className="top-pop" ref={menu === i.id ? menuRef : null}>
      <button className="icon-btn-plain doc-kebab" aria-label="Item options" onClick={e => { e.stopPropagation(); setMenu(menu === i.id ? null : i.id) }}><MoreVertical size={19} /></button>
      {menu === i.id && (
        <div className="popover popover-sm doc-menu" onClick={e => e.stopPropagation()}>
          <button className="popover-item" onClick={() => open(i)}>Open</button>
          {inTrash ? (
            <>
              <button className="popover-item" onClick={() => run(() => vaultService.restore(i.id), 'Restored')}><RotateCcw size={15} /> Restore</button>
              <button className="popover-item danger" onClick={() => run(() => vaultService.deleteForever(i.id), 'Deleted for good')}>Delete forever</button>
            </>
          ) : (
            <>
              <button className="popover-item" onClick={() => { setMenu(null); setRenaming({ id: i.id, title: i.title }) }}><Pencil size={15} /> Rename</button>
              <button className="popover-item danger" onClick={() => run(() => vaultService.trash(i.id), 'Moved to Trash')}>Move to Trash</button>
            </>
          )}
        </div>
      )}
    </div>
  )

  const Meta = ({ i }) => (
    <>
      <span className="vi-kind">{KIND_LABEL[i.kind] || i.kind}</span>
      {i.tag && <span className="vi-tag">{i.tag}</span>}
      {i.kind === 'analysis' && i.risk && <span className={`pill ${RISK_PILL[i.risk] || 'pill-gray'}`}>{i.risk} risk</span>}
    </>
  )

  return (
    <div className="vault-tab">
      <div className="vault-bar">
        <label className="vault-search"><Search size={19} /><input value={q} onChange={e => setQ(e.target.value)} placeholder="Search saved items..." /></label>
          <div className="view-toggle">
            <button className={view === 'grid' ? 'active' : ''} onClick={() => setView('grid')} aria-label="Grid view"><LayoutGrid size={20} /></button>
            <button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')} aria-label="List view"><List size={20} /></button>
          </div>
      </div>

      <div className="vault-grid">
        <aside className="vault-side">
          <section className="card vault-files">
            <h2 className="card-title">Saved in Vault</h2>
            <ul>
              {CATEGORIES.map(c => (
                <li key={c.key}>
                  <button className={cat === c.key ? 'active' : ''} onClick={() => setCat(c.key)}>
                    {c.key === 'favourites' ? <Star size={19} fill="#f59e0b" color="#f59e0b" /> : c.key === 'all' ? <Folder size={19} fill="#1d5fd6" color="#1d5fd6" /> : <c.icon size={19} />}
                    <span>{c.label}</span><em>{counts?.[c.key] ?? ''}</em>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </aside>

        <section className="card vault-docs">
          <div className="card-head">
            <h2 className="vault-h2">{CATEGORIES.find(c => c.key === cat).label} <span>({list.data?.total ?? 0})</span></h2>
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
          {inTrash && <p className="vault-note">Items stay in the Trash for 30 days and are then deleted for good. Restore one to keep it.</p>}

          {list.error && !list.data && <ErrorState compact error={list.error} onRetry={list.reload} />}
          {!list.data && list.loading && <div className="doc-grid">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} h={150} r={10} />)}</div>}
          {list.data && items.length === 0 && (
            <div className="vault-empty"><FolderOpen size={40} /><b>{search ? 'Nothing matches your search' : emptyTitle}</b><p>{search ? 'Try a different word.' : emptyText}</p></div>
          )}

          {items.length > 0 && (view === 'grid' ? (
            <div className={`doc-grid ${list.loading ? 'is-refreshing' : ''}`}>
              {items.map(i => {
                const Icon = KIND_ICON[i.kind] || FileText
                return (
                  <div key={i.id} className="doc-card vi-card" onClick={() => open(i)}>
                    <div className="doc-card-top">
                      <span className={`vi-icon vi-${i.kind}`}><Icon size={24} /></span>
                      <div className="doc-card-info"><b dir="auto" title={i.title}>{i.title}</b><div className="vi-meta"><Meta i={i} /></div></div>
                      <Menu i={i} />
                    </div>
                    <p className="vi-summary" dir="auto">{i.summary}</p>
                    <div className="doc-card-foot">
                      <small>{inTrash ? `Deleted ${formatDate(i.trashedAt)}` : `Saved ${formatDate(i.savedAt)}`}{i.noteCount > 0 && ` • ${i.noteCount} note${i.noteCount > 1 ? 's' : ''}`}</small>
                      {!inTrash && <button className={`icon-btn-plain doc-star ${i.favourite ? 'on' : ''}`} onClick={e => { e.stopPropagation(); toggleFav(i) }} aria-label="Favourite"><Star size={21} /></button>}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className={`doc-table vi-table ${list.loading ? 'is-refreshing' : ''}`}>
              <div className="doc-tr doc-th"><span>Title</span><span>Type</span><span>Saved</span><span>Notes</span><span /><span /></div>
              {items.map(i => (
                <div key={i.id} className="doc-tr" onClick={() => open(i)}>
                  <span className="doc-td-name"><b dir="auto">{i.title}</b></span>
                  <span className="vi-meta"><Meta i={i} /></span>
                  <span>{formatDate(inTrash ? i.trashedAt : i.savedAt)}</span>
                  <span>{i.noteCount || ''}</span>
                  {!inTrash ? <button className={`icon-btn-plain doc-star ${i.favourite ? 'on' : ''}`} onClick={e => { e.stopPropagation(); toggleFav(i) }} aria-label="Favourite"><Star size={19} /></button> : <span />}
                  <Menu i={i} />
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

      <Modal open={renaming !== null} onClose={() => setRenaming(null)} className="modal-sm">
        <form className="confirm" onSubmit={rename}>
          <span className="icon-tile tile-blue tile-lg"><Pencil /></span>
          <h3>Rename</h3>
          <input autoFocus className="input" maxLength={160} value={renaming?.title || ''} onChange={e => setRenaming(r => ({ ...r, title: e.target.value }))} placeholder="Title" />
          <div className="confirm-actions">
            <button type="button" className="btn btn-outline" onClick={() => setRenaming(null)}>Cancel</button>
            <button className="btn btn-orange" disabled={busy || !renaming?.title.trim()}>{busy && <Loader2 size={16} className="spin" />} Save</button>
          </div>
        </form>
      </Modal>

      <Modal open={confirmEmpty} onClose={() => setConfirmEmpty(false)} className="modal-sm">
        <div className="confirm">
          <span className="icon-tile tile-red tile-lg"><Trash2 /></span>
          <h3>Empty the Trash?</h3>
          <p>Everything in the Trash will be deleted for good. This cannot be undone.</p>
          <div className="confirm-actions">
            <button className="btn btn-outline" onClick={() => setConfirmEmpty(false)}>Cancel</button>
            <button className="btn btn-orange" onClick={emptyTrash} disabled={busy}>{busy && <Loader2 size={16} className="spin" />} Delete everything</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
