// Helpers for the mock implementations used while VITE_USE_MOCKS=true.
import { MOCK_DELAY } from './config'

export const sleep = ms => new Promise(r => setTimeout(r, ms))

/** Resolves with a deep copy of `data` after the configured mock latency. */
export async function mock(data, ms = MOCK_DELAY) {
  await sleep(ms)
  return data === undefined ? null : structuredClone(data)
}

/** Simulates an upload by ticking progress from 0 to 100. */
export async function mockUpload(onProgress, ms = 1600) {
  const steps = 10
  for (let i = 1; i <= steps; i++) {
    await sleep(ms / steps)
    onProgress?.(Math.round((i / steps) * 100))
  }
}

/** Pretends to download by showing nothing but resolving; the UI shows a toast. */
export const mockDownload = () => sleep(MOCK_DELAY)

export const uid = (prefix = 'id') => `${prefix}_${Math.random().toString(36).slice(2, 10)}`
