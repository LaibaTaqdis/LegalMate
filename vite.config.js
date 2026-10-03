import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    // Optional: with VITE_API_BASE_URL=/api/v1 and VITE_PROXY_TARGET=http://localhost:8000,
    // the dev server forwards /api/* to the backend so no CORS setup is needed locally.
    server: env.VITE_PROXY_TARGET
      ? { proxy: { '/api': { target: env.VITE_PROXY_TARGET, changeOrigin: true } } }
      : undefined,
  }
})
