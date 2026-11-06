import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Eye, Loader2, MessageCircle, Send, ShieldCheck, ThumbsUp } from 'lucide-react'
import { Breadcrumb } from '../components/common'
import { useUI } from '../components/UIContext'
import { PageSkeleton, ErrorState, EmptyState } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { communityService } from '../api/services/communityService'
import { timeAgo, initials } from '../utils/format'

export default function QuestionView() {
  const { id } = useParams()
  const { toast } = useUI()
  const query = useQuery(signal => communityService.get(id, signal), [id])
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const [liked, setLiked] = useState({})

  const submit = async e => {
    e.preventDefault()
    setBusy(true)
    try {
      const a = await communityService.answer(id, { text: answer })
      query.setData(q => ({ ...q, answers: [...q.answers, a] }))
      setAnswer('')
      toast('Your answer has been posted.')
    } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }

  const like = a => {
    if (liked[a.id]) return
    setLiked(l => ({ ...l, [a.id]: true }))
    query.setData(q => ({ ...q, answers: q.answers.map(x => (x.id === a.id ? { ...x, upvotes: x.upvotes + 1 } : x)) }))
  }

  if (!query.data) {
    if (query.loading) return <PageSkeleton cards={0} rows={2} />
    return <ErrorState error={query.error} onRetry={query.reload} />
  }
  const question = query.data

  return (
    <div className="forum">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Community Q&A', to: '/community' }, { label: question.title }]} />

      <article className="card card-pad forum-question">
        <span className="pill pill-blue">{question.category}</span>
        <h1 className="forum-q-title">{question.title}</h1>
        <p className="forum-meta">{question.anonymous ? 'Anonymous' : question.authorName} <i>&middot;</i> {timeAgo(question.createdAt)} <i>&middot;</i> <Eye size={14} /> {question.viewCount} views</p>
        <p className="forum-q-body">{question.body}</p>
      </article>

      <h2 className="forum-answers-title"><MessageCircle size={19} /> {question.answers.length} Answer{question.answers.length === 1 ? '' : 's'}</h2>

      {!question.answers.length && <EmptyState title="No answers yet" text="Be the first to help answer this question." />}

      <ul className="forum-answers">
        {question.answers.map(a => (
          <li key={a.id} className="card card-pad forum-answer">
            <div className="forum-answer-head">
              <span className="avatar">{initials(a.authorName)}</span>
              <div><b>{a.authorName}</b>{a.isExpert && <span className="pill pill-green forum-expert"><ShieldCheck size={13} /> Verified Expert</span>}</div>
              <span className="forum-answer-time">{timeAgo(a.createdAt)}</span>
            </div>
            <p>{a.text}</p>
            <button type="button" className={`link-btn forum-like ${liked[a.id] ? 'on' : ''}`} onClick={() => like(a)}><ThumbsUp size={15} /> Helpful ({a.upvotes})</button>
          </li>
        ))}
      </ul>

      <form className="card card-pad forum-answer-form" onSubmit={submit}>
        <span className="field-label">Post your answer</span>
        <textarea className="textarea" rows={4} required value={answer} onChange={e => setAnswer(e.target.value)} placeholder="Share what you know — cite the relevant law or your own experience if you can." />
        <button className="btn btn-orange forum-post-btn" disabled={busy}>{busy ? <Loader2 size={18} className="spin" /> : <Send size={17} />} Post Answer</button>
      </form>
    </div>
  )
}
