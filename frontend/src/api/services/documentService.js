import { api, download, upload } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock, mockDownload, sleep, uid } from '../mock'
import { MOCK_ANALYSIS } from '../mocks/documents'

export const ACCEPTED_TYPES = ['pdf', 'docx', 'jpg', 'png']
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024

export const documentService = {
  /**
   * Uploads a file for analysis / storage. -> { id, name, sizeBytes, fileType, pages }
   * `startAt` only affects the mock progress animation.
   */
  upload: async (file, { onProgress, signal, saveToVault = false, startAt = 0 } = {}) => {
    if (!USE_MOCKS) return upload(EP.documents.upload, file, { fields: { purpose: 'analysis', saveToVault }, onProgress, signal })
    for (let p = startAt; p < 100; p = Math.min(100, p + 7)) {
      if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
      onProgress?.(p)
      await sleep(350)
    }
    onProgress?.(100)
    return { id: uid('doc'), name: file.name, sizeBytes: file.size, fileType: file.name.split('.').pop().toLowerCase() }
  },

  /** Discards an uploaded (not yet analysed) document. */
  remove: id => (USE_MOCKS ? mock(null, 100) : api.delete(`${EP.documents.upload}/${id}`)),

  /**
   * Starts an analysis job. -> { id, status }
   * options: { documentIds, language: 'auto'|'en'|'ur', depth: 'quick'|'detailed', saveToVault }
   */
  startAnalysis: options => (USE_MOCKS ? mock({ id: 'tenancy', status: 'processing' }) : api.post(EP.documents.analyses, options)),

  /** -> Analysis (poll while status is 'queued' or 'processing') */
  getAnalysis: (id, signal) => (USE_MOCKS ? mock(MOCK_ANALYSIS) : api.get(EP.documents.analysis(id), { signal })),

  downloadReport: (id, name = 'Analysis_Report.pdf') => (USE_MOCKS ? mockDownload() : download(EP.documents.analysisReport(id), name)),

  /** Saves the analysed document + report into the Legal Vault. -> { vaultDocumentId } */
  saveToVault: id => (USE_MOCKS ? mock({ vaultDocumentId: 'tenancy' }) : api.post(`${EP.documents.analysis(id)}/save`)),

  /** -> { url } a shareable read-only link */
  share: id => (USE_MOCKS ? mock({ url: `${window.location.origin}/documents/analysis/${id}` }) : api.post(EP.documents.analysisShare(id))),
}
