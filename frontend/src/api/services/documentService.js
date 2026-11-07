import { api, download, upload } from '../client'
import { isMock } from '../config'
import { EP } from '../endpoints'
import { mock, mockDownload, sleep, uid } from '../mock'
import { MOCK_ANALYSIS, MOCK_ANALYSIS_HISTORY } from '../mocks/documents'

const MOCK = () => isMock('documents')
let mockHistory = [...MOCK_ANALYSIS_HISTORY]
export const ACCEPTED_TYPES = ['pdf', 'docx', 'jpg', 'png']
// Keep VITE_MAX_UPLOAD_MB equal to the backend's MAX_UPLOAD_MB; the server enforces its own limit anyway.
export const MAX_UPLOAD_MB = Number(import.meta.env.VITE_MAX_UPLOAD_MB || 10)
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

export const documentService = {
  /**
   * Uploads a file for analysis / storage. -> { id, name, sizeBytes, fileType, pages }
   * `startAt` only affects the mock progress animation.
   */
  upload: async (file, { onProgress, signal, saveToVault = false, startAt = 0 } = {}) => {
    if (!MOCK()) return upload(EP.documents.upload, file, { fields: { purpose: 'analysis', saveToVault: !!saveToVault }, onProgress, signal })
    for (let p = startAt; p < 100; p = Math.min(100, p + 7)) {
      if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
      onProgress?.(p)
      await sleep(350)
    }
    onProgress?.(100)
    return { id: uid('doc'), name: file.name, sizeBytes: file.size, fileType: file.name.split('.').pop().toLowerCase() }
  },

  /** Discards an uploaded (not yet analysed) document. */
  remove: id => (MOCK() ? mock(null, 100) : api.delete(`${EP.documents.upload}/${id}`)),

  /**
   * Starts an analysis job. -> { id, status }
   * options: { documentIds, language: 'auto'|'en'|'ur', depth: 'quick'|'detailed', saveToVault }
   */
  startAnalysis: options => (MOCK() ? mock({ id: 'tenancy', status: 'processing' }) : api.post(EP.documents.analyses, options)),

  /**
   * The user's analysis history. filters: { q, risk: all|High|Medium|Low, status: all|completed|running|failed, days: 0|7|30|90,
   * sort: newest|oldest|name|risk, page, pageSize } -> { items, total, page, pageSize, counts }
   */
  listAnalyses: (filters = {}, signal) => {
    if (!MOCK()) return api.get(EP.documents.analyses, { query: filters, signal })
    const f = { risk: 'all', status: 'all', days: '0', sort: 'newest', page: '1', ...filters }
    let list = mockHistory.filter(a => (!f.q || a.name.toLowerCase().includes(f.q.toLowerCase())) && (f.risk === 'all' || a.risk === f.risk)
      && (f.status === 'all' || a.status === (f.status === 'running' ? 'processing' : f.status))
      && (Number(f.days) === 0 || Date.now() - new Date(a.createdAt).getTime() < Number(f.days) * 86400000))
    const risk = { High: 3, Medium: 2, Low: 1 }
    list = [...list].sort({ newest: (a, b) => b.createdAt.localeCompare(a.createdAt), oldest: (a, b) => a.createdAt.localeCompare(b.createdAt),
      name: (a, b) => a.name.localeCompare(b.name), risk: (a, b) => (risk[b.risk] || 0) - (risk[a.risk] || 0) }[f.sort])
    const size = Number(f.pageSize) || 10
    const counts = { all: mockHistory.length, completed: 0, running: 0, failed: 0, High: 0, Medium: 0, Low: 0 }
    mockHistory.forEach(a => { counts[a.status === 'processing' ? 'running' : a.status]++; if (a.risk) counts[a.risk]++ })
    return mock({ items: list.slice((Number(f.page) - 1) * size, Number(f.page) * size), total: list.length, page: Number(f.page), pageSize: size, counts })
  },

  deleteAnalysis: id => {
    if (!MOCK()) return api.delete(EP.documents.analysis(id))
    mockHistory = mockHistory.filter(a => a.id !== id)
    return mock(null, 150)
  },

  /** -> Analysis (poll while status is 'queued' or 'processing') */
  getAnalysis: (id, signal) => (MOCK() ? mock(MOCK_ANALYSIS) : api.get(EP.documents.analysis(id), { signal })),

  downloadReport: (id, name = 'Analysis_Report.pdf') => (MOCK() ? mockDownload() : download(EP.documents.analysisReport(id), name)),

  /** Saves the analysed document + report into the Legal Vault. -> { vaultDocumentId } */
  saveToVault: id => (MOCK() ? mock({ vaultDocumentId: 'tenancy' }) : api.post(`${EP.documents.analysis(id)}/save`)),

  /** -> { url } a shareable read-only link */
  share: id => (MOCK() ? mock({ url: `${window.location.origin}/documents/analysis/${id}` }) : api.post(EP.documents.analysisShare(id))),
}
