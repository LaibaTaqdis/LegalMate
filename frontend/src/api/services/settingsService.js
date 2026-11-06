import { api, upload } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock } from '../mock'
import { MOCK_SETTINGS, MOCK_USER } from '../mocks/user'

// Deep-merge helper for PATCH /users/me/preferences in mock mode.
const merge = (a, b) => Object.fromEntries(Object.entries({ ...a, ...b }).map(([k, v]) => [k, v && typeof v === 'object' && !Array.isArray(v) && a?.[k] ? { ...a[k], ...v } : v]))

export const settingsService = {
  /* ---------- Profile ---------- */
  /** -> User */
  getProfile: signal => (USE_MOCKS ? mock(MOCK_USER) : api.get(EP.settings.profile, { signal })),
  /** patch: { name, email, phone, city, address } -> User */
  updateProfile: patch => {
    if (!USE_MOCKS) return api.patch(EP.settings.profile, patch)
    Object.assign(MOCK_USER, patch)
    return mock(MOCK_USER, 400)
  },
  /** -> { avatarUrl } */
  uploadAvatar: file => (USE_MOCKS ? mock({ avatarUrl: URL.createObjectURL(file) }, 500) : upload(EP.settings.avatar, file)),

  /* ---------- Security ---------- */
  changePassword: ({ currentPassword, newPassword }) => (USE_MOCKS ? mock(null, 500) : api.post(EP.settings.password, { currentPassword, newPassword })),
  /** -> { twoFactorEnabled, loginAlerts } */
  getSecurity: signal => (USE_MOCKS ? mock(MOCK_SETTINGS.security) : api.get(EP.settings.security, { signal })),
  updateSecurity: patch => {
    if (!USE_MOCKS) return api.patch(EP.settings.security, patch)
    Object.assign(MOCK_SETTINGS.security, patch)
    return mock(MOCK_SETTINGS.security, 200)
  },
  /** -> { items: Session[] } */
  listSessions: signal => (USE_MOCKS ? mock({ items: MOCK_SETTINGS.sessions }) : api.get(EP.settings.sessions, { signal })),
  revokeSession: id => {
    if (!USE_MOCKS) return api.delete(EP.settings.session(id))
    MOCK_SETTINGS.sessions = MOCK_SETTINGS.sessions.filter(s => s.id !== id)
    return mock(null, 200)
  },

  /* ---------- Preferences (notifications, region, privacy, appearance, offline) ---------- */
  getPreferences: signal => (USE_MOCKS ? mock(MOCK_SETTINGS.preferences) : api.get(EP.settings.preferences, { signal })),
  /** Partial update, e.g. { notifications: { sms: true } } -> Preferences */
  updatePreferences: patch => {
    if (!USE_MOCKS) return api.patch(EP.settings.preferences, patch)
    MOCK_SETTINGS.preferences = merge(MOCK_SETTINGS.preferences, patch)
    return mock(MOCK_SETTINGS.preferences, 150)
  },

  /* ---------- Data ---------- */
  /** -> { storage: { usedBytes, quotaBytes } } */
  getStorage: signal => (USE_MOCKS ? mock({ storage: MOCK_SETTINGS.storage }) : api.get(EP.vault.stats, { signal })),
  /** Queues a data export; the backend emails a download link. -> { requestId } */
  requestExport: () => (USE_MOCKS ? mock({ requestId: 'exp_1' }, 400) : api.post(EP.settings.export)),
  /** Starts account deletion; the backend emails a confirmation link. */
  deleteAccount: () => (USE_MOCKS ? mock(null, 400) : api.delete(EP.settings.account)),

  /* ---------- Connected apps ---------- */
  /** -> { items: [{ provider, connected, account }] } */
  listIntegrations: signal => (USE_MOCKS ? mock({ items: MOCK_SETTINGS.integrations }) : api.get(EP.settings.integrations, { signal })),
  /** Google returns { redirectUrl } for OAuth; others connect directly. */
  connectIntegration: provider => (USE_MOCKS ? mock({ provider, connected: true, account: 'arfah.rizwan@gmail.com' }, 400) : api.post(EP.settings.integration(provider))),
  disconnectIntegration: provider => (USE_MOCKS ? mock(null, 200) : api.delete(EP.settings.integration(provider))),
}
