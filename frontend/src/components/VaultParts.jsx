import { useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { useUI } from './UIContext'
import { useQuery } from '../hooks/useApi'
import { formatDateTime } from '../utils/format'

export const ACTION_LABEL = {
  saved: 'Saved to the Vault', uploaded: 'Uploaded', renamed: 'Renamed', moved: 'Moved to another folder', categorised: 'Category changed', downloaded: 'Downloaded',
  favourited: 'Added to favourites', unfavourited: 'Removed from favourites', noted: 'Note added', trashed: 'Moved to Trash', restored: 'Restored from Trash',
}

/** Notes on a Vault item or file. `api`: { list(id, signal), add(id, text), remove(id, noteId) }. */
export function VaultNotes({ id, locked, api, onChanged }) {
  const { toast } = useUI()
  const q = useQuery(signal => api.list(id, signal), [id])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const add = async e => {
    e.preventDefault()
    if (!text.trim()) return
    setBusy(true)
    try { await api.add(id, text.trim()); setText(''); q.reload({ silent: true }); onChanged?.() } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }
  const remove = async n => {
    q.setData(d => ({ ...d, items: d.items.filter(x => x.id !== n.id) }))
    try { await api.remove(id, n.id); onChanged?.() } catch (err) { toast(err.message, 'info'); q.reload({ silent: true }) }
  }
  return (
    <section className="card vi-notes">
      <h3>Notes</h3>
      {!locked && (
        <form className="vi-note-form" onSubmit={add}>
          <textarea value={text} maxLength={2000} onChange={e => setText(e.target.value)} placeholder="Add a note for yourself…" aria-label="New note" />
          <div><span>{text.length}/2000</span><button className="btn btn-outline btn-sm" disabled={busy || !text.trim()}>{busy && <Loader2 size={15} className="spin" />} Add note</button></div>
        </form>
      )}
      {q.data?.items.length === 0 && <p className="vi-empty">{locked ? 'No notes.' : 'No notes yet.'}</p>}
      {q.data?.items.map(n => (
        <div key={n.id} className="vi-note">
          <div><p>{n.text}</p><small>{formatDateTime(n.createdAt)}</small></div>
          {!locked && <button className="icon-btn-plain" aria-label="Delete note" onClick={() => remove(n)}><X size={16} /></button>}
        </div>
      ))}
    </section>
  )
}

/** What happened to a Vault item or file, newest first. `load(id, signal)`; `version` reloads it after a change. */
export function VaultActivity({ id, version, load }) {
  const q = useQuery(signal => load(id, signal), [id, version])
  return (
    <section className="card vi-activity">
      <h3>Activity</h3>
      <ul className="vi-log">
        {q.data?.items.map((a, i) => <li key={i}>{ACTION_LABEL[a.action] || a.action}<span>{formatDateTime(a.createdAt)}</span></li>)}
      </ul>
    </section>
  )
}
