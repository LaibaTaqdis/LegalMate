// Runtime configuration for the API layer. Values come from Vite env vars (see .env.example).
const env = import.meta.env

export const API_BASE_URL = (env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

// VITE_USE_MOCKS=false  -> every service talks to the backend.
// otherwise             -> mocks, except the services listed in VITE_REAL_SERVICES (comma separated),
//                          e.g. VITE_REAL_SERVICES=auth,chat,profile while the other modules are still being built.
const ALL_REAL = String(env.VITE_USE_MOCKS ?? 'true') === 'false'
const REAL = new Set(String(env.VITE_REAL_SERVICES || '').split(',').map(s => s.trim()).filter(Boolean))

/** True while the whole app runs on mocks or in the mixed mode: pages of unfinished modules keep their demo behaviour. */
export const USE_MOCKS = !ALL_REAL

/** Per-service switch: `isMock('chat')` is false when the chat service should call the backend. */
export const isMock = service => !ALL_REAL && !REAL.has(service)

export const MOCK_DELAY = Number(env.VITE_MOCK_DELAY ?? 300)
