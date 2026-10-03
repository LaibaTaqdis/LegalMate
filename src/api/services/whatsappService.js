import { api } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock } from '../mock'

const MOCK_COMMANDS = [
  { command: '/Ask', description: 'What is the notice period for tenancy?' },
  { command: '/status', description: 'Check my document status' },
  { command: '/legal-aid', description: 'Find legal aid in Islamabad' },
  { command: '/support', description: 'Talk to a support agent' },
]

function mockReply(text) {
  const t = text.trim().toLowerCase()
  if (t === '2' || t.startsWith('/status')) return '📄 Tenancy Agreement.pdf - analysis complete. Overall risk: Medium. 3 items need clarification.'
  if (t === '3' || t.startsWith('/legal-aid')) return '⚖️ Nearest verified help: Adv. Usman Malik (Islamabad, 2.3 km) and Legal Aid Society of Pakistan (free). Reply /book to request help.'
  if (t === '4' || t.startsWith('/support')) return '🙋 Connecting you to a support agent. Average wait time is under 5 minutes.'
  return 'Thanks for your question! Here’s a quick answer based on Pakistani law. For a detailed, source-backed explanation, open this chat in your LegalMate dashboard.'
}

export const whatsappService = {
  /** -> { connected, phone, connectedAt } */
  getStatus: signal => (USE_MOCKS ? mock({ connected: true, phone: '300 1234567', connectedAt: '2026-09-20T10:00:00' }) : api.get(EP.whatsapp.status, { signal })),

  /**
   * Links a number. -> { status: 'pending_verification' | 'connected', phone }
   * The backend sends a WhatsApp opt-in message; status becomes 'connected' once the user replies.
   */
  connect: ({ phone, consent }) => (USE_MOCKS ? mock({ status: 'connected', phone }, 1200) : api.post(EP.whatsapp.connect, { phone: `+92${phone.replace(/\s/g, '')}`, consent })),

  disconnect: () => (USE_MOCKS ? mock(null, 300) : api.delete(EP.whatsapp.disconnect)),

  /** Linking QR code. -> { qrImageUrl, expiresAt, webUrl } */
  getQr: signal => (USE_MOCKS
    ? mock({ qrImageUrl: '/assets/img/whatsapp-qr.png', expiresAt: new Date(Date.now() + 175000).toISOString(), webUrl: 'https://web.whatsapp.com' }, 200)
    : api.get(EP.whatsapp.qr, { signal })),

  /** -> { items: [{ command, description }] } */
  listCommands: signal => (USE_MOCKS ? mock({ items: MOCK_COMMANDS }, 0) : api.get(EP.whatsapp.commands, { signal })),

  /** Sends a real test message to the linked number. -> { sent: true } */
  sendTestMessage: () => (USE_MOCKS ? mock({ sent: true }, 400) : api.post(EP.whatsapp.testMessage)),

  /** Bot reply for the phone preview on this page. -> { reply } (plain text) */
  preview: text => (USE_MOCKS ? mock({ reply: mockReply(text) }, 1200) : api.post(`${EP.whatsapp.status}/preview`, { text })),
}
