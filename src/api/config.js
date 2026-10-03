// Runtime configuration for the API layer. Values come from Vite env vars (see .env.example).
const env = import.meta.env

export const API_BASE_URL = (env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

// Mocks stay on until a backend is configured explicitly.
export const USE_MOCKS = String(env.VITE_USE_MOCKS ?? 'true') !== 'false'

export const MOCK_DELAY = Number(env.VITE_MOCK_DELAY ?? 300)
