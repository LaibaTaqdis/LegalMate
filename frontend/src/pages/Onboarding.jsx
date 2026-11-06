import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, FileText, Keyboard, Lock, ShieldCheck } from 'lucide-react'
import { FileIcon } from '../components/Icons'

const SLIDES = [
  {
    img: '/assets/img/onboarding-1.jpg',
    title: 'Get Legal Guidance in Simple Language',
    text: 'Ask questions in English or Urdu and receive clear, source-backed legal information.',
    chips: [
      { icon: <span className="ob-chip-a">A</span>, label: 'English' },
      { icon: <span className="urdu ob-chip-ur">اُ</span>, label: 'Urdu' },
      { icon: <FileText size={17} />, label: 'Source-backed' },
    ],
  },
  {
    img: '/assets/img/onboarding-2.jpg',
    title: 'Understand Complex Documents',
    text: 'Upload agreements, notices or legal letters to identify important clauses, risks and deadlines.',
    chips: [
      { icon: <FileIcon type="pdf" size={20} />, label: 'PDF' },
      { icon: <span className="ob-word">W</span>, label: 'DOCX' },
      { icon: <FileIcon type="jpg" size={20} color="#21a35a" />, label: 'JPG' },
      { icon: <FileIcon type="png" size={20} />, label: 'PNG' },
    ],
  },
  {
    img: '/assets/img/onboarding-3.jpg',
    title: 'Keep Your Legal Records Secure',
    text: 'Store documents, briefs and analysis reports in your private Legal Vault.',
    chips: [
      { icon: <Lock size={17} />, label: 'Encrypted' },
      { icon: <ShieldCheck size={17} fill="currentColor" stroke="#fff" />, label: 'Private' },
      { icon: <FileText size={17} />, label: 'Accessible' },
    ],
  },
]

export default function Onboarding() {
  const [step, setStep] = useState(0)
  const navigate = useNavigate()
  const last = step === SLIDES.length - 1

  const next = useCallback(() => (last ? navigate('/signup') : setStep(s => s + 1)), [last, navigate])
  const back = useCallback(() => setStep(s => Math.max(0, s - 1)), [])

  useEffect(() => {
    const onKey = e => {
      if (e.key === 'ArrowRight') next()
      if (e.key === 'ArrowLeft') back()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [next, back])

  const s = SLIDES[step]
  return (
    <div className="ob-page">
      <div className="ob-card">
        <div className="ob-main">
          <div className="ob-art">
            {SLIDES.map((sl, i) => (
              <img key={sl.img} src={sl.img} alt="" className={`ob-img ${i === step ? 'show' : ''}`} />
            ))}
            <div className="ob-logo">
              <span className="ob-logo-word">Legal<span>Mate</span></span>
              <span className="ob-logo-tag">Your Legal Questions, A Clearer Tomorrow</span>
            </div>
          </div>
          <div className="ob-copy">
            <div className="ob-kicker"><span className="ob-kicker-first">PEOPLE</span><span>|</span><span>LAW</span><span>|</span><span>A BRIGHTER TOMORROW</span></div>
            <div className="ob-text" key={step}>
              <p className="ob-step">STEP {step + 1} OF 3</p>
              <h1 className="ob-title">{s.title}</h1>
              <p className="ob-desc">{s.text}</p>
              <div className="ob-chips">
                {s.chips.map(c => (
                  <span key={c.label} className="ob-chip">{c.icon}{c.label}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="ob-foot">
          <p className="ob-hint"><Keyboard size={20} /> Press → to continue</p>
          <div className="ob-dots" role="tablist">
            {SLIDES.map((_, i) => (
              <button key={i} className={i === step ? 'active' : ''} onClick={() => setStep(i)} aria-label={`Step ${i + 1}`} />
            ))}
          </div>
          <div className="ob-actions">
            {step === 0
              ? <button className="btn btn-outline btn-lg ob-btn" onClick={() => navigate('/signup')}>Skip</button>
              : <button className="btn btn-outline btn-lg ob-btn" onClick={back}>Back</button>}
            <button className="btn btn-orange btn-lg ob-btn-primary" onClick={next}>
              {last ? 'Create Account' : 'Next'} <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
