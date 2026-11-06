import { useState } from 'react'
import {
  Ambulance, Car, Flame, Loader2, MapPin, MessageCircleWarning, Phone, Plus, Send, Shield,
  ShieldAlert, Siren, Trash2, Users, X,
} from 'lucide-react'
import { Breadcrumb, Modal } from '../components/common'
import { useUI } from '../components/UIContext'
import { PageSkeleton } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { emergencyService } from '../api/services/emergencyService'

const CATEGORY_ICON = { shield: Shield, cross: Ambulance, flame: Flame, users: Users, 'shield-alert': ShieldAlert, car: Car }

function AddContactForm({ onClose, onSaved }) {
  const { toast } = useUI()
  const [form, setForm] = useState({ name: '', relation: '', phone: '' })
  const [busy, setBusy] = useState(false)
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async e => {
    e.preventDefault()
    setBusy(true)
    try {
      const contact = await emergencyService.addContact(form)
      onSaved(contact)
      toast('Emergency contact added')
      onClose()
    } catch (err) { toast(err.message, 'info') } finally { setBusy(false) }
  }

  return (
    <form className="em-add-form" onSubmit={submit}>
      <div className="em-add-head"><b>Add emergency contact</b><button type="button" className="icon-btn-plain" onClick={onClose} aria-label="Close"><X size={20} /></button></div>
      <label className="field"><span className="field-label">Full name</span><input className="input" required value={form.name} onChange={set('name')} placeholder="e.g. Ahmed Raza" /></label>
      <label className="field"><span className="field-label">Relation</span><input className="input" required value={form.relation} onChange={set('relation')} placeholder="e.g. Brother, Family lawyer" /></label>
      <label className="field"><span className="field-label">Phone number</span><input className="input" required value={form.phone} onChange={set('phone')} placeholder="+92 3XX XXXXXXX" /></label>
      <button className="btn btn-orange btn-lg btn-block" disabled={busy}>{busy ? <Loader2 size={18} className="spin" /> : <Plus size={18} />} Save Contact</button>
    </form>
  )
}

export default function Emergency() {
  const { toast } = useUI()
  const contactsQ = useQuery(signal => emergencyService.contacts(signal), [])
  const personalQ = useQuery(signal => emergencyService.myContacts(signal), [])
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [sending, setSending] = useState(false)
  const [sharing, setSharing] = useState(false)

  const list = personalQ.data?.items || []
  const primary = list.find(c => c.primary) || list[0]

  const sendAlert = async () => {
    setSending(true)
    try {
      const res = await emergencyService.sendAlert({ contactId: primary?.id, shareLocation: true })
      toast(`Alert sent. ${res.notifiedContact?.name || 'Your emergency contact'} has been notified with your situation and last known location.`)
      setConfirmOpen(false)
    } catch (err) { toast(err.message, 'info') } finally { setSending(false) }
  }

  const notifyContact = async () => {
    if (!primary) return toast('Add an emergency contact first.', 'info')
    try {
      const res = await emergencyService.sendAlert({ contactId: primary.id, shareLocation: false })
      toast(`${res.notifiedContact?.name} has been notified of your situation.`)
    } catch (err) { toast(err.message, 'info') }
  }

  const toggleShare = () => {
    setSharing(s => !s)
    toast(sharing ? 'Location sharing turned off.' : 'Your live location is being shared with your primary contact for the next 2 hours.', 'info')
  }

  const removeContact = async c => {
    personalQ.setData(d => ({ ...d, items: d.items.filter(x => x.id !== c.id) }))
    try { await emergencyService.removeContact(c.id) } catch { personalQ.reload() }
    toast('Contact removed', 'info')
  }

  if (!contactsQ.data) return <PageSkeleton cards={3} rows={2} />

  const { helpline, categories } = contactsQ.data

  return (
    <div className="em">
      <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Emergency Mode' }]} />
      <h1 className="page-title">Emergency Mode</h1>
      <p className="page-sub">If a client, employer or counterparty is threatening legal action against you — or you're in immediate danger — get help fast.</p>

      <div className="em-top">
        <section className="em-sos">
          <span className="em-sos-ring"><Siren size={34} /></span>
          <h2>Need help right now?</h2>
          <p>Notifies your emergency contact with your situation and last known location, and connects you to LegalMate's helpline.</p>
          <button className="btn btn-orange btn-lg em-sos-btn" onClick={() => setConfirmOpen(true)}><Send size={18} /> Send Emergency Alert</button>
          {!list.length && <p className="em-sos-hint">Add an emergency contact below so an alert has somewhere to go.</p>}
        </section>

        <div className="em-quick">
          <a className="card em-qcard" href={`tel:${helpline.number}`}>
            <span className="icon-tile tile-blue tile-md"><Phone /></span>
            <div><b>Call Legal Helpline</b><span>{helpline.sub}</span><i>{helpline.number}</i></div>
          </a>
          <button type="button" className="card em-qcard" onClick={notifyContact}>
            <span className="icon-tile tile-orange tile-md"><MessageCircleWarning /></span>
            <div><b>Notify My Emergency Contact</b><span>Instantly message {primary ? primary.name : 'your saved contact'} with your situation.</span></div>
          </button>
          <button type="button" className={`card em-qcard ${sharing ? 'on' : ''}`} onClick={toggleShare}>
            <span className="icon-tile tile-green tile-md"><MapPin /></span>
            <div><b>{sharing ? 'Sharing Location…' : 'Share My Location'}</b><span>Send a live location pin to your emergency contact for 2 hours.</span></div>
          </button>
        </div>
      </div>

      <section className="em-cats">
        <h2 className="card-title em-section-title">National Emergency Numbers</h2>
        <div className="em-cat-grid">
          {categories.map(cat => {
            const Icon = CATEGORY_ICON[cat.icon] || Shield
            return (
              <div key={cat.key} className="card em-cat">
                <div className="em-cat-head"><span className="icon-tile tile-red tile-sm"><Icon /></span><b>{cat.label}</b></div>
                <ul>
                  {cat.numbers.map(n => (
                    <li key={n.number}>
                      <span>{n.label}</span>
                      <a href={`tel:${n.number}`} className="em-num"><Phone size={14} />{n.number}</a>
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      </section>

      <section className="card card-pad em-contacts">
        <div className="card-head">
          <h2 className="card-title">My Emergency Contacts</h2>
          <button className="btn btn-outline btn-sm" onClick={() => setAddOpen(true)}><Plus size={16} /> Add Contact</button>
        </div>
        {personalQ.data && !list.length && <p className="muted em-empty">No emergency contacts yet. Add someone who should be notified if you send an alert.</p>}
        <ul className="em-contact-list">
          {list.map(c => (
            <li key={c.id} className="em-contact">
              <span className="avatar">{c.name.split(' ').map(w => w[0]).slice(0, 2).join('')}</span>
              <div className="em-contact-main"><b>{c.name}</b><span>{c.relation}{c.primary && <i className="pill pill-orange em-primary">Primary</i>}</span></div>
              <span className="em-contact-phone">{c.phone}</span>
              <a className="circle-btn" href={`tel:${c.phone}`} aria-label={`Call ${c.name}`}><Phone size={15} /></a>
              <button className="icon-btn-plain em-remove" onClick={() => removeContact(c)} aria-label={`Remove ${c.name}`}><Trash2 size={17} /></button>
            </li>
          ))}
        </ul>
      </section>

      <Modal open={confirmOpen} onClose={() => setConfirmOpen(false)} className="modal-sm em-confirm">
        <div className="em-confirm-body">
          <span className="icon-tile tile-red tile-lg"><Siren /></span>
          <h3>Send emergency alert?</h3>
          <p>This notifies {primary ? <b>{primary.name}</b> : 'your primary emergency contact'} with your current situation and last known location.</p>
          <div className="em-confirm-btns">
            <button className="btn btn-outline btn-lg" onClick={() => setConfirmOpen(false)}>Cancel</button>
            <button className="btn btn-orange btn-lg" onClick={sendAlert} disabled={sending}>{sending ? <Loader2 size={18} className="spin" /> : <Send size={18} />} Send Alert</button>
          </div>
        </div>
      </Modal>

      <Modal open={addOpen} onClose={() => setAddOpen(false)} className="modal-sm">
        <AddContactForm onClose={() => setAddOpen(false)} onSaved={contact => personalQ.setData(d => ({ ...d, items: [...(d?.items || []), contact] }))} />
      </Modal>
    </div>
  )
}
