import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft, ArrowRight, BadgeCheck, Camera, CheckCheck, ChevronDown, Copy, ExternalLink, FileUp, Lock, Mic,
  MoreVertical, Paperclip, Phone, RefreshCw, Send, ShieldCheck, Smile, CheckCircle2, BellRing, Signal, Wifi,
  BatteryFull, Loader2
} from 'lucide-react'
import { Breadcrumb, Checkbox } from '../components/common'
import { PakFlag, WhatsAppIcon } from '../components/Icons'
import { useUI } from '../components/UIContext'
import { Skeleton } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { whatsappService } from '../api/services/whatsappService'

const CAN_DO = [
  { tone: 'blue', icon: WhatsAppIcon, t: 'Ask quick legal questions', d: 'Get instant answers to common legal queries.' },
  { tone: 'green', icon: BellRing, t: 'Receive case updates', d: 'Stay informed about your cases and deadlines.' },
  { tone: 'orange', icon: FileUp, t: 'Upload supported documents', d: 'Send documents (PDF, images) for basic review.' },
  { tone: 'purple', icon: RefreshCw, t: 'Save conversations to LegalMate', d: 'Automatically save your WhatsApp chats to your account.' },
]

// Demo conversation shown in the phone preview (static marketing content).
const INITIAL_CHAT = [
  { from: 'bot', time: '9:41 AM', body: (
    <>
      <p>👋 <b>Assalamu Alaikum!</b><br />Welcome to <b>LegalMate!</b></p>
      <p>I'm your AI legal assistant. You can ask questions, get updates and access legal resources.</p>
      <p>Here's what you can do:</p>
      <ol><li><b>Ask a legal question</b></li><li><b>Check document status</b></li><li><b>Find legal aid</b></li><li><b>Talk to support</b></li></ol>
      <p>Reply with the number or type your question.</p>
    </>
  ) },
  { from: 'me', time: '9:42 AM', body: <p>1<br />What is the notice period for a tenancy agreement in Pakistan?</p> },
  { from: 'bot', time: '9:42 AM', body: (
    <>
      <p>In Pakistan, the typical notice period for residential tenancy is 1–3 months, depending on the agreement terms and local laws.</p>
      <p>Under the Rent Restriction Act, 2001, notice requirements may vary by province.</p>
      <p><b>Source:</b> <a className="wa-link" href="#source"><ExternalLink size={13} /> Rent Restriction Act, 2001</a></p>
    </>
  ) },
  { from: 'bot', time: '9:42 AM', body: (
    <>
      <p>Need more details? You can also view this on your LegalMate dashboard.</p>
      <Link className="wa-open" to="/chat/tenant-rights"><ExternalLink size={16} /> Open in LegalMate</Link>
    </>
  ) },
]

export default function WhatsApp() {
  const { toast } = useUI()
  const [phone, setPhone] = useState('')
  const [agree, setAgree] = useState(true)
  const [connecting, setConnecting] = useState(false)
  const [chat, setChat] = useState(INITIAL_CHAT)
  const [draft, setDraft] = useState('')
  const [typing, setTyping] = useState(false)
  const [testing, setTesting] = useState(false)
  const [, tick] = useState(0)
  const scrollRef = useRef(null)

  const status = useQuery(signal => whatsappService.getStatus(signal), [])
  const qr = useQuery(signal => whatsappService.getQr(signal), [])
  const commands = useQuery(signal => whatsappService.listCommands(signal), [])
  const connected = status.data?.connected
  const secs = qr.data ? Math.max(0, Math.round((new Date(qr.data.expiresAt) - Date.now()) / 1000)) : 0

  useEffect(() => { if (status.data?.phone && !phone) setPhone(status.data.phone) }, [status.data, phone])

  // Countdown for the QR code expiry.
  useEffect(() => {
    const t = setInterval(() => tick(x => x + 1), 1000)
    return () => clearInterval(t)
  }, [])
  const firstLen = useRef(chat.length)
  useEffect(() => {
    if (chat.length === firstLen.current && !typing) return // keep the welcome message in view on first load
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [chat.length, typing])

  const clock = () => new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  // Phone preview: the reply comes from the bot preview endpoint.
  const send = async text => {
    if (!text.trim()) return
    setChat(c => [...c, { from: 'me', time: clock(), body: <p>{text}</p> }])
    setDraft('')
    setTyping(true)
    try {
      const { reply } = await whatsappService.preview(text)
      setChat(c => [...c, { from: 'bot', time: clock(), body: reply.split('\n').map((l, i) => <p key={i}>{l}</p>) }])
    } catch (e) {
      toast(e.message, 'info')
    } finally {
      setTyping(false)
    }
  }

  const connect = async () => {
    if (phone.replace(/\D/g, '').length < 10) return toast('Enter a valid mobile number', 'info')
    if (!agree) return toast('Please agree to receive messages on WhatsApp', 'info')
    setConnecting(true)
    try {
      const res = await whatsappService.connect({ phone, consent: agree })
      status.setData(s => ({ ...s, connected: res.status === 'connected', phone: res.phone }))
      toast(res.status === 'connected' ? 'WhatsApp connected successfully!' : 'Check WhatsApp and reply to our message to finish linking.', res.status === 'connected' ? 'success' : 'info')
    } catch (e) {
      toast(e.message || 'Could not connect WhatsApp', 'info')
    } finally {
      setConnecting(false)
    }
  }

  const sendTest = async () => {
    setTesting(true)
    try { await whatsappService.sendTestMessage(); toast('Test message sent to your WhatsApp'); send('/status') } catch (e) { toast(e.message, 'info') } finally { setTesting(false) }
  }

  return (
    <div className="wa">
      <div className="wa-left">
        <div className="page-head wa-head">
          <div>
            <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'WhatsApp Bot' }]} />
            <h1 className="page-title">LegalMate on WhatsApp</h1>
            <p className="page-sub wa-sub">Ask basic legal questions and receive updates directly through WhatsApp.</p>
          </div>
        </div>

        <section className="card wa-connect">
          <div className="wa-connect-form">
            <h2 className="cb-h2">Connect Your WhatsApp Number</h2>
            <p className="wa-muted">Enter your phone number to link it with your LegalMate account.</p>
            <div className="wa-phone">
              <span className="wa-cc"><PakFlag width={24} /> <ChevronDown size={15} /></span>
              <span className="wa-plus">+92</span>
              <input value={phone} onChange={e => setPhone(e.target.value.replace(/[^\d ]/g, '').slice(0, 11))} inputMode="tel" aria-label="Phone number" />
            </div>
            <Checkbox checked={agree} onChange={setAgree} tone="blue">I agree to receive messages from LegalMate on WhatsApp, including legal information, case updates and notifications.</Checkbox>
            <a href="#privacy" className="wa-privacy">View Privacy Policy</a>
            <button className="btn btn-orange btn-xl btn-block wa-connect-btn" onClick={connect} disabled={connecting}>
              {connecting ? <Loader2 size={22} className="spin" /> : <WhatsAppIcon size={24} />} {connecting ? 'Connecting…' : connected ? 'Reconnect WhatsApp' : 'Connect WhatsApp'}
            </button>
          </div>
          <div className="wa-or"><span>OR</span></div>
          <div className="wa-qr">
            <h3>Scan QR Code</h3>
            <p className="wa-muted">Open WhatsApp on your phone and scan this code.</p>
            {qr.data ? <img src={qr.data.qrImageUrl} alt="WhatsApp QR code" className={secs === 0 ? 'expired' : ''} /> : <Skeleton w={126} h={126} />}
            <a className="btn btn-soft btn-block wa-web" href={qr.data?.webUrl || 'https://web.whatsapp.com'} target="_blank" rel="noreferrer"><ExternalLink size={17} /> Open WhatsApp Web</a>
            <p className="wa-exp">{secs > 0 ? <>QR code expires in {String(Math.floor(secs / 60)).padStart(2, '0')}:{String(secs % 60).padStart(2, '0')}</> : 'QR code expired'} <button className="link small" onClick={() => qr.reload()}><RefreshCw size={14} className={qr.loading ? 'spin' : ''} /> Refresh</button></p>
          </div>
        </section>

        <section className="card wa-can">
          <h2 className="cb-h2">What You Can Do on WhatsApp</h2>
          <div className="wa-can-grid">
            {CAN_DO.map(c => (
              <div key={c.t} className={`wa-tile wa-${c.tone}`}>
                <div className="wa-tile-head"><c.icon size={30} /><b>{c.t}</b></div>
                <p>{c.d}</p>
              </div>
            ))}
          </div>
        </section>

        <div className="wa-bottom">
          <section className="card wa-cmds">
            <h2 className="cb-h2">Example Commands</h2>
            <p className="wa-muted">You can send these commands on WhatsApp:</p>
            <div className="wa-cmd-table">
              {(commands.data?.items || []).map(({ command: c, description: d }) => (
                <div key={c} className="wa-cmd">
                  <b>{c}</b><span>{d}</span>
                  <button className="icon-btn-plain" onClick={() => { navigator.clipboard?.writeText(`${c} ${d}`); toast(`Copied “${c}”`) }} aria-label={`Copy ${c}`}><Copy size={17} /></button>
                </div>
              ))}
            </div>
          </section>
          <section className="card wa-privacy-card">
            <div className="wa-priv-head">
              <ShieldCheck size={34} strokeWidth={1.6} />
              <div>
                <h2 className="cb-h2">Your Privacy Matters</h2>
                <p>Your conversations on WhatsApp are encrypted end-to-end. We only use your number to provide LegalMate services and will not share it with third parties.</p>
                <a href="#privacy" className="link small">Learn more about our privacy policy <ArrowRight size={15} /></a>
              </div>
            </div>
            <div className="wa-safe"><Lock size={30} fill="#16a34a" color="#fff" /><div><b>Safe. Secure. Confidential.</b><span>Your legal information stays protected.</span></div></div>
          </section>
        </div>
      </div>

      <div className="wa-right">
        <div className="phone">
          <div className="phone-screen">
            <div className="phone-status"><b>9:41</b><span className="phone-notch" /><span className="phone-icons"><Signal size={15} /><Wifi size={15} /><BatteryFull size={18} /></span></div>
            <div className="wa-bar">
              <ArrowLeft size={22} className="wa-back" />
              <span className="wa-avatar"><img src="/assets/img/logo-mark-gold.png" alt="" /></span>
              <div><b>LegalMate <BadgeCheck size={17} fill="#22c55e" color="#fff" /></b><span>Business Account</span></div>
              <Phone size={20} /><MoreVertical size={20} />
            </div>
            <div className="wa-chat" ref={scrollRef}>
              {chat.map((m, i) => (
                <div key={i} className={`wa-msg ${m.from}`}>
                  {m.body}
                  <span className="wa-time">{m.time}{m.from === 'me' && <CheckCheck size={14} />}</span>
                </div>
              ))}
              {typing && <div className="wa-msg bot wa-typing"><i /><i /><i /></div>}
            </div>
            <form className="wa-input" onSubmit={e => { e.preventDefault(); send(draft) }}>
              <div><Smile size={20} /><input value={draft} onChange={e => setDraft(e.target.value)} placeholder="Type a message..." aria-label="Message" /><Paperclip size={19} /><Camera size={19} /></div>
              <button className="wa-mic" aria-label={draft ? 'Send' : 'Voice message'}>{draft ? <Send size={19} /> : <Mic size={20} />}</button>
            </form>
          </div>
        </div>
        {connected && (
          <div className="wa-success">
            <CheckCircle2 size={34} fill="#16a34a" color="#fff" />
            <div><b>WhatsApp connected successfully!</b><span>You can now chat with LegalMate on WhatsApp.</span></div>
            <button className="btn btn-outline" onClick={sendTest} disabled={testing}>{testing ? <Loader2 size={16} className="spin" /> : <Send size={16} />} Send Test Message</button>
          </div>
        )}
      </div>
    </div>
  )
}
