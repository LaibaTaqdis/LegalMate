import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BriefcaseBusiness, CalendarCheck, CalendarClock, CircleDollarSign, Clock, Heart, List, LocateFixed, Map, MapPin,
  MessageSquare, Monitor, Phone, Search, Siren, Star, Users, CheckCircle2, ChevronDown
} from 'lucide-react'
import { Breadcrumb, Select, useClickOutside } from '../components/common'
import { useUI } from '../components/UIContext'
import { ErrorState, Skeleton } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { legalAidService } from '../api/services/legalAidService'
import { initials } from '../utils/format'

// API provider -> card fields used by the markup
const toCard = p => ({
  ...p,
  areas: p.practiceAreas,
  langs: p.languages.join(', '),
  dist: p.distanceKm != null ? `${p.distanceKm.toLocaleString('en-US')} km` : null,
  mode: p.modes,
  avail: p.availability.label,
  slot: p.availability.nextSlotLabel,
  reviews: p.reviewCount,
  exp: p.experienceLabel,
})

// Filter key in the UI -> query param + value mapping for the API
const FILTER_PARAM = { area: 'area', city: 'city', lang: 'language', fee: 'fee', mode: 'mode', avail: 'availability' }
const SORT_PARAM = { Relevance: 'relevance', Rating: 'rating', Distance: 'distance' }
const EMERGENCY_ICONS = { phone: Phone, siren: Siren }

const FILTERS = [
  { k: 'area', icon: BriefcaseBusiness, label: 'Practice Area', options: ['Family Law', 'Property Law', 'Criminal Law', 'Corporate Law', 'Labour Matters', 'Startup & IP Advisory'] },
  { k: 'city', icon: MapPin, label: 'City', options: ['Islamabad', 'Rawalpindi', 'Lahore', 'Karachi'] },
  { k: 'lang', icon: MessageSquare, label: 'Language', options: ['English', 'Urdu', 'Punjabi'] },
  { k: 'mode', icon: Monitor, label: 'Online / In-person', options: ['Online & In-person', 'In-person'] },
  { k: 'avail', icon: Clock, label: 'Availability', options: ['Available Today', 'Available Tomorrow', 'Available This Week'] },
]

function FilterDrop({ f, value, onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useClickOutside(() => setOpen(false))
  return (
    <div className="la-filter" ref={ref}>
      <button className={value ? 'set' : ''} onClick={() => setOpen(o => !o)}><f.icon size={18} /> <span>{value || f.label}</span> <ChevronDown size={17} /></button>
      {open && (
        <div className="popover la-filter-menu">
          {f.options.map(o => <button key={o} className={`popover-item ${o === value ? 'active' : ''}`} onClick={() => { onChange(o === value ? null : o); setOpen(false) }}>{o}</button>)}
        </div>
      )}
    </div>
  )
}

export default function LegalAid() {
  const { toast } = useUI()
  const [q, setQ] = useState('')
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState({})
  const [sort, setSort] = useState('Relevance')
  const [view, setView] = useState('list')
  const [selected, setSelected] = useState(null)
  const [savedOverride, setSavedOverride] = useState({})

  const params = useMemo(() => {
    const p = { q: query || undefined, sort: SORT_PARAM[sort] }
    Object.entries(filters).forEach(([k, v]) => { if (v) p[FILTER_PARAM[k]] = k === 'fee' ? v.toLowerCase() : v })
    return p
  }, [query, filters, sort])
  const search = useQuery(signal => legalAidService.search(params, signal), [JSON.stringify(params)])
  const emergency = useQuery(signal => legalAidService.emergencyContacts(signal), [])

  const results = (search.data?.items || []).map(toCard)
  const count = search.data?.total ?? 0
  const sel = results.find(p => p.id === selected) || results[0]
  const mapImage = search.data?.mapImageUrl || '/assets/img/legal-aid-map.jpg'
  const isSaved = p => savedOverride[p.id] ?? p.saved

  const toggleSave = async p => {
    const next = !isSaved(p)
    setSavedOverride(s => ({ ...s, [p.id]: next }))
    try { await legalAidService.setSaved(p.id, next); toast(next ? 'Saved to your list' : 'Removed from saved') } catch (e) { setSavedOverride(s => ({ ...s, [p.id]: !next })); toast(e.message, 'info') }
  }

  const Verified = () => <span className="pill pill-green la-verified"><CheckCircle2 size={15} fill="#22a45a" color="#fff" /> Verified</span>

  return (
    <div className="la">
      <div className="page-head la-head">
        <div>
          <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Find a Lawyer' }]} />
          <h1 className="page-title">Find a Lawyer</h1>
          <p className="page-sub la-sub">Search verified lawyers by specialization, city and fee, then view their profile and book a consultation.</p>
        </div>
        <div className="la-emergency">
          <div className="la-em-main"><Siren size={36} /><div><b>In an emergency?</b><span>For immediate legal assistance, call the National Helpline.</span></div></div>
          {(emergency.data?.items || []).map(c => {
            const Icon = EMERGENCY_ICONS[c.icon] || Phone
            return <a key={c.number} href={`tel:${c.number}`} className="la-em-num"><b><Icon size={22} /> {c.number}</b><span>{c.label}</span></a>
          })}
        </div>
      </div>

      <form className="la-search" onSubmit={e => { e.preventDefault(); setQuery(q) }}>
        <label><Search size={20} /><input value={q} onChange={e => setQ(e.target.value)} placeholder="Search by lawyer name or specialization..." /></label>
        <button className="btn btn-orange la-search-btn">Search</button>
      </form>

      <div className="la-filters">
        {FILTERS.map(f => <FilterDrop key={f.k} f={f} value={filters[f.k]} onChange={v => setFilters(p => ({ ...p, [f.k]: v }))} />)}
        <button className="link la-clear" onClick={() => { setFilters({}); setQ(''); setQuery('') }}>Clear All</button>
      </div>

      <div className="la-grid">
        <div className="la-results">
          <div className="la-results-head">
            <p>Showing <b>{count} results</b></p>
            <div className="la-sort">
              <span>Sort by:</span>
              <Select compact value={sort} onChange={setSort} options={['Relevance', 'Rating', 'Distance']} className="la-sort-sel" />
              <div className="view-toggle la-view">
                <button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')}><List size={17} /> List</button>
                <button className={view === 'map' ? 'active' : ''} onClick={() => setView('map')}><Map size={17} /> Map</button>
              </div>
            </div>
          </div>

          {view === 'map' && (
            <div className="la-map la-map-full"><img src={mapImage} alt="Map of legal help near Islamabad" /></div>
          )}

          <div className={`la-list ${search.loading && search.data ? 'is-refreshing' : ''}`}>
            {!search.data && search.loading && Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} h={112} r={14} />)}
            {search.error && !search.data && <ErrorState compact error={search.error} onRetry={search.reload} />}
            {results.map(p => (
              <article key={p.id} className={`card la-card ${sel?.id === p.id ? 'selected' : ''}`} onClick={() => setSelected(p.id)}>
                <span className="la-photo la-avatar">{initials(p.name)}</span>
                <div className="la-info">
                  <h3>{p.name} <Verified /></h3>
                  <p className="la-areas">{p.areas.map((a, i) => <span key={a}>{i > 0 && <i>|</i>}{a}</span>)}</p>
                  <p className="la-meta"><MessageSquare size={16} /> {p.langs}</p>
                  <p className="la-meta"><MapPin size={16} /> {p.city}{p.dist && <> <i>•</i> {p.dist}</>}<span className="la-mode"><Monitor size={16} /> {p.mode}</span></p>
                </div>
                <div className="la-cta">
                  <div className="la-avail"><span><span className="dot dot-green" /> {p.avail}</span><small>{p.slot}</small></div>
                  <button className={`icon-btn-plain la-heart ${isSaved(p) ? 'on' : ''}`} onClick={e => { e.stopPropagation(); toggleSave(p) }} aria-label="Save"><Heart size={21} /></button>
                  <div className="la-btns">
                    <Link to={`/find-a-lawyer/${p.id}`} className="btn btn-outline" onClick={e => e.stopPropagation()}>View Profile</Link>
                    <Link to={`/find-a-lawyer/${p.id}/book`} className="btn btn-orange" onClick={e => e.stopPropagation()}><CalendarCheck size={16} /> Book Consultation</Link>
                  </div>
                </div>
              </article>
            ))}
            {search.data && !results.length && <div className="card la-none"><Users size={36} /><b>No results found</b><p>Try a different search or clear your filters.</p></div>}
          </div>
        </div>

        <aside className="la-side">
          <div className="la-map">
            <img src={mapImage} alt="Map of legal help near Islamabad" />
            <button className="la-map-hit la-map-search" onClick={() => { toast('Searching this area…', 'info'); search.reload() }} aria-label="Search this area" />
            <button className="la-map-hit la-map-plus" onClick={() => toast('Zoomed in', 'info')} aria-label="Zoom in" />
            <button className="la-map-hit la-map-minus" onClick={() => toast('Zoomed out', 'info')} aria-label="Zoom out" />
            <button className="la-map-hit la-map-loc" onClick={() => toast('Showing results near your location', 'info')} aria-label="My location"><LocateFixed size={1} /></button>
          </div>
          {sel && <section className="card la-detail">
            <div className="la-detail-top">
              <span className="la-photo la-avatar la-avatar-lg">{initials(sel.name)}</span>
              <div>
                <h3>{sel.name} <Verified /></h3>
                <p className="la-areas">{sel.areas.map((a, i) => <span key={a}>{i > 0 && <i>|</i>}{a}</span>)}</p>
                <p className="la-rating"><Star size={19} fill="#f59e0b" color="#f59e0b" /> {sel.rating.toFixed(1)} <span>({sel.reviews} reviews)</span><CalendarClock size={18} /> {sel.exp}</p>
              </div>
              <button className={`icon-btn-plain la-heart ${isSaved(sel) ? 'on' : ''}`} onClick={() => toggleSave(sel)} aria-label="Save"><Heart size={21} /></button>
            </div>
            <p className="la-meta"><MessageSquare size={16} /> {sel.langs}</p>
            <p className="la-meta"><MapPin size={16} /> {sel.city}{sel.dist && <> <i>•</i> {sel.dist}</>}<span className="la-mode"><Monitor size={16} /> {sel.mode}</span></p>
            <p className="la-bio">{sel.bio}</p>
            <div className="la-detail-btns">
              <Link to={`/find-a-lawyer/${sel.id}`} className="btn btn-outline btn-lg">View Profile</Link>
              <Link to={`/find-a-lawyer/${sel.id}/book`} className="btn btn-orange btn-lg"><CalendarCheck size={18} /> Book Consultation</Link>
            </div>
          </section>}
        </aside>
      </div>
    </div>
  )
}
