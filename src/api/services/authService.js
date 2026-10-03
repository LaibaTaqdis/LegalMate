import { api } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock, uid } from '../mock'
import { MOCK_TOKENS, MOCK_USER, MOCK_USER_ADMIN, MOCK_USER_LAWYER } from '../mocks/user'

// Mock mode only: which demo account "role" is signed in, so /auth/me survives a page refresh.
const ROLE_KEY = 'legalmate.mockRole'
const USERS_BY_ROLE = { client: MOCK_USER, lawyer: MOCK_USER_LAWYER, admin: MOCK_USER_ADMIN }
const rememberRole = role => { try { localStorage.setItem(ROLE_KEY, role) } catch { /* storage unavailable */ } }
const readRole = () => { try { return localStorage.getItem(ROLE_KEY) } catch { return null } }
const forgetRole = () => { try { localStorage.removeItem(ROLE_KEY) } catch { /* ignore */ } }

export const authService = {
  /** { identifier: email or phone, password, remember, role: 'client'|'lawyer'|'admin' } -> { user, accessToken, refreshToken } */
  login: ({ identifier, password, remember, role = 'client' }) => {
    if (USE_MOCKS) { rememberRole(role); return mock({ user: USERS_BY_ROLE[role] || MOCK_USER, ...MOCK_TOKENS }) }
    return api.post(EP.auth.login, { identifier, password, remember, role }, { auth: false })
  },

  /** Full-page redirect to the backend's Google OAuth flow. */
  googleLogin: () => {
    if (USE_MOCKS) { rememberRole('client'); return mock({ user: MOCK_USER, ...MOCK_TOKENS }) }
    window.location.href = `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}${EP.auth.google}?redirect=${encodeURIComponent(window.location.origin + '/dashboard')}`
    return new Promise(() => {})
  },

  /** Step 1 of signup (client accounts only) -> { verificationId, channel, maskedDestination } */
  register: payload =>
    USE_MOCKS
      ? mock({ verificationId: uid('ver'), channel: 'sms', maskedDestination: `+92 ${payload.phone || '300 1234567'}` })
      : api.post(EP.auth.register, payload, { auth: false }),

  /** Step 2 of signup -> { user, accessToken, refreshToken } */
  verifyOtp: ({ verificationId, code }) => {
    if (USE_MOCKS) { rememberRole('client'); return mock({ user: MOCK_USER, ...MOCK_TOKENS }) }
    return api.post(EP.auth.verifyOtp, { verificationId, code }, { auth: false })
  },

  resendOtp: verificationId =>
    USE_MOCKS ? mock({ ok: true }) : api.post(EP.auth.resendOtp, { verificationId }, { auth: false }),

  forgotPassword: identifier =>
    USE_MOCKS ? mock({ ok: true }) : api.post(EP.auth.forgotPassword, { identifier }, { auth: false }),

  me: () => (USE_MOCKS ? mock(USERS_BY_ROLE[readRole()] || MOCK_USER, 150) : api.get(EP.auth.me)),

  logout: refreshToken => {
    if (USE_MOCKS) { forgetRole(); return mock(null, 100) }
    return api.post(EP.auth.logout, { refreshToken })
  },
}
