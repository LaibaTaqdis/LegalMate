// Formatting helpers so the backend can send raw values (ISO dates, bytes, numbers)
// while the UI keeps the exact look of the designs.

const toDate = v => (v instanceof Date ? v : new Date(v))

/** "10:24 AM" */
export const formatTime = iso => (iso ? toDate(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : '')

/** "22 Sep 2026" */
export const formatDate = iso => (iso ? toDate(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '')

/** "22 Sep 2026, 10:24 AM" */
export const formatDateTime = iso => (iso ? `${formatDate(iso)}, ${formatTime(iso)}` : '')

/** "5h ago", "Yesterday", "20 Sep" */
export function timeAgo(iso) {
  if (!iso) return ''
  const diff = (Date.now() - toDate(iso).getTime()) / 1000
  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 172800) return 'Yesterday'
  return toDate(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

/** 2516582 -> "2.4 MB" */
export function formatBytes(bytes) {
  if (bytes == null) return ''
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

/** 24500 -> "PKR 24,500" */
export const pkr = n => `PKR ${Math.round(n).toLocaleString('en-US')}`

/** Initials from a full name: "Arfah Rizwan" -> "AR" */
export const initials = name => (name || '').split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('')
