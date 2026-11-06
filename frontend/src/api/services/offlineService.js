import { api } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock, uid } from '../mock'

/*
 * Offline support.
 * - Writes made while offline are queued locally (localStorage) as operations.
 * - When the connection returns, the queue is sent to POST /sync in one batch.
 * - GET /offline/manifest tells the app which documents / briefs / guides to cache for offline use.
 */

const QUEUE_KEY = 'legalmate.offline.queue'
const SYNC_KEY = 'legalmate.offline.lastSync'

// Design demo items, used to seed the queue in mock mode.
const DEMO_QUEUE = [
  { id: 'op_1', type: 'note.create', title: 'New note', subtitle: 'Tenancy Agreement', createdAt: '2026-09-24T14:15:00', payload: {} },
  { id: 'op_2', type: 'brief.update', title: 'Edited brief', subtitle: 'Ahmad Khan vs State', createdAt: '2026-09-24T13:40:00', payload: {} },
  { id: 'op_3', type: 'calculation.save', title: 'Saved calculation', subtitle: 'Court Fee Estimate', createdAt: '2026-09-24T12:20:00', payload: {} },
  { id: 'op_4', type: 'bookmark.create', title: 'New bookmark', subtitle: 'Section 379 PPC', createdAt: '2026-09-24T11:05:00', payload: {} },
]

const read = (key, fallback) => {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback } catch { return fallback }
}
const write = (key, value) => { try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* storage full or blocked */ } }

export const offlineQueue = {
  list: () => read(QUEUE_KEY, USE_MOCKS ? DEMO_QUEUE : []),
  /** Queue a write to replay later. type e.g. 'note.create', payload = the API request body. */
  add: (type, payload, { title, subtitle } = {}) => {
    const op = { id: uid('op'), type, payload, title, subtitle, createdAt: new Date().toISOString() }
    write(QUEUE_KEY, [...offlineQueue.list(), op])
    return op
  },
  remove: id => write(QUEUE_KEY, offlineQueue.list().filter(o => o.id !== id)),
  clear: () => write(QUEUE_KEY, []),
}

export const offlineService = {
  /** What is cached on this device. -> { documents, briefs, conversations, guides } */
  getAvailable: () => mock(USE_MOCKS
    ? { documents: 12, briefs: 5, conversations: 28, guides: 18 }
    : read('legalmate.offline.cache', { documents: 0, briefs: 0, conversations: 0, guides: 0 }), 150),

  /** List of items the server recommends caching. -> { documents: [{id, updatedAt, url}], briefs: [...], guides: [...] } */
  getManifest: signal => (USE_MOCKS ? mock({ documents: [], briefs: [], guides: [] }) : api.get(EP.offline.manifest, { signal })),

  lastSync: () => read(SYNC_KEY, USE_MOCKS ? '2026-09-22T10:24:00' : null),

  /** Browser storage usage. -> { usedBytes, quotaBytes } */
  storageEstimate: async () => {
    if (!USE_MOCKS && navigator.storage?.estimate) {
      const { usage, quota } = await navigator.storage.estimate()
      return { usedBytes: usage || 0, quotaBytes: quota || 0 }
    }
    return { usedBytes: 2.1e9, quotaBytes: 5e9 }
  },

  /**
   * Replays queued operations. -> { synced: number, failed: [{ id, error }], syncedAt }
   * Real backend: POST /sync { operations: [{ id, type, payload, createdAt }] }
   */
  sync: async () => {
    const operations = offlineQueue.list()
    let res
    if (USE_MOCKS) res = await mock({ results: operations.map(o => ({ id: o.id, status: 'ok' })), syncedAt: new Date().toISOString() }, 1200)
    else res = await api.post(EP.offline.sync, { operations: operations.map(({ id, type, payload, createdAt }) => ({ id, type, payload, createdAt })) })
    const failed = res.results.filter(r => r.status !== 'ok')
    write(QUEUE_KEY, operations.filter(o => failed.some(f => f.id === o.id)))
    write(SYNC_KEY, res.syncedAt)
    return { synced: operations.length - failed.length, failed, syncedAt: res.syncedAt }
  },
}
