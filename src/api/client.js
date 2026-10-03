// Thin fetch wrapper used by every service. Handles auth headers, token refresh,
// JSON/FormData bodies, query strings, errors, uploads with progress, SSE streams and downloads.
import { API_BASE_URL } from './config'
import { tokenStore } from './tokenStore'

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'UNKNOWN', details = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

let language = 'en'
/** Called by the UI when the user switches language, so the backend can localise answers. */
export const setApiLanguage = lang => { language = lang }

function buildUrl(path, query) {
  const url = new URL(API_BASE_URL + path, window.location.origin)
  Object.entries(query || {}).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return
    if (Array.isArray(v)) v.forEach(x => url.searchParams.append(k, x))
    else url.searchParams.set(k, v)
  })
  return url.toString()
}

function headers(auth, extra, isJson) {
  const h = { Accept: 'application/json', 'Accept-Language': language, ...extra }
  if (isJson) h['Content-Type'] = 'application/json'
  if (auth && tokenStore.accessToken) h.Authorization = `Bearer ${tokenStore.accessToken}`
  return h
}

async function toError(res) {
  let body = null
  try { body = await res.json() } catch { /* not JSON */ }
  const e = body?.error || {}
  return new ApiError(e.message || res.statusText || 'Request failed', { status: res.status, code: e.code, details: e.details })
}

let refreshing = null
async function refreshTokens() {
  if (!tokenStore.refreshToken) return false
  refreshing ??= fetch(buildUrl('/auth/refresh'), {
    method: 'POST',
    headers: headers(false, {}, true),
    body: JSON.stringify({ refreshToken: tokenStore.refreshToken }),
  })
    .then(async r => {
      if (!r.ok) return false
      const t = await r.json()
      tokenStore.update({ accessToken: t.accessToken, refreshToken: t.refreshToken || tokenStore.refreshToken })
      return true
    })
    .catch(() => false)
    .finally(() => { refreshing = null })
  return refreshing
}

function expireSession() {
  tokenStore.clear()
  window.dispatchEvent(new Event('auth:expired'))
}

export async function request(path, { method = 'GET', body, query, headers: extra, signal, auth = true, raw = false, retry = true } = {}) {
  const isForm = body instanceof FormData
  const res = await fetch(buildUrl(path, query), {
    method,
    headers: headers(auth, extra, body !== undefined && !isForm),
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    signal,
  })

  if (res.status === 401 && auth && retry) {
    if (await refreshTokens()) return request(path, { method, body, query, headers: extra, signal, auth, raw, retry: false })
    expireSession()
  }
  if (!res.ok) throw await toError(res)
  if (raw) return res
  if (res.status === 204) return null
  const type = res.headers.get('content-type') || ''
  return type.includes('application/json') ? res.json() : res.text()
}

export const api = {
  get: (path, opts) => request(path, { ...opts, method: 'GET' }),
  post: (path, body, opts) => request(path, { ...opts, method: 'POST', body }),
  put: (path, body, opts) => request(path, { ...opts, method: 'PUT', body }),
  patch: (path, body, opts) => request(path, { ...opts, method: 'PATCH', body }),
  delete: (path, opts) => request(path, { ...opts, method: 'DELETE' }),
}

/**
 * Multipart upload with progress (fetch cannot report upload progress, so this uses XHR).
 * `fields` are extra form fields; the file is sent as `file`.
 */
export function upload(path, file, { fields = {}, onProgress, signal } = {}) {
  return new Promise((resolve, reject) => {
    const form = new FormData()
    form.append('file', file)
    Object.entries(fields).forEach(([k, v]) => v !== undefined && form.append(k, typeof v === 'object' ? JSON.stringify(v) : v))

    const xhr = new XMLHttpRequest()
    xhr.open('POST', buildUrl(path))
    Object.entries(headers(true, {}, false)).forEach(([k, v]) => xhr.setRequestHeader(k, v))
    xhr.upload.onprogress = e => e.lengthComputable && onProgress?.(Math.round((e.loaded / e.total) * 100))
    xhr.onload = () => {
      let data = null
      try { data = JSON.parse(xhr.responseText) } catch { /* empty */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data)
      else {
        if (xhr.status === 401) expireSession()
        reject(new ApiError(data?.error?.message || 'Upload failed', { status: xhr.status, code: data?.error?.code }))
      }
    }
    xhr.onerror = () => reject(new ApiError('Network error during upload'))
    signal?.addEventListener('abort', () => { xhr.abort(); reject(new DOMException('Aborted', 'AbortError')) })
    xhr.send(form)
  })
}

/**
 * POST that returns Server-Sent Events. Calls `onEvent({ event, data })` for each event,
 * where `data` is parsed JSON when possible. Resolves when the stream ends.
 */
export async function stream(path, body, { onEvent, signal } = {}) {
  const res = await request(path, { method: 'POST', body, signal, raw: true, headers: { Accept: 'text/event-stream' } })
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buffer.indexOf('\n\n')) >= 0) {
      const chunk = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      let event = 'message'
      const data = []
      chunk.split('\n').forEach(line => {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) data.push(line.slice(5).trim())
      })
      const text = data.join('\n')
      let parsed = text
      try { parsed = JSON.parse(text) } catch { /* plain text */ }
      onEvent?.({ event, data: parsed })
    }
  }
}

/** Downloads a file from an authenticated endpoint and saves it with the given name. */
export async function download(path, filename, { query } = {}) {
  const res = await request(path, { query, raw: true, headers: { Accept: '*/*' } })
  const blob = await res.blob()
  const disposition = res.headers.get('content-disposition') || ''
  const name = /filename="?([^";]+)"?/.exec(disposition)?.[1] || filename
  const url = URL.createObjectURL(blob)
  const a = Object.assign(document.createElement('a'), { href: url, download: name })
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
