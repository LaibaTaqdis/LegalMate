import { api, stream, upload } from '../client'
import { isMock } from '../config'
import { EP } from '../endpoints'
import { mock, sleep, uid } from '../mock'
import { CONVERSATIONS, genericAnswer, initialMessages } from '../mocks/chat'

const MOCK = () => isMock('chat')
const now = () => new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
const withIds = (msgs, convId) => msgs.map((m, i) => ({ id: m.id || `${convId}_m${i}`, ...m }))

export const chatService = {
  /** -> { items: Conversation[] } (most recent first) */
  listConversations: signal =>
    MOCK() ? mock({ items: CONVERSATIONS }) : api.get(EP.chat.conversations, { signal }),

  /** -> { conversation, messages: Message[] } */
  getConversation: (id, signal) => {
    if (!MOCK()) return api.get(EP.chat.conversation(id), { signal })
    const conversation = CONVERSATIONS.find(c => c.id === id)
    return mock({ conversation, messages: withIds(initialMessages()[id] || [], id) })
  },

  /**
   * Starts a conversation from the first question. -> { conversation }
   * The backend should derive `title`/`tag` from the question (or from `topic`).
   */
  createConversation: ({ firstMessage, topic }) => {
    if (!MOCK()) return api.post(EP.chat.conversations, { firstMessage, topic })
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
   * Sends a user message and resolves with the assistant's message (kind: answer | clarify | info).
   * Real backend: POST .../messages returns text/event-stream:
   *   `status` {state:'thinking'|'loading_library'|'reading_image'|'searching_sources'|'writing_answer'} ('reading_image' only when a photo is attached: it is read now, not at upload) ... `conversation` (renamed/updated) -> `answer` (the Message) | `error`.
   * `onStatus({state})` drives the progress label; `onConversation(conversation)` receives the auto-generated title and tag.
   */
  sendMessage: async (conversationId, { content, attachmentIds = [], language }, { onStatus, onConversation, signal } = {}) => {
    if (MOCK()) {
      onStatus?.({ state: 'thinking' })
      await sleep(1400)
      return { id: uid('msg'), ...genericAnswer(content, now()) }
    }
    let answer = null
    await stream(EP.chat.messages(conversationId), { content, attachmentIds, language }, {
      signal,
      onEvent: ({ event, data }) => {
        if (event === 'answer') answer = data
        else if (event === 'conversation') onConversation?.(data)
        else if (event === 'error') throw new Error(data?.message || 'LegalMate could not answer right now.')
        else if (event === 'status') onStatus?.(data)
      },
    })
    if (!answer) throw new Error('No answer received.')
    return answer
  },

  deleteConversation: id => (MOCK() ? mock(null, 150) : api.delete(EP.chat.conversation(id))),
  pinConversation: (id, pinned = true) => (MOCK() ? mock(null, 150) : api.put(EP.chat.pin(id), { pinned })),
  renameConversation: (id, title) => (MOCK() ? mock(null, 150) : api.patch(EP.chat.conversation(id), { title })),

  /** vote: 'up' | 'down' */
  feedback: (messageId, vote, comment) => (MOCK() ? mock(null, 150) : api.post(EP.chat.feedback(messageId), { vote, comment })),
  saveToVault: messageId => (MOCK() ? mock({ documentId: uid('doc') }) : api.post(EP.chat.saveToVault(messageId))),
  reportSource: ({ messageId, sourceId, reason }) => (MOCK() ? mock(null, 150) : api.post(EP.chat.reportSource, { messageId, sourceId, reason })),

  /** Uploads a chat attachment through the documents endpoint -> { id, name } */
  uploadAttachment: (file, onProgress) =>
    isMock('documents') ? mock({ id: uid('doc'), name: file.name }, 200) : upload(EP.documents.upload, file, { fields: { purpose: 'chat' }, onProgress }),
}
