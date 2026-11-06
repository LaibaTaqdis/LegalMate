// Custom brand / file icons that lucide does not provide.

export function GoogleIcon({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 8 3l5.7-5.7C34 6.1 29.3 4 24 4 13 4 4 13 4 24s9 20 20 20 20-9 20-20c0-1.3-.1-2.6-.4-3.9z" />
      <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 8 3l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2A11.9 11.9 0 0 1 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3a12 12 0 0 1-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.6-.4-3.9z" />
    </svg>
  )
}

export function PakFlag({ width = 22, className = '' }) {
  const h = (width * 2) / 3
  return (
    <svg className={className} width={width} height={h} viewBox="0 0 30 20" aria-label="Pakistan flag">
      <rect width="30" height="20" rx="2" fill="#01411C" />
      <rect width="7.5" height="20" fill="#fff" />
      <circle cx="19" cy="10" r="5.6" fill="#fff" />
      <circle cx="20.6" cy="8.7" r="4.8" fill="#01411C" />
      <polygon fill="#fff" points="22.4,5.4 22.9,6.9 24.5,6.9 23.2,7.8 23.7,9.3 22.4,8.4 21.1,9.3 21.6,7.8 20.3,6.9 21.9,6.9" />
    </svg>
  )
}

export function WhatsAppIcon({ size = 20, className = '', filled = false }) {
  if (filled) {
    return (
      <svg className={className} width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <path fill="#25D366" d="M16 2.5C8.6 2.5 2.6 8.5 2.6 15.9c0 2.4.6 4.7 1.8 6.7L2.5 29.5l7.1-1.9a13.4 13.4 0 0 0 6.4 1.6c7.4 0 13.4-6 13.4-13.4S23.4 2.5 16 2.5z" />
        <path fill="#fff" d="M11.6 9.3c.3-.6.6-.6.9-.6h.8c.3 0 .6 0 .9.7l1.2 2.9c.1.3.1.6-.1.9l-.7 1c-.2.2-.3.5 0 .9.7 1.3 1.8 2.5 3.1 3.4.4.3.8.4 1 .1l.9-1.1c.3-.3.6-.4 1-.2l2.8 1.3c.4.2.6.3.6.6 0 1-.5 2.1-1.4 2.7-.9.6-2.2.9-3.8.3-1.9-.7-3.8-1.9-5.4-3.5-1.5-1.5-2.7-3.2-3.3-5-.5-1.5 0-2.8.8-3.7z" />
      </svg>
    )
  }
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 2.6a9.4 9.4 0 0 0-8.1 14.2L2.6 21.4l4.7-1.2A9.4 9.4 0 1 0 12 2.6z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path fill="currentColor" d="M8.8 7.3c.2-.4.4-.4.6-.4h.5c.2 0 .4 0 .6.5l.8 1.9c.1.2.1.4 0 .6l-.5.7c-.1.2-.2.3 0 .6.5.9 1.2 1.7 2.1 2.3.3.2.5.3.7.1l.6-.7c.2-.2.4-.3.6-.2l1.9.9c.3.1.4.2.4.4 0 .7-.3 1.4-.9 1.8-.6.4-1.5.6-2.6.2-1.3-.5-2.6-1.3-3.7-2.4-1-1-1.8-2.2-2.2-3.4-.3-1 0-1.9.5-2.5z" />
    </svg>
  )
}

const FILE_COLORS = { pdf: '#E5322D', docx: '#1F66E0', xlsx: '#1E8E4E', jpg: '#7C4DDB', png: '#7C4DDB' }

export function FileIcon({ type = 'pdf', size = 40, className = '', color: colorProp }) {
  const color = colorProp || FILE_COLORS[type] || '#64748b'
  const w = size * 0.8
  return (
    <svg className={className} width={w} height={size} viewBox="0 0 32 40" aria-label={`${type.toUpperCase()} file`}>
      <path d="M4 0h17.5L32 10.5V36a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4V4a4 4 0 0 1 4-4z" fill={color} />
      <path d="M21.5 0v7.5a3 3 0 0 0 3 3H32z" fill="#fff" opacity=".38" />
      {type === 'pdf' && (
        <path d="M9.3 31.5c1.6-1 3.4-4.4 4.9-8.8.9-2.7 1-5.4.2-5.6-1-.2-1.2 2.5-.3 5.2 1.3 3.9 4.5 6.9 7.7 7.3 1.7.2 1.9-1.1.4-1.5-2.7-.8-8.7.8-11.7 2.6-1.3.8-1.9.9-1.2.8z" fill="none" stroke="#fff" strokeWidth="1.5" strokeLinejoin="round" />
      )}
      {(type === 'jpg' || type === 'png') && (
        <g fill="#fff">
          <rect x="7.5" y="17" width="17" height="14" rx="2" fill="none" stroke="#fff" strokeWidth="1.6" />
          <circle cx="12" cy="21.4" r="1.7" />
          <path d="M8.5 29.5l4.8-5 3.2 3.2 2.8-2.7 4.2 4.5z" />
        </g>
      )}
      {(type === 'docx' || type === 'xlsx') && (
        <text x="16" y="28.5" textAnchor="middle" fontSize="7.4" fontWeight="800" fill="#fff" fontFamily="Inter, sans-serif">{type.toUpperCase()}</text>
      )}
    </svg>
  )
}

export function FolderIcon({ color = '#3B82F6', size = 52 }) {
  return (
    <svg width={size} height={size * 0.82} viewBox="0 0 50 41" aria-hidden="true">
      <path d="M4 1h13.5c1.1 0 2.1.4 2.8 1.2L24.5 7H46a4 4 0 0 1 4 4v26a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4V5a4 4 0 0 1 4-4z" fill={color} />
      <path d="M0 15a4 4 0 0 1 4-4h42a4 4 0 0 1 4 4v22a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4z" fill="#fff" opacity=".22" />
    </svg>
  )
}

export function UrduGlyph({ size = 18 }) {
  return <span className="urdu-glyph" style={{ fontSize: size * 0.8 }}>اُ</span>
}
