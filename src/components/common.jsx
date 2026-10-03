import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, ChevronDown } from 'lucide-react'

/* ---------- Brand ---------- */
export function Logo({ variant = 'light', tagline = 'LAW MADE SIMPLE', size = 'md', to }) {
  const mark = variant === 'light' ? '/assets/img/logo-mark-gold.png' : '/assets/img/logo-mark-navy.png'
  const inner = (
    <span className={`logo logo-${variant} logo-${size}`}>
      <img src={mark} alt="" className="logo-mark" />
      <span className="logo-text">
        <span className="logo-word"><b>Legal</b>Mate</span>
        {tagline && <span className="logo-tag">{tagline}</span>}
      </span>
    </span>
  )
  return to ? <Link to={to} className="logo-link" aria-label="LegalMate home">{inner}</Link> : inner
}

/* ---------- Page header helpers ---------- */
export function Breadcrumb({ items }) {
  return (
    <nav className="breadcrumb" aria-label="Breadcrumb">
      {items.map((it, i) => (
        <span key={i} className="crumb">
          {i > 0 && <span className="crumb-sep">/</span>}
          {it.to ? <Link to={it.to}>{it.label}</Link> : <span className="crumb-current">{it.label}</span>}
        </span>
      ))}
    </nav>
  )
}

/* ---------- Donut chart (SVG) ---------- */
export function Donut({ segments, size = 150, stroke = 22, gap = 1.5, children, track = '#eef2f7' }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const total = segments.reduce((s, x) => s + x.value, 0) || 1
  let offset = 0
  return (
    <div className="donut" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
        {segments.map((s, i) => {
          const len = (s.value / total) * c
          const el = (
            <circle key={i} cx={size / 2} cy={size / 2} r={r} fill="none" stroke={s.color} strokeWidth={stroke}
              strokeDasharray={`${Math.max(len - gap, 0)} ${c}`} strokeDashoffset={-offset}
              transform={`rotate(-90 ${size / 2} ${size / 2})`} />
          )
          offset += len
          return el
        })}
      </svg>
      <div className="donut-center">{children}</div>
    </div>
  )
}

export function Ring({ value, size = 150, stroke = 12, color = '#16a34a', track = '#e8edf3', children }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  return (
    <div className="donut" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={`${(value / 100) * c} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dasharray .8s ease' }} />
      </svg>
      <div className="donut-center">{children}</div>
    </div>
  )
}

/* ---------- Misc ---------- */
export function Pill({ tone = 'gray', children, icon: Icon, className = '' }) {
  return <span className={`pill pill-${tone} ${className}`}>{Icon && <Icon size={14} />}{children}</span>
}

export function IconTile({ icon: Icon, tone = 'blue', size = 'md', children }) {
  return <span className={`icon-tile tile-${tone} tile-${size}`}>{Icon ? <Icon /> : children}</span>
}

export function useClickOutside(onOutside) {
  const ref = useRef(null)
  useEffect(() => {
    const h = e => { if (ref.current && !ref.current.contains(e.target)) onOutside() }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [onOutside])
  return ref
}

/** Lightweight custom select that matches the design's dropdown fields. */
export function Select({ value, onChange, options, icon: Icon, className = '', placeholder, compact }) {
  const [open, setOpen] = useState(false)
  const ref = useClickOutside(() => setOpen(false))
  const current = options.find(o => (o.value ?? o) === value)
  const label = current ? (current.label ?? current) : placeholder
  return (
    <div className={`select ${compact ? 'select-compact' : ''} ${open ? 'open' : ''} ${className}`} ref={ref}>
      <button type="button" className="select-btn" onClick={() => setOpen(o => !o)} aria-haspopup="listbox" aria-expanded={open}>
        {Icon && <Icon size={17} className="select-icon" />}
        <span className={`select-label ${current ? '' : 'placeholder'}`}>{label}</span>
        <ChevronDown size={16} className="select-chev" />
      </button>
      {open && (
        <ul className="select-menu" role="listbox">
          {options.map(o => {
            const v = o.value ?? o
            return (
              <li key={v} role="option" aria-selected={v === value} className={v === value ? 'active' : ''}
                onClick={() => { onChange(v); setOpen(false) }}>
                <span>{o.label ?? o}</span>{v === value && <Check size={15} />}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

export function Toggle({ checked, onChange, label }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label}
      className={`toggle ${checked ? 'on' : ''}`} onClick={() => onChange(!checked)}>
      <span className="toggle-knob" />
    </button>
  )
}

export function Checkbox({ checked, onChange, children, tone = 'navy' }) {
  return (
    <label className={`checkbox checkbox-${tone}`}>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      <span className="checkbox-box"><Check size={13} strokeWidth={3} /></span>
      {children && <span className="checkbox-label">{children}</span>}
    </label>
  )
}

export function Modal({ open, onClose, children, className = '' }) {
  useEffect(() => {
    if (!open) return
    const h = e => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', h)
    return () => document.removeEventListener('keydown', h)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="modal-backdrop" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${className}`} role="dialog" aria-modal="true">{children}</div>
    </div>
  )
}
