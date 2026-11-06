import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { USE_MOCKS } from '../api/config'
import { tokenStore } from '../api/tokenStore'
import { authService } from '../api/services/authService'
import { initials } from '../utils/format'

const AuthContext = createContext(null)

// Fill in display fields the backend may not send.
const normalize = u => u && ({
  ...u,
  initials: u.initials || initials(u.name),
  firstName: u.firstName || (u.name || '').split(' ')[0],
  roleLabel: u.roleLabel || 'Citizen Account',
})

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  // Restore the session on first load. In mock mode a demo user is always signed in.
  useEffect(() => {
    if (!USE_MOCKS && !tokenStore.accessToken) { setReady(true); return }
    authService.me()
      .then(u => setUser(normalize(u)))
      .catch(() => tokenStore.clear())
      .finally(() => setReady(true))
  }, [])

  useEffect(() => {
    const onExpired = () => setUser(null)
    window.addEventListener('auth:expired', onExpired)
    return () => window.removeEventListener('auth:expired', onExpired)
  }, [])

  const startSession = useCallback(({ user: u, accessToken, refreshToken }, remember = true) => {
    tokenStore.set({ accessToken, refreshToken }, remember)
    setUser(normalize(u))
    return u
  }, [])

  const login = useCallback(async creds => startSession(await authService.login(creds), creds.remember), [startSession])
  const loginWithGoogle = useCallback(async () => startSession(await authService.googleLogin()), [startSession])
  const verifyOtp = useCallback(async payload => startSession(await authService.verifyOtp(payload)), [startSession])

  const logout = useCallback(async () => {
    try { await authService.logout(tokenStore.refreshToken) } catch { /* ignore network errors on logout */ }
    tokenStore.clear()
    setUser(null)
  }, [])

  const updateUser = useCallback(patch => setUser(u => normalize({ ...u, ...patch, initials: undefined })), [])

  return (
    <AuthContext.Provider value={{ user, ready, login, loginWithGoogle, verifyOtp, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

/** Each role's own landing page, used for default post-login redirects and role-mismatch bounces. */
export const homeFor = role => (role === 'lawyer' ? '/lawyer' : role === 'admin' ? '/admin' : '/dashboard')

const Boot = () => <div className="boot-screen"><img src="/assets/img/logo-mark-navy.png" alt="Loading LegalMate" /></div>

/** Route guard for a role's signed-in area. Unauthenticated users go to /login?next=...; a signed-in user of the wrong role is bounced to their own home. */
export function RequireRole({ role, children }) {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) return <Boot />
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />
  if (user.role !== role) return <Navigate to={homeFor(user.role)} replace />
  return children
}
