import { api, stream, upload } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock, sleep, uid } from '../mock'
import { CONVERSATIONS, genericAnswer, initialMessages } from '../mocks/chat'

const now = () => new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
const withIds = (msgs, convId) => msgs.map((m, i) => ({ id: m.id || `${convId}_m${i}`, ...m }))

export const chatService = {
  /** -> { items: Conversation[] } (most recent first) */
  listConversations: signal =>
    USE_MOCKS ? mock({ items: CONVERSATIONS }) : api.get(EP.chat.conversations, { signal }),

  /** -> { conversation, messages: Message[] } */
  getConversation: (id, signal) => {
    if (!USE_MOCKS) return api.get(EP.chat.conversation(id), { signal })
    const conversation = CONVERSATIONS.find(c => c.id === id)
    return mock({ conversation, messages: withIds(initialMessages()[id] || [], id) })
  },

  /**
   * Starts a conversation from the first question. -> { conversation }
   * The backend should derive `title`/`tag` from the question (or from `topic`).
   */
  createConversation: ({ firstMessage, topic }) => {
    if (!USE_MOCKS) return api.post(EP.chat.conversations, { firstMessage, topic })
    const isTenancy = /rent|landlord|tenan/i.test(firstMessage)
    const title = isTenancy ? 'Tenant rights in Pakistan' : firstMessage.length > 34 ? `${firstMessage.slice(0, 32).trim()}…` : firstMessage
    return mock({
      conversation: {
        id: isTenancy ? 'tenant-rights' : uid('conv'), title, tag: isTenancy ? 'Property Law' : 'General',
        preview: `${firstMessage.slice(0, 32)}...`, icon: 'chat', group: 'Today', time: now(),
      },
    }, 150)
  },

  /**
   * Sends a user message and resolves with the assistant's answer.
   * Real backend: POST .../messages returning text/event-stream with events
   *   `status` {state:'thinking'} -> optional `delta` -> `answer` (final Message) | `error`.
   * `onStatus` is called with each status/delta so the UI can show progress.
   */
  sendMessage: async (conversationId, { content, attachmentIds = [], language }, { onStatus, signal } = {}) => {
    if (USE_MOCKS) {
      onStatus?.({ state: 'thinking' })
      await sleep(1400)
      return { id: uid('msg'), ...genericAnswer(content, now()) }
    }
    let answer = null
    await stream(EP.chat.messages(conversationId), { content, attachmentIds, language }, {
      signal,
      onEvent: ({ event, data }) => {
        if (event === 'answer') answer = data
        else if (event === 'error') throw new Error(data?.message || 'LegalMate could not answer right now.')
        else onStatus?.(data)
      },
    })
    if (!answer) throw new Error('No answer received.')
    return answer
  },

  deleteConversation: id => (USE_MOCKS ? mock(null, 150) : api.delete(EP.chat.conversation(id))),
  pinConversation: (id, pinned = true) => (USE_MOCKS ? mock(null, 150) : api.put(EP.chat.pin(id), { pinned })),
  renameConversation: (id, title) => (USE_MOCKS ? mock(null, 150) : api.patch(EP.chat.conversation(id), { title })),

  /** vote: 'up' | 'down' */
  feedback: (messageId, vote, comment) => (USE_MOCKS ? mock(null, 150) : api.post(EP.chat.feedback(messageId), { vote, comment })),
  saveToVault: messageId => (USE_MOCKS ? mock({ documentId: uid('doc') }) : api.post(EP.chat.saveToVault(messageId))),
  reportSource: ({ messageId, sourceId, reason }) => (USE_MOCKS ? mock(null, 150) : api.post(EP.chat.reportSource, { messageId, sourceId, reason })),

  /** Uploads a chat attachment through the documents endpoint -> { id, name } */
  uploadAttachment: (file, onProgress) =>
    USE_MOCKS ? mock({ id: uid('doc'), name: file.name }, 200) : upload(EP.documents.upload, file, { fields: { purpose: 'chat' }, onProgress }),
}
