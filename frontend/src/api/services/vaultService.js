import { api, download, upload } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock, mockDownload, uid } from '../mock'
import { vaultDb } from '../mocks/vault'

const folderName = id => vaultDb.folders.find(f => f.id === id)?.name
const withFolder = d => ({ ...d, folderName: folderName(d.folderId) })

/* ---------- mock implementations (mirror the real API's behaviour) ---------- */
function mockList({ category = 'all', folderId, q, status, sort = 'updated_desc' }) {
  let list = vaultDb.documents
  if (q) list = list.filter(d => d.name.toLowerCase().includes(q.toLowerCase()))
  if (category === 'favourites') list = list.filter(d => d.favourite)
  else if (category === 'shared') list = list.slice(1, 3)
  else if (category === 'trash') list = vaultDb.trash
  else if (category !== 'all') list = list.filter(d => d.category === category)
  if (folderId) list = list.filter(d => d.folderId === folderId)
  if (status) list = list.filter(d => d.status === status)
  const sorted = [...list].sort({
    updated_desc: (a, b) => b.updatedAt.localeCompare(a.updatedAt),
    updated_asc: (a, b) => a.updatedAt.localeCompare(b.updatedAt),
    name_asc: (a, b) => a.name.localeCompare(b.name),
    name_desc: (a, b) => b.name.localeCompare(a.name),
  }[sort])
  const unfiltered = category === 'all' && !folderId && !q && !status
  return { items: sorted.map(withFolder), total: unfiltered ? vaultDb.totalDocuments : sorted.length, page: 1, pageSize: 50 }
}

function mockUpdate(id, patch) {
  const d = vaultDb.documents.find(x => x.id === id)
  if (d) Object.assign(d, patch, { updatedAt: new Date().toISOString() })
  return withFolder(d)
}

export const vaultService = {
  /** -> { storage: { usedBytes, quotaBytes }, counts: { all, Contracts, ..., favourites, shared, trash } } */
  getStats: signal => (USE_MOCKS
    ? mock({ storage: vaultDb.storage, counts: { ...vaultDb.counts, favourites: vaultDb.documents.filter(d => d.favourite).length + 2 } })
    : api.get(EP.vault.stats, { signal })),

  /** -> { items: Folder[] } */
  listFolders: signal => (USE_MOCKS ? mock({ items: vaultDb.folders }) : api.get(EP.vault.folders, { signal })),
  createFolder: ({ name, color = '#0ea5e9' }) => {
    if (!USE_MOCKS) return api.post(EP.vault.folders, { name, color })
    const f = { id: uid('fld'), name, color, fileCount: 0 }
    vaultDb.folders.push(f)
    return mock(f, 150)
  },

  /** filters: { category, folderId, q, status, sort, page, pageSize } -> { items, total, page, pageSize } */
  listDocuments: (filters, signal) => (USE_MOCKS ? mock(mockList(filters)) : api.get(EP.vault.documents, { query: filters, signal })),

  /** Uploads straight into the vault. -> Document */
  uploadDocument: (file, { folderId, category, onProgress } = {}) => {
    if (!USE_MOCKS) return upload(EP.vault.documents, file, { fields: { folderId, category }, onProgress })
    const ext = file.name.split('.').pop().toLowerCase()
    const d = {
      id: uid('doc'), name: file.name, fileType: ['pdf', 'docx', 'xlsx', 'jpg', 'png'].includes(ext) ? ext : 'pdf',
      category: category || 'Personal', folderId: folderId || 'fld_personal', updatedAt: new Date().toISOString(),
      sizeBytes: file.size, status: 'secure', favourite: false, pages: 1, verified: false, tags: [],
    }
    vaultDb.documents.unshift(d)
    return mock(withFolder(d), 400)
  },

  /** -> Document (full metadata incl. tags, owner, verified, analysisId) */
  getDocument: (id, signal) => {
    if (!USE_MOCKS) return api.get(EP.vault.document(id), { signal })
    const d = vaultDb.documents.find(x => x.id === id) || vaultDb.documents[0]
    return mock({ ...withFolder(d), owner: 'You', uploadedAt: d.updatedAt })
  },

  /** -> { pageCount, fileUrl, pages: [{ number, html }] } - html must be sanitised server-side */
  getContent: (id, signal) => (USE_MOCKS ? mock({ pageCount: 12, fileUrl: null, pages: null }) : api.get(EP.vault.content(id), { signal })),

  /** patch: { name?, folderId?, category?, tags? } -> Document */
  updateDocument: (id, patch) => (USE_MOCKS ? mock(mockUpdate(id, patch), 150) : api.patch(EP.vault.document(id), patch)),

  setFavourite: (id, favourite) => (USE_MOCKS ? mock(mockUpdate(id, { favourite }), 100) : api.put(EP.vault.favourite(id), { favourite })),

  copyDocument: id => {
    if (!USE_MOCKS) return api.post(EP.vault.copy(id))
    const d = vaultDb.documents.find(x => x.id === id)
    const copy = { ...d, id: uid('doc'), name: d.name.replace(/(\.[a-z]+)$/i, ' (1)$1'), favourite: false }
    vaultDb.documents.unshift(copy)
    return mock(withFolder(copy), 200)
  },

  /** Moves to Trash (restorable for 30 days). */
  deleteDocument: id => {
    if (!USE_MOCKS) return api.delete(EP.vault.document(id))
    const d = vaultDb.documents.find(x => x.id === id)
    vaultDb.documents = vaultDb.documents.filter(x => x.id !== id)
    if (d) vaultDb.trash.push(d)
    return mock(null, 150)
  },

  downloadDocument: (id, name) => (USE_MOCKS ? mockDownload() : download(EP.vault.file(id), name)),

  /** -> { items: Note[] } */
  listNotes: (id, signal) => (USE_MOCKS ? mock({ items: vaultDb.notes[id] || [] }) : api.get(EP.vault.notes(id), { signal })),
  addNote: (id, text) => {
    if (!USE_MOCKS) return api.post(EP.vault.notes(id), { text })
    const n = { id: uid('note'), text, createdAt: new Date().toISOString() }
    vaultDb.notes[id] = [n, ...(vaultDb.notes[id] || [])]
    return mock(n, 150)
  },

  /** -> { items: ActivityEvent[] } */
  listActivity: (id, signal) => (USE_MOCKS ? mock({ items: vaultDb.activity }) : api.get(EP.vault.activity(id), { signal })),
}
