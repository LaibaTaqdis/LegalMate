import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowRight, BarChart3, BookOpenCheck, Building2, CheckCheck, ExternalLink, FileText, GraduationCap, Lock,
  Menu, MessageCircle, Paperclip, Send, ShieldCheck, Sparkles, Upload, User, Users, X, FileSearch,
  Scale, Landmark, HeartHandshake, ClipboardCheck, MessagesSquare, Mail, Phone, MapPin
} from 'lucide-react'
import { Logo } from '../components/common'
import { PakFlag } from '../components/Icons'

const FEATURES = [
  { icon: MessageCircle, title: 'Ask Legal Questions', text: 'Get clear, easy-to-understand answers to your legal questions in plain language.' },
  { icon: FileText, title: 'Analyse Documents', text: 'Upload and analyse contracts, notices, or legal documents instantly.' },
  { icon: ShieldCheck, title: 'Store Records Securely', text: 'Keep your important legal documents safe and organised in one place.' },
]

const AUDIENCE = [
  { icon: Users, label: 'For Individuals & Families' },
  { icon: Building2, label: 'For Small Businesses' },
  { icon: GraduationCap, label: 'For Students & Learners' },
]

const STEPS = [
  { icon: MessagesSquare, title: 'Ask or upload', text: 'Type your question in English or Urdu, or upload an agreement, notice or legal letter.' },
  { icon: FileSearch, title: 'Get source-backed answers', text: 'LegalMate explains your rights in plain language with citations from Pakistani law.' },
  { icon: ClipboardCheck, title: 'Take the next step', text: 'Save to your Legal Vault, generate a case brief, or connect with verified legal aid.' },
]

const RESOURCES = [
  { icon: Landmark, tone: 'blue', title: 'Tenancy Laws in Pakistan', text: 'Know your rights as a tenant or landlord, from notice periods to deposits.' },
  { icon: Scale, tone: 'green', title: 'Labour Laws Guide', text: 'Understand wages, termination, notice periods and employee protections.' },
  { icon: HeartHandshake, tone: 'purple', title: 'Family Law Basics', text: 'Marriage, divorce, custody and inheritance explained simply.' },
  { icon: BookOpenCheck, tone: 'orange', title: 'Filing an FIR', text: 'A step-by-step guide to reporting a crime and following up with police.' },
]

export default function Landing() {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [question, setQuestion] = useState('')

  const scrollTo = id => {
    setMenuOpen(false)
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="landing">
      <header className="lp-header">
        <div className="lp-container lp-header-inner">
          <Logo variant="dark" tagline="Law Made Simpler" to="/" />
          <nav className={`lp-nav ${menuOpen ? 'open' : ''}`}>
            <button onClick={() => scrollTo('features')}>Features</button>
            <button onClick={() => scrollTo('how')}>How It Works</button>
            <button onClick={() => scrollTo('resources')}>Legal Resources</button>
            <button onClick={() => scrollTo('about')}>About</button>
            <div className="lp-nav-mobile-cta">
              <Link to="/login" className="btn btn-outline-navy">Log In</Link>
              <Link to="/onboarding" className="btn btn-orange">Get Started</Link>
            </div>
          </nav>
          <div className="lp-header-cta">
            <Link to="/login" className="btn btn-outline-navy lp-login">Log In</Link>
            <Link to="/onboarding" className="btn btn-orange lp-start">Get Started</Link>
          </div>
          <button className="lp-burger icon-btn-plain" onClick={() => setMenuOpen(o => !o)} aria-label="Menu">
            {menuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </header>

      <div className="lp-strip">
        <div className="lp-container lp-strip-inner">
          <p><span className="dot dot-green" /> <b>LegalMate is live and ready to help</b><span className="lp-strip-sep">|</span><span className="lp-strip-muted">Reliable. Secure. Always here for you.</span></p>
          <p className="lp-strip-right"><PakFlag width={20} /> Serving the people of Pakistan</p>
        </div>
      </div>

      <section className="lp-hero">
        <img className="lp-hero-mosque" src="/assets/img/landing-mosque.jpg" alt="Faisal Mosque, Islamabad - A fairer Pakistan for everyone" />
        <div className="lp-container lp-hero-grid">
          <div className="lp-hero-copy">
            <span className="lp-eyebrow"><Sparkles size={16} /> Your Personal Legal Companion</span>
            <h1 className="lp-title">Understand Your Legal Rights with Confidence</h1>
            <p className="lp-lead">Get clear legal guidance, analyse documents and securely manage your legal records-all in one place.</p>
            <div className="lp-hero-actions">
              <Link to="/onboarding" className="btn btn-orange btn-xl lp-ask">Ask LegalMate <ArrowRight size={19} /></Link>
              <Link to="/onboarding" className="btn btn-outline-navy btn-xl lp-upload"><Upload size={19} /> Upload a Document</Link>
            </div>
            <p className="lp-designed">Designed for citizens of Pakistan</p>
            <ul className="lp-trust">
              <li><span><ShieldCheck size={18} /></span>Secure</li>
              <li><span><Lock size={18} /></span>Confidential</li>
              <li><span><BookOpenCheck size={18} /></span>Source-backed</li>
            </ul>
          </div>

          <div className="lp-hero-visual">
            <div className="lp-chat">
              <div className="lp-chat-head">
                <img src="/assets/img/logo-mark-navy.png" alt="" className="lp-chat-mark" />
                <div><b>LegalMate</b><span>AI Legal Assistant</span></div>
                <span className="lp-online"><span className="dot dot-green" />Online</span>
              </div>
              <div className="lp-chat-body">
                <div className="lp-msg-user">
                  <div className="lp-bubble-user">Can my landlord increase rent without notice?</div>
                  <span className="lp-user-avatar"><User size={18} /></span>
                </div>
                <div className="lp-time lp-time-right">10:24 AM <CheckCheck size={13} /></div>
                <div className="lp-msg-bot">
                  <span className="lp-bot-avatar"><img src="/assets/img/logo-mark-gold.png" alt="" /></span>
                  <div className="lp-bubble-bot">Under standard tenancy practice, notice is typically required before a rent increase. Check your agreement and applicable housing rules.</div>
                </div>
                <div className="lp-time">10:24 AM</div>
                <div className="lp-citation">
                  <span className="lp-cite-icon"><FileText size={18} /></span>
                  <div>
                    <b>Citation: Tenancy Guidance</b>
                    <span>Pakistan Tenancy Act, 1887</span>
                    <span>Section 7 – Rent Increase and Notice Requirements</span>
                  </div>
                  <ExternalLink size={16} className="lp-cite-ext" />
                </div>
              </div>
              <form className="lp-chat-input" onSubmit={e => { e.preventDefault(); navigate('/onboarding') }}>
                <Paperclip size={18} />
                <input value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask another question..." aria-label="Ask another question" />
                <button className="lp-send" aria-label="Send"><Send size={17} /></button>
              </form>
            </div>
            <div className="lp-confidence">
              <BarChart3 size={30} strokeWidth={2.6} />
              <div><b>92%</b><span>High confidence</span></div>
            </div>
          </div>
        </div>
      </section>

      <section className="lp-features" id="features">
        <div className="lp-container">
          <div className="lp-feature-grid">
            {FEATURES.map(f => (
              <Link to="/onboarding" key={f.title} className="lp-feature">
                <span className="lp-feature-icon"><f.icon size={26} /></span>
                <div><h3>{f.title}</h3><p>{f.text}</p></div>
                <span className="circle-btn lp-feature-arrow"><ArrowRight size={18} /></span>
              </Link>
            ))}
          </div>
          <div className="lp-trusted"><span>TRUSTED. ACCESSIBLE. FOR A STRONGER PAKISTAN.</span></div>
          <div className="lp-audience">
            {AUDIENCE.map(a => (
              <div key={a.label} className="lp-aud"><span><a.icon size={24} /></span>{a.label}</div>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-section" id="how">
        <div className="lp-container">
          <p className="lp-kicker">HOW IT WORKS</p>
          <h2 className="lp-h2">Legal help in three simple steps</h2>
          <div className="lp-steps">
            {STEPS.map((s, i) => (
              <div key={s.title} className="lp-step">
                <span className="lp-step-num">{i + 1}</span>
                <span className="lp-feature-icon lp-step-icon"><s.icon size={24} /></span>
                <h3>{s.title}</h3>
                <p>{s.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-section lp-section-alt" id="resources">
        <div className="lp-container">
          <p className="lp-kicker">LEGAL RESOURCES</p>
          <h2 className="lp-h2">Know the law that affects you</h2>
          <div className="lp-resources">
            {RESOURCES.map(r => (
              <Link to="/onboarding" key={r.title} className="lp-resource">
                <span className={`icon-tile tile-${r.tone} tile-lg`}><r.icon /></span>
                <h3>{r.title}</h3>
                <p>{r.text}</p>
                <span className="link">Read More <ArrowRight size={15} /></span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-section" id="about">
        <div className="lp-container lp-about">
          <div>
            <p className="lp-kicker">ABOUT LEGALMATE</p>
            <h2 className="lp-h2">A fairer Pakistan starts with understanding the law</h2>
            <p className="lp-about-text">LegalMate is a personal legal companion built for the people of Pakistan. We turn complex laws, agreements and procedures into clear, source-backed guidance-in English and Urdu-so every citizen can make informed decisions, protect their rights and know when to seek a qualified lawyer.</p>
            <ul className="lp-about-points">
              <li><ShieldCheck size={18} /> Encrypted and private by design</li>
              <li><BookOpenCheck size={18} /> Answers grounded in Pakistani laws and sources</li>
              <li><Users size={18} /> Connects you with verified legal aid</li>
            </ul>
          </div>
          <div className="lp-cta-card">
            <h3>Ready to understand your rights?</h3>
            <p>Create your free account and ask your first legal question in minutes.</p>
            <Link to="/onboarding" className="btn btn-orange btn-lg btn-block">Get Started <ArrowRight size={18} /></Link>
            <Link to="/login" className="btn btn-outline btn-lg btn-block lp-cta-login">I already have an account</Link>
          </div>
        </div>
      </section>

      <footer className="lp-footer">
        <div className="lp-container lp-footer-grid">
          <div>
            <Logo variant="light" tagline="LAW MADE SIMPLE" />
            <p className="lp-footer-note">LegalMate provides general legal information, not formal legal representation.</p>
          </div>
          <div><h4>Product</h4><button onClick={() => scrollTo('features')}>Features</button><button onClick={() => scrollTo('how')}>How It Works</button><Link to="/onboarding">Get Started</Link></div>
          <div><h4>Resources</h4><button onClick={() => scrollTo('resources')}>Legal Guides</button><Link to="/login">Legal Aid</Link><Link to="/login">WhatsApp Bot</Link></div>
          <div><h4>Contact</h4><span><Mail size={15} /> support@legalmate.pk</span><span><Phone size={15} /> +92 51 000 0000</span><span><MapPin size={15} /> Islamabad, Pakistan</span></div>
        </div>
        <div className="lp-container lp-footer-bottom">© 2026 LegalMate. All rights reserved. <span>Terms of Service · Privacy Policy</span></div>
      </footer>
    </div>
  )
}
