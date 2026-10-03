import { api } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock } from '../mock'
import { MOCK_NOTIFICATIONS } from '../mocks/user'

export const notificationService = {
  /** -> { unreadCount, items: Notification[] } */
  list: signal => (USE_MOCKS ? mock(MOCK_NOTIFICATIONS) : api.get(EP.notifications.list, { query: { limit: 10 }, signal })),
  markAllRead: () => (USE_MOCKS ? mock(null, 100) : api.post(EP.notifications.readAll)),
  markRead: id => (USE_MOCKS ? mock(null, 100) : api.post(EP.notifications.read(id))),
}
