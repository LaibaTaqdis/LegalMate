import { api, upload } from '../client'
import { isMock } from '../config'
import { EP } from '../endpoints'
import { mock, uid } from '../mock'
import { vaultDb, vaultFilesDb } from '../mocks/vault'

const MOCK = () => isMock('vault')

/* ---------- mock implementations (mirror the real API's behaviour) ---------- */
const live = i => !i.trashedAt
function counts() {
  const all = vaultDb.items
  return { all: all.filter(live).length, answer: all.filter(i => live(i) && i.kind === 'answer').length, analysis: all.filter(i => live(i) && i.kind === 'analysis').length,
    brief: 0, calculation: all.filter(i => live(i) && i.kind === 'calculation').length, letter: all.filter(i => live(i) && i.kind === 'letter').length, favourites: all.filter(i => live(i) && i.favourite).length, trash: all.filter(i => !live(i)).length }
}
function mockList({ category = 'all', q, sort = 'updated_desc' }) {
  let list = vaultDb.items.filter(category === 'trash' ? i => !live(i) : live)
  if (category === 'favourites') list = list.filter(i => i.favourite)
  else if (['answer', 'analysis', 'brief', 'calculation', 'letter'].includes(category)) list = list.filter(i => i.kind === category)
  if (q) list = list.filter(i => (i.title + ' ' + i.summary).toLowerCase().includes(q.toLowerCase()))
  const cmp = { updated_desc: (a, b) => b.updatedAt.localeCompare(a.updatedAt), updated_asc: (a, b) => a.updatedAt.localeCompare(b.updatedAt),
    name_asc: (a, b) => a.title.localeCompare(b.title), name_desc: (a, b) => b.title.localeCompare(a.title) }[sort]
  const items = [...list].sort(cmp).map(({ content, ...rest }) => rest)
  return { items, total: items.length, page: 1, pageSize: 24, counts: counts() }
}
const find = id => vaultDb.items.find(i => i.id === id)
const touch = (i, patch = {}) => Object.assign(i, patch, { updatedAt: new Date().toISOString() })
const log = (id, action) => { vaultDb.activity[id] = [{ action, createdAt: new Date().toISOString() }, ...(vaultDb.activity[id] || [])] }


/* ---------- part B (your own files): mock implementations ---------- */
const CATEGORIES = ['Contracts', 'Notices', 'Court Documents', 'Property', 'Personal', 'Family', 'Other']
const fdb = vaultFilesDb
const fileCounts = () => {
  const live = fdb.files.filter(f => !f.trashedAt)
  return { all: live.length, favourites: live.filter(f => f.favourite).length, trash: fdb.files.length - live.length, ...Object.fromEntries(CATEGORIES.map(c => [c, live.filter(f => f.category === c).length])) }
}
const findFile = id => fdb.files.find(f => f.id === id)
const touchFile = (f, patch = {}) => Object.assign(f, patch, { updatedAt: new Date().toISOString() })
const fileLog = (id, action) => { fdb.activity[id] = [{ action, createdAt: new Date().toISOString() }, ...(fdb.activity[id] || [])] }
const folderName = id => fdb.folders.find(f => f.id === id)?.name || null
const syncFolders = () => fdb.folders.forEach(fo => { fo.fileCount = fdb.files.filter(f => f.folderId === fo.id && !f.trashedAt).length })
function mockFiles({ category = 'all', folderId, q, sort = 'updated_desc' }) {
  let list = fdb.files.filter(category === 'trash' ? f => f.trashedAt : f => !f.trashedAt)
  if (category === 'favourites') list = list.filter(f => f.favourite)
  else if (CATEGORIES.includes(category)) list = list.filter(f => f.category === category)
  if (folderId) list = list.filter(f => f.folderId === folderId)
  if (q) list = list.filter(f => f.name.toLowerCase().includes(q.toLowerCase()))
  const cmp = { updated_desc: (a, b) => b.updatedAt.localeCompare(a.updatedAt), updated_asc: (a, b) => a.updatedAt.localeCompare(b.updatedAt),
    name_asc: (a, b) => a.name.localeCompare(b.name), name_desc: (a, b) => b.name.localeCompare(a.name), size_desc: (a, b) => b.sizeBytes - a.sizeBytes }[sort]
  const items = [...list].sort(cmp)
  const used = fdb.files.reduce((n, f) => n + f.sizeBytes, 0)
  return { items, total: items.length, page: 1, pageSize: 24, counts: fileCounts(), storage: { usedBytes: used, quotaBytes: fdb.storage.quotaBytes } }
}

export const vaultService = {
  /** -> { counts: { all, answer, analysis, brief, favourites, trash } } */
  getStats: signal => (MOCK() ? mock({ counts: counts(), files: fileCounts(), storage: vaultFilesDb.storage, filesEnabled: true }, 150) : api.get(EP.vault.stats, { signal })),

  /** filters: { category: all|answer|analysis|brief|calculation|letter|favourites|trash, q, sort: updated_desc|updated_asc|name_asc|name_desc, page, pageSize }
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

  /* ---------- part B: your own files ---------- */
  /** filters: { category: all|favourites|trash|<a category>, folderId, q, sort, page, pageSize } -> { items: VaultFile[], total, page, pageSize, counts, storage } */
  listFiles: (filters, signal) => (MOCK() ? mock(mockFiles(filters)) : api.get(EP.vault.files, { query: filters, signal })),
  getFile: (id, signal) => (MOCK() ? mock(findFile(id) || fdb.files[0]) : api.get(EP.vault.file(id), { signal })),
  /** Uploads one file into the Vault. -> VaultFile (photos and scans have textStatus 'pending' for a moment while they are read) */
  uploadFile: (file, { folderId, category, onProgress } = {}) => {
    if (!MOCK()) return upload(EP.vault.files, file, { fields: { folderId, category }, onProgress })
    const ext = file.name.split('.').pop().toLowerCase().replace('jpeg', 'jpg')
    const f = { id: uid('vf'), name: file.name, fileType: ['pdf', 'docx', 'jpg', 'png'].includes(ext) ? ext : 'pdf', category: category || 'Other', folderId: folderId || null,
      folderName: folderName(folderId), sizeBytes: file.size, pages: 1, favourite: false, noteCount: 0, textStatus: 'ready', hasText: true,
      uploadedAt: new Date().toISOString(), updatedAt: new Date().toISOString(), trashedAt: null }
    fdb.files.unshift(f); syncFolders(); fileLog(f.id, 'uploaded')
    return mock(f, 500)
  },
  /** A short-lived link (about 5 minutes): download=true saves the file, otherwise it opens in place. -> { url, expiresIn } */
  getFileLink: (id, download = false) => (MOCK() ? mock({ url: null, expiresIn: 300 }, 100) : api.get(EP.vault.fileLink(id), { query: { download } })),
  /** The text read from the file (for Word files and search). -> { text, truncated, status } */
  getFileText: (id, signal) => (MOCK() ? mock({ text: 'TENANCY AGREEMENT\n\nThe monthly rent is PKR 45,000 payable by the 5th of each month.', truncated: false, status: 'ready' }) : api.get(EP.vault.fileText(id), { signal })),
  /** patch: { name?, folderId? (null = no folder), category? } -> VaultFile */
  updateFile: (id, patch) => {
    if (!MOCK()) return api.patch(EP.vault.file(id), patch)
    const f = findFile(id)
    if ('folderId' in patch) patch = { ...patch, folderName: folderName(patch.folderId) }
    touchFile(f, patch); syncFolders()
    for (const k of ['name', 'folderId', 'category']) if (k in patch) fileLog(id, { name: 'renamed', folderId: 'moved', category: 'categorised' }[k])
    return mock(f, 150)
  },
  setFileFavourite: (id, favourite) => {
    if (!MOCK()) return api.put(EP.vault.fileFavourite(id), { favourite })
    touchFile(findFile(id), { favourite }); fileLog(id, favourite ? 'favourited' : 'unfavourited')
    return mock(null, 100)
  },
  trashFile: id => {
    if (!MOCK()) return api.delete(EP.vault.file(id))
    touchFile(findFile(id), { trashedAt: new Date().toISOString() }); syncFolders(); fileLog(id, 'trashed')
    return mock(null, 150)
  },
  restoreFile: id => {
    if (!MOCK()) return api.post(EP.vault.fileRestore(id))
    touchFile(findFile(id), { trashedAt: null }); syncFolders(); fileLog(id, 'restored')
    return mock(null, 150)
  },
  deleteFileForever: id => {
    if (!MOCK()) return api.delete(EP.vault.file(id), { query: { permanent: true } })
    fdb.files = fdb.files.filter(f => f.id !== id)
    return mock(null, 150)
  },
  emptyFilesTrash: () => {
    if (!MOCK()) return api.delete(EP.vault.filesTrash)
    const n = fdb.files.filter(f => f.trashedAt).length
    fdb.files = fdb.files.filter(f => !f.trashedAt)
    return mock({ deleted: n }, 200)
  },
  listFileNotes: (id, signal) => (MOCK() ? mock({ items: fdb.notes[id] || [] }) : api.get(EP.vault.fileNotes(id), { signal })),
  addFileNote: (id, text) => {
    if (!MOCK()) return api.post(EP.vault.fileNotes(id), { text })
    const n = { id: uid('vn'), text, createdAt: new Date().toISOString() }
    fdb.notes[id] = [n, ...(fdb.notes[id] || [])]
    const f = findFile(id); touchFile(f, { noteCount: (f.noteCount || 0) + 1 }); fileLog(id, 'noted')
    return mock(n, 150)
  },
  deleteFileNote: (id, noteId) => {
    if (!MOCK()) return api.delete(EP.vault.fileNote(id, noteId))
    fdb.notes[id] = (fdb.notes[id] || []).filter(n => n.id !== noteId)
    const f = findFile(id); if (f) f.noteCount = Math.max(0, (f.noteCount || 1) - 1)
    return mock(null, 100)
  },
  listFileActivity: (id, signal) => (MOCK() ? mock({ items: fdb.activity[id] || [] }) : api.get(EP.vault.fileActivity(id), { signal })),

  /** -> { items: [{ id, name, color, fileCount }] } */
  listFolders: signal => (MOCK() ? (syncFolders(), mock({ items: fdb.folders })) : api.get(EP.vault.folders, { signal })),
  createFolder: ({ name, color }) => {
    if (!MOCK()) return api.post(EP.vault.folders, { name, color })
    const fo = { id: uid('fo'), name, color: color || '#0ea5e9', fileCount: 0 }
    fdb.folders.push(fo)
    return mock(fo, 150)
  },
  updateFolder: (id, patch) => {
    if (!MOCK()) return api.patch(EP.vault.folder(id), patch)
    const fo = fdb.folders.find(x => x.id === id); Object.assign(fo, patch)
    fdb.files.forEach(f => { if (f.folderId === id) f.folderName = fo.name })
    return mock(fo, 150)
  },
  /** The files inside are kept; they just have no folder any more. */
  deleteFolder: id => {
    if (!MOCK()) return api.delete(EP.vault.folder(id))
    fdb.folders = fdb.folders.filter(x => x.id !== id)
    fdb.files.forEach(f => { if (f.folderId === id) { f.folderId = null; f.folderName = null } })
    return mock(null, 150)
  },

  /** -> { items: [{ action: saved|renamed|favourited|unfavourited|noted|trashed|restored, createdAt }] } newest first */
  listActivity: (id, signal) => (MOCK() ? mock({ items: vaultDb.activity[id] || [] }) : api.get(EP.vault.activity(id), { signal })),
}
