import { api, download, upload } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock, mockDownload, uid } from '../mock'
import { MOCK_BRIEF, MOCK_DRAFT } from '../mocks/briefs'

export const caseBriefService = {
  /**
   * The user's current draft (created on first call).
   * `fromMessage` / `fromAnalysis` ask the backend to pre-fill it from a chat answer or document analysis.
   */
  getDraft: ({ fromMessage, fromAnalysis } = {}, signal) =>
    USE_MOCKS ? mock(MOCK_DRAFT) : api.get(EP.briefs.draft, { query: { fromMessage, fromAnalysis }, signal }),

  /** Autosave. -> { savedAt } */
  saveDraft: draft => (USE_MOCKS ? mock({ savedAt: new Date().toISOString() }, 200) : api.put(EP.briefs.draft, draft)),

  /** -> { id, name, sizeBytes, fileType } */
  uploadAttachment: (file, onProgress) =>
    USE_MOCKS
      ? mock({ id: uid('att'), name: file.name, sizeBytes: file.size, fileType: file.name.split('.').pop().toLowerCase() }, 500)
      : upload(EP.briefs.attachments, file, { onProgress }),

  removeAttachment: id => (USE_MOCKS ? mock(null, 100) : api.delete(`${EP.briefs.attachments}/${id}`)),

  /** Generates a brief from the draft. -> { id, status } (poll GET /case-briefs/:id while 'generating') */
  generate: payload => (USE_MOCKS ? mock({ id: MOCK_BRIEF.id, status: 'completed' }, 1600) : api.post(EP.briefs.list, payload)),

  /** -> CaseBrief */
  get: (id, signal) => (USE_MOCKS ? mock(MOCK_BRIEF) : api.get(EP.briefs.brief(id), { signal })),

  /** -> CaseBrief (re-generated content) */
  regenerate: id => (USE_MOCKS ? mock(MOCK_BRIEF, 1400) : api.post(EP.briefs.regenerate(id))),

  /** Stores the generated brief in the Legal Vault. -> { vaultDocumentId } */
  saveToVault: id => (USE_MOCKS ? mock({ vaultDocumentId: 'brief' }) : api.post(`${EP.briefs.brief(id)}/save`)),

  /** format: 'pdf' | 'docx' */
  export: (id, format, filename) => (USE_MOCKS ? mockDownload() : download(EP.briefs.export(id), filename, { query: { format } })),

  /** recipients: [{ contact, permission: 'View'|'Comment'|'Edit' }] -> { invites } */
  invite: (id, { recipients, message }) => (USE_MOCKS ? mock({ invites: recipients.map(r => ({ id: uid('inv'), ...r })) }, 900) : api.post(EP.briefs.invites(id), { recipients, message })),

  /** settings: { enabled, expiresIn, requirePassword } -> { enabled, url, expiresIn, requirePassword } */
  updateShareLink: (id, settings) => (USE_MOCKS ? mock({ ...MOCK_BRIEF.sharing.link, ...settings }, 200) : api.put(EP.briefs.shareLink(id), settings)),
}
