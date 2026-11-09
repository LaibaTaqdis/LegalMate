import { api } from '../client'
import { isMock } from '../config'
import { EP } from '../endpoints'
import { mock, uid } from '../mock'
import { vaultDb } from '../mocks/vault'

const MOCK = () => isMock('vault')

/* ---------- mock implementations (mirror the real API's behaviour) ---------- */
const live = i => !i.trashedAt
function counts() {
  const all = vaultDb.items
  return { all: all.filter(live).length, answer: all.filter(i => live(i) && i.kind === 'answer').length, analysis: all.filter(i => live(i) && i.kind === 'analysis').length,
    brief: 0, favourites: all.filter(i => live(i) && i.favourite).length, trash: all.filter(i => !live(i)).length }
}
function mockList({ category = 'all', q, sort = 'updated_desc' }) {
  let list = vaultDb.items.filter(category === 'trash' ? i => !live(i) : live)
  if (category === 'favourites') list = list.filter(i => i.favourite)
  else if (['answer', 'analysis', 'brief'].includes(category)) list = list.filter(i => i.kind === category)
  if (q) list = list.filter(i => (i.title + ' ' + i.summary).toLowerCase().includes(q.toLowerCase()))
  const cmp = { updated_desc: (a, b) => b.updatedAt.localeCompare(a.updatedAt), updated_asc: (a, b) => a.updatedAt.localeCompare(b.updatedAt),
    name_asc: (a, b) => a.title.localeCompare(b.title), name_desc: (a, b) => b.title.localeCompare(a.title) }[sort]
  const items = [...list].sort(cmp).map(({ content, ...rest }) => rest)
  return { items, total: items.length, page: 1, pageSize: 24, counts: counts() }
}
const find = id => vaultDb.items.find(i => i.id === id)
const touch = (i, patch = {}) => Object.assign(i, patch, { updatedAt: new Date().toISOString() })
const log = (id, action) => { vaultDb.activity[id] = [{ action, createdAt: new Date().toISOString() }, ...(vaultDb.activity[id] || [])] }

export const vaultService = {
  /** -> { counts: { all, answer, analysis, brief, favourites, trash } } */
  getStats: signal => (MOCK() ? mock({ counts: counts() }, 150) : api.get(EP.vault.stats, { signal })),

  /** filters: { category: all|answer|analysis|brief|favourites|trash, q, sort: updated_desc|updated_asc|name_asc|name_desc, page, pageSize }
   *  -> { items: SavedItem[], total, page, pageSize, counts } */
  listItems: (filters, signal) => (MOCK() ? mock(mockList(filters)) : api.get(EP.vault.items, { query: filters, signal })),

  /** -> SavedItem + content (answer: { question, answer: Message }; analysis: the analysis result) */
  getItem: (id, signal) => (MOCK() ? mock(find(id) || vaultDb.items[0]) : api.get(EP.vault.item(id), { signal })),

  /** Saves a chat answer or a finished analysis. ref: { kind: 'answer', messageId } | { kind: 'analysis', analysisId } -> { id, alreadySaved } */
  save: ref => (MOCK() ? mock({ id: uid('vi'), alreadySaved: false }, 300) : api.post(EP.vault.items, ref)),

  rename: (id, title) => {
    if (!MOCK()) return api.patch(EP.vault.item(id), { title })
    const i = find(id); touch(i, { title }); log(id, 'renamed')
    return mock(i, 150)
  },
  setFavourite: (id, favourite) => {
    if (!MOCK()) return api.put(EP.vault.favourite(id), { favourite })
    touch(find(id), { favourite }); log(id, favourite ? 'favourited' : 'unfavourited')
    return mock(null, 100)
  },
  /** Moves to the Trash (emptied by the server after 30 days). */
  trash: id => {
    if (!MOCK()) return api.delete(EP.vault.item(id))
    touch(find(id), { trashedAt: new Date().toISOString() }); log(id, 'trashed')
    return mock(null, 150)
  },
  restore: id => {
    if (!MOCK()) return api.post(EP.vault.restore(id))
    touch(find(id), { trashedAt: null }); log(id, 'restored')
    return mock(null, 150)
  },
  /** Only for an item that is already in the Trash. */
  deleteForever: id => {
    if (!MOCK()) return api.delete(EP.vault.item(id), { query: { permanent: true } })
    vaultDb.items = vaultDb.items.filter(i => i.id !== id)
    return mock(null, 150)
  },
  emptyTrash: () => {
    if (!MOCK()) return api.delete(EP.vault.trash)
    const n = vaultDb.items.filter(i => !live(i)).length
    vaultDb.items = vaultDb.items.filter(live)
    return mock({ deleted: n }, 200)
  },

  /** -> { items: Note[] } newest first */
  listNotes: (id, signal) => (MOCK() ? mock({ items: vaultDb.notes[id] || [] }) : api.get(EP.vault.notes(id), { signal })),
  addNote: (id, text) => {
    if (!MOCK()) return api.post(EP.vault.notes(id), { text })
    const n = { id: uid('vn'), text, createdAt: new Date().toISOString() }
    vaultDb.notes[id] = [n, ...(vaultDb.notes[id] || [])]
    const i = find(id); touch(i, { noteCount: (i.noteCount || 0) + 1 }); log(id, 'noted')
    return mock(n, 150)
  },
  deleteNote: (id, noteId) => {
    if (!MOCK()) return api.delete(EP.vault.note(id, noteId))
    vaultDb.notes[id] = (vaultDb.notes[id] || []).filter(n => n.id !== noteId)
    const i = find(id); if (i) i.noteCount = Math.max(0, (i.noteCount || 1) - 1)
    return mock(null, 100)
  },

  /** -> { items: [{ action: saved|renamed|favourited|unfavourited|noted|trashed|restored, createdAt }] } newest first */
  listActivity: (id, signal) => (MOCK() ? mock({ items: vaultDb.activity[id] || [] }) : api.get(EP.vault.activity(id), { signal })),
}
