// Persists the auth tokens. "Remember me" keeps them in localStorage, otherwise sessionStorage.
const KEY = 'legalmate.auth'

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || sessionStorage.getItem(KEY) || 'null')
  } catch {
    return null
  }
}

export const tokenStore = {
  get accessToken() { return read()?.accessToken || null },
  get refreshToken() { return read()?.refreshToken || null },

  set({ accessToken, refreshToken }, remember = true) {
    const value = JSON.stringify({ accessToken, refreshToken })
    try {
      ;(remember ? localStorage : sessionStorage).setItem(KEY, value)
      ;(remember ? sessionStorage : localStorage).removeItem(KEY)
    } catch { /* storage unavailable (private mode) - tokens live for this page only */ }
  },

  update(partial) {
    const cur = read()
    if (!cur) return
    const remember = !!localStorage.getItem(KEY)
    this.set({ ...cur, ...partial }, remember)
  },

  clear() {
    try { localStorage.removeItem(KEY); sessionStorage.removeItem(KEY) } catch { /* ignore */ }
  },
}
