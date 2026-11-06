import { api } from '../client'
import { isMock } from '../config'
import { EP } from '../endpoints'
import { mock } from '../mock'
import { MOCK_TOKENS, MOCK_USER, MOCK_USER_ADMIN, MOCK_USER_LAWYER } from '../mocks/user'

const MOCK = () => isMock('auth')

// Mock mode only: which demo account "role" is signed in, so /auth/me survives a page refresh.
const ROLE_KEY = 'legalmate.mockRole'
const USERS_BY_ROLE = { client: MOCK_USER, lawyer: MOCK_USER_LAWYER, admin: MOCK_USER_ADMIN }
const rememberRole = role => { try { localStorage.setItem(ROLE_KEY, role) } catch { /* storage unavailable */ } }
const readRole = () => { try { return localStorage.getItem(ROLE_KEY) } catch { return null } }
const forgetRole = () => { try { localStorage.removeItem(ROLE_KEY) } catch { /* ignore */ } }

export const authService = {
  /** { identifier: email or phone, password, remember, role: 'client'|'lawyer'|'admin' } -> { user, accessToken, refreshToken } */
  login: ({ identifier, password, remember, role = 'client' }) => {
    if (MOCK()) { rememberRole(role); return mock({ user: USERS_BY_ROLE[role] || MOCK_USER, ...MOCK_TOKENS }) }
    return api.post(EP.auth.login, { identifier, password, remember, role }, { auth: false })
  },

  /** Full-page redirect to the backend's Google OAuth flow (not built yet: the sign-in page hides the button when the backend is real). */
  googleLogin: () => {
    if (MOCK()) { rememberRole('client'); return mock({ user: MOCK_USER, ...MOCK_TOKENS }) }
    window.location.href = `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}${EP.auth.google}?redirect=${encodeURIComponent(window.location.origin + '/dashboard')}`
    return new Promise(() => {})
  },

  /** Creates the account and signs in (no OTP step) -> { user, accessToken, refreshToken } */
  register: payload => {
    if (MOCK()) { rememberRole('client'); return mock({ user: { ...MOCK_USER, name: payload.fullName || MOCK_USER.name }, ...MOCK_TOKENS }) }
    return api.post(EP.auth.register, payload, { auth: false })
  },

  forgotPassword: identifier =>
    MOCK() ? mock({ ok: true }) : api.post(EP.auth.forgotPassword, { identifier }, { auth: false }),

  me: () => (MOCK() ? mock(USERS_BY_ROLE[readRole()] || MOCK_USER, 150) : api.get(EP.auth.me)),

  logout: refreshToken => {
    if (MOCK()) { forgetRole(); return mock(null, 100) }
    return api.post(EP.auth.logout, { refreshToken })
  },
}
