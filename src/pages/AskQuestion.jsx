import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, Send } from 'lucide-react'
import { Breadcrumb, Select } from '../components/common'
import { useUI } from '../components/UIContext'
import { communityService } from '../api/services/communityService'
import { CATEGORIES } from '../api/mocks/community'

export default function AskQuestion() {
  const navigate = useNavigate()
  const { toast } = useUI()
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState(CATEGORIES[0])
  const [body, setBody] = useState('')
  const [privacy, setPrivacy] = useState('public')
  const [busy, setBusy] = useState(false)

  const submit = async e => {
    e.preventDefault()
    setBusy(true)
    try {
      const question = await communityService.create({ title, category, body, privacy })
      toast('Your question has been posted.')
      navigate(`/community/${question.id}`)
    } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }

  return (
    <div className="forum">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Community Q&A', to: '/community' }, { label: 'Ask a Question' }]} />
      <h1 className="page-title">Ask a Question</h1>
      <p className="page-sub">Get answers from the community and verified legal professionals.</p>

      <form className="card card-pad forum-ask" onSubmit={submit}>
        <label className="field">
          <span className="field-label">Question title <span className="req">*</span></span>
          <input className="input" required value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Is a verbal rental agreement legally binding?" />
        </label>

        <label className="field">
          <span className="field-label">Category <span className="req">*</span></span>
          <Select value={category} onChange={setCategory} options={CATEGORIES} />
        </label>

        <label className="field">
          <span className="field-label">Details <span className="req">*</span></span>
          <textarea className="textarea" rows={7} required value={body} onChange={e => setBody(e.target.value)} placeholder="Share as much detail as possible — what happened, relevant dates, and what you'd like to know." />
        </label>

        <div className="field">
          <span className="field-label">Privacy</span>
          <div className="forum-privacy">
            <button type="button" className={privacy === 'public' ? 'active' : ''} onClick={() => setPrivacy('public')}>Public <span>Shown with your name</span></button>
            <button type="button" className={privacy === 'anonymous' ? 'active' : ''} onClick={() => setPrivacy('anonymous')}>Anonymous <span>Your name is hidden</span></button>
          </div>
        </div>

        <button className="btn btn-orange btn-lg forum-post-btn" disabled={busy}>{busy ? <Loader2 size={18} className="spin" /> : <Send size={18} />} Post Question</button>
      </form>
    </div>
  )
}
