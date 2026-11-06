import { AlertTriangle, Inbox, RefreshCw } from 'lucide-react'

/** Shimmer placeholder block. */
export function Skeleton({ w = '100%', h = 16, r = 8, style }) {
  return <span className="skeleton" style={{ width: w, height: h, borderRadius: r, ...style }} />
}

/** Generic page skeleton shown while a page's first request is in flight. */
export function PageSkeleton({ cards = 4, rows = 2 }) {
  return (
    <div className="page-skeleton" aria-busy="true" aria-label="Loading">
      <Skeleton w={140} h={14} />
      <Skeleton w={320} h={34} style={{ marginTop: 10 }} />
      <Skeleton w={420} h={14} style={{ marginTop: 10 }} />
      <div className="sk-grid" style={{ gridTemplateColumns: `repeat(${cards}, 1fr)` }}>
        {Array.from({ length: cards }).map((_, i) => <Skeleton key={i} h={130} r={14} />)}
      </div>
      {Array.from({ length: rows }).map((_, i) => <Skeleton key={i} h={220} r={14} style={{ marginTop: 16 }} />)}
    </div>
  )
}

/** Error block with a retry button. */
export function ErrorState({ error, onRetry, compact }) {
  return (
    <div className={`state-box ${compact ? 'compact' : ''}`} role="alert">
      <span className="icon-tile tile-red tile-lg"><AlertTriangle /></span>
      <b>Something went wrong</b>
      <p>{error?.message || 'We could not load this content. Please check your connection and try again.'}</p>
      {onRetry && <button className="btn btn-outline" onClick={() => onRetry()}><RefreshCw size={16} /> Try again</button>}
    </div>
  )
}

export function EmptyState({ icon: Icon = Inbox, title = 'Nothing here yet', text, action }) {
  return (
    <div className="state-box compact">
      <span className="icon-tile tile-gray tile-lg"><Icon /></span>
      <b>{title}</b>
      {text && <p>{text}</p>}
      {action}
    </div>
  )
}

/**
 * Renders skeleton / error / content for a `useQuery` result.
 *   <QueryBoundary query={q} skeleton={<PageSkeleton />}>{data => <Page data={data} />}</QueryBoundary>
 */
export function QueryBoundary({ query, skeleton = <PageSkeleton />, children }) {
  if (query.error && query.data === undefined) return <ErrorState error={query.error} onRetry={query.reload} />
  if (query.data === undefined || query.data === null) return query.loading ? skeleton : <ErrorState onRetry={query.reload} />
  return children(query.data)
}
