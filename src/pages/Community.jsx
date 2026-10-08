import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Eye, MessageCircle, Plus, Search, ShieldCheck, TrendingUp } from 'lucide-react'
import { Breadcrumb, Select } from '../components/common'
import { Skeleton, ErrorState } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { communityService } from '../api/services/communityService'
import { timeAgo } from '../utils/format'

const SORTS = [{ value: 'trending', label: 'Trending' }, { value: 'recent', label: 'Most Recent' }]

export default function Community() {
  const [q, setQ] = useState('')
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState(null)
  const [sort, setSort] = useState('trending')

  const cats = useQuery(signal => communityService.categories(signal), [])
  const filters = useMemo(() => ({ category, sort, q: query || undefined }), [category, sort, query])
  const list = useQuery(signal => communityService.list(filters, signal), [JSON.stringify(filters)])
  const results = list.data?.items || []

  return (
    <div className="forum">
      <div className="page-head">
        <div>
          <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Community Q&A' }]} />
          <h1 className="page-title">Community Q&amp;A</h1>
          <p className="page-sub">Ask questions, get answers and learn from other members and legal professionals.</p>
        </div>
        <Link to="/community/ask" className="btn btn-orange btn-lg"><Plus size={18} /> Ask a Question</Link>
      </div>

      <div className="forum-grid">
        <aside className="card forum-cats">
          <h3 className="card-title forum-cats-title">Categories</h3>
          <ul>
            <li><button className={!category ? 'active' : ''} onClick={() => setCategory(null)}>All Categories<span>{cats.data?.items.reduce((s, c) => s + c.count, 0) ?? ''}</span></button></li>
            {cats.data?.items.map(c => (
              <li key={c.key}><button className={category === c.key ? 'active' : ''} onClick={() => setCategory(c.key)}>{c.key}<span>{c.count}</span></button></li>
            ))}
          </ul>
        </aside>

        <div className="forum-main">
          <div className="forum-toolbar">
            <form className="forum-search" onSubmit={e => { e.preventDefault(); setQuery(q) }}>
              <Search size={18} /><input value={q} onChange={e => setQ(e.target.value)} placeholder="Search community questions..." />
            </form>
            <Select value={sort} onChange={setSort} options={SORTS} className="forum-sort" />
          </div>

          <div className="forum-list">
            {!list.data && list.loading && Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} h={84} r={12} />)}
            {list.error && !list.data && <ErrorState compact error={list.error} onRetry={list.reload} />}
            {results.map(item => (
              <Link to={`/community/${item.id}`} key={item.id} className="card forum-item">
                <div className="forum-item-top">
                  <span className="pill pill-blue">{item.category}</span>
                  {item.hasExpertAnswer && <span className="pill pill-green forum-expert"><ShieldCheck size={13} /> Expert answered</span>}
                </div>
                <h3>{item.title}</h3>
                <p className="forum-meta">{item.authorName} <i>&middot;</i> {timeAgo(item.createdAt)} <i>&middot;</i> <Eye size={14} /> {item.viewCount} <i>&middot;</i> <MessageCircle size={14} /> {item.answerCount} answer{item.answerCount === 1 ? '' : 's'}</p>
              </Link>
            ))}
            {list.data && !results.length && (
              <div className="card forum-none"><TrendingUp size={32} /><b>No questions found</b><p>Try a different search, or be the first to ask.</p></div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
