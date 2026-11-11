import { api, download } from '../client'
import { isMock } from '../config'
import { EP } from '../endpoints'
import { mock, mockDownload } from '../mock'

const MOCK = () => isMock('guidance')

// Demo mode (no backend): one guide, one letter and a canned contract check, so the pages open instead of failing.
const DEMO_GUIDE = {
  id: 'g_landlord', title: 'My landlord wants me out', intro: 'A few quick questions, then a plan for what to do first.', situation: 'My landlord wants me to leave the property.',
  questions: [{ id: 'q1', text: 'What did the landlord do?', options: ['Told me to leave verbally', 'Sent a written notice', 'Filed a case'] }],
  tools: [{ type: 'letter', id: 'tenant_reply', name: 'Reply to a landlord\'s eviction notice', label: 'Draft a reply to the landlord', link: '/letters/tenant_reply' }],
  note: 'Demo guide. With the backend connected the plan comes from the law library with its sources.',
}
const DEMO_LETTER = {
  id: 'tenant_reply', title: 'Reply to a landlord\'s eviction notice', summary: 'Say in writing that you have not agreed to leave.', who: 'Tenant',
  note: 'Demo letter: connect the backend to build the real text.',
  fields: [{ key: 'senderName', label: 'Your full name', type: 'text', required: true }, { key: 'recipientName', label: 'Landlord\'s name', type: 'text', required: true }],
}

export const guidanceService = {
  /** -> { id, title, intro, situation, questions: [{ id, text, options }], tools: [{ type: 'calculator'|'letter'|'check', name, label, link }], note } */
  guide: (id, signal) => (MOCK() ? mock(DEMO_GUIDE, 150) : api.get(EP.guidance.guide(id), { signal })),

  /** -> { id, title, summary, who, note, fields: [{ key, label, type: text|textarea|date|number|select, required, options, default, help, placeholder }] } */
  letter: (id, signal) => (MOCK() ? mock(DEMO_LETTER, 150) : api.get(EP.guidance.letter(id), { signal })),

  /** Builds the letter on the server from the typed facts. -> { id, title, subject, text, fields } */
  renderLetter: (id, fields) => (MOCK()
    ? mock({ id, title: DEMO_LETTER.title, subject: 'Demo', text: 'Demo mode: connect the backend (add "guidance" to VITE_REAL_SERVICES) to build the real letter.', fields }, 250)
    : api.post(EP.guidance.renderLetter(id), { fields })),

  /** Saves the drafted letter to the Legal Vault (the server builds it again from the facts). -> { id } */
  saveLetter: (letterId, fields) => (MOCK() ? mock({ id: `demo_${Date.now()}` }) : api.post(EP.guidance.saveLetter, { letterId, fields })),

  downloadLetter: (id, fields) => (MOCK() ? mockDownload() : download(EP.guidance.letterPdf(id), 'Draft_Letter.pdf', { method: 'POST', body: { fields } })),
  downloadSavedLetter: itemId => (MOCK() ? mockDownload() : download(EP.guidance.savedLetterPdf(itemId), 'Draft_Letter.pdf')),

  /** -> { types: [{ key, label }], limits } */
  contractCheckOptions: signal => (MOCK() ? mock({ types: [{ key: 'general', label: 'General business agreement' }], limits: 'Demo.' }, 100) : api.get(EP.guidance.contractCheck, { signal })),

  /** Checks an uploaded document. -> { level, score, typeLabel, clauses: [...], flags: [...], summary, limits, document } */
  checkContract: (documentId, contractType) => (MOCK()
    ? mock({ level: 'Medium', score: 4, typeLabel: 'General business agreement', words: 900, document: { id: documentId, name: 'Demo contract.pdf' },
      summary: { expected: 8, foundExpected: 6, missingExpected: 2, flags: 1 }, limits: 'Demo result.',
      clauses: [{ key: 'payment', label: 'Price and payment terms', found: true, expected: true, snippet: '...', why: 'Demo', question: 'Demo?' }],
      flags: [{ key: 'auto_renew', label: 'Renews by itself', severity: 'medium', snippet: '...renews automatically...', why: 'Demo', question: 'Demo?' }] }, 400)
    : api.post(EP.guidance.contractCheck, { documentId, contractType })),
}
