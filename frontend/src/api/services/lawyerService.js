import { api } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock, uid } from '../mock'
import { MOCK_BOOKINGS, MOCK_LAWYERS } from '../mocks/marketplace'
import { MOCK_USER, MOCK_USER_LAWYER } from '../mocks/user'
import { initials } from '../../utils/format'

const PLATFORM_FEE = 150
const DURATION_MIN = 30

const toCard = l => ({ id: l.id, name: l.name, verified: l.verified, title: l.title, specializations: l.specializations, city: l.city, fee: l.fee, rating: l.rating, reviewCount: l.reviewCount, experienceYears: l.experienceYears, availableDays: l.availableDays })

function mockSearch({ q, specialization, city, fee, sort }) {
  let list = MOCK_LAWYERS.filter(l => {
    const text = `${l.name} ${l.specializations.join(' ')} ${l.city}`.toLowerCase()
    if (q && !q.toLowerCase().split(/\s+/).every(w => text.includes(w))) return false
    if (specialization && !l.specializations.includes(specialization)) return false
    if (city && l.city !== city) return false
    if (fee === 'under2000' && l.fee >= 2000) return false
    if (fee === '2000to4000' && (l.fee < 2000 || l.fee > 4000)) return false
    if (fee === 'above4000' && l.fee <= 4000) return false
    return true
  })
  if (sort === 'rating') list = [...list].sort((a, b) => b.rating - a.rating)
  if (sort === 'feeAsc') list = [...list].sort((a, b) => a.fee - b.fee)
  return { items: list.map(toCard), total: list.length }
}

function computeTotal(fee) {
  return { fee, platformFee: PLATFORM_FEE, total: fee + PLATFORM_FEE }
}

export const lawyerService = {
  /** filters: { q, specialization, city, fee: 'under2000'|'2000to4000'|'above4000', sort: 'relevance'|'rating'|'feeAsc' } -> { items, total } */
  search: (filters, signal) => (USE_MOCKS ? mock(mockSearch(filters)) : api.get(EP.lawyers.list, { query: filters, signal })),

  /** -> full Lawyer profile (credentials, reviews, bio) */
  getLawyer: (id, signal) => (USE_MOCKS ? mock(MOCK_LAWYERS.find(l => l.id === id)) : api.get(EP.lawyers.one(id), { signal })),

  /** payload: { lawyerId, date, time, type: 'video'|'phone'|'in_person' } -> Booking (status: pending_payment) */
  createBooking: payload => {
    if (!USE_MOCKS) return api.post(EP.bookings.list, payload)
    const lawyer = MOCK_LAWYERS.find(l => l.id === payload.lawyerId)
    const booking = {
      id: uid('bkg'),
      lawyerId: lawyer.id,
      lawyerName: lawyer.name,
      clientId: MOCK_USER.id,
      clientName: MOCK_USER.name,
      date: payload.date,
      time: payload.time,
      type: payload.type,
      durationMin: DURATION_MIN,
      status: 'pending_payment',
      paymentMethod: null,
      paymentStatus: 'unpaid',
      ...computeTotal(lawyer.fee),
      createdAt: new Date().toISOString(),
    }
    MOCK_BOOKINGS.push(booking)
    return mock(booking, 500)
  },

  /** -> Booking */
  getBooking: (id, signal) => (USE_MOCKS ? mock(MOCK_BOOKINGS.find(b => b.id === id)) : api.get(EP.bookings.one(id), { signal })),

  /** payload: { method: 'cash'|'bank_transfer' } -> updated Booking */
  payBooking: (id, payload) => {
    if (!USE_MOCKS) return api.post(EP.bookings.pay(id), payload)
    const booking = MOCK_BOOKINGS.find(b => b.id === id)
    booking.paymentMethod = payload.method
    booking.paymentStatus = payload.method === 'cash' ? 'cash_pending' : 'bank_pending_verification'
    booking.status = 'confirmed'
    return mock(booking, 600)
  },

  /** -> { items: Booking[] } bookings made by the signed-in client */
  myBookings: signal => (USE_MOCKS ? mock({ items: MOCK_BOOKINGS.filter(b => b.clientId === MOCK_USER.id) }) : api.get(EP.bookings.mine, { signal })),

  /** patch: partial Lawyer fields (bio, fee, city, specializations, languages, modes) -> updated Lawyer */
  updateProfile: (id, patch) => {
    if (!USE_MOCKS) return api.patch(EP.lawyers.one(id), patch)
    const lawyer = MOCK_LAWYERS.find(l => l.id === id)
    Object.assign(lawyer, patch)
    return mock(lawyer, 500)
  },

  /** -> { items: Booking[] } every booking for this lawyer, for the lawyer portal */
  consultationsFor: (lawyerId, signal) => (USE_MOCKS ? mock({ items: MOCK_BOOKINGS.filter(b => b.lawyerId === lawyerId) }) : api.get(EP.bookings.list, { query: { lawyerId }, signal })),

  /** Marks a confirmed booking as completed once the session has taken place. -> updated Booking */
  completeBooking: id => {
    if (!USE_MOCKS) return api.post(EP.bookings.complete(id))
    const booking = MOCK_BOOKINGS.find(b => b.id === id)
    booking.status = 'completed'
    if (booking.paymentMethod === 'cash') booking.paymentStatus = 'paid'
    return mock(booking, 400)
  },

  /** -> { totalEarned, pending, completedCount, items: Booking[] } earnings summary for this lawyer */
  earningsFor: (lawyerId, signal) => {
    const compute = () => {
      const bookings = MOCK_BOOKINGS.filter(b => b.lawyerId === lawyerId)
      const totalEarned = bookings.filter(b => b.paymentStatus === 'paid').reduce((s, b) => s + b.fee, 0)
      const pending = bookings.filter(b => b.paymentStatus === 'cash_pending' || b.paymentStatus === 'bank_pending_verification').reduce((s, b) => s + b.fee, 0)
      const completedCount = bookings.filter(b => b.status === 'completed').length
      return { totalEarned, pending, completedCount, items: bookings }
    }
    return USE_MOCKS ? mock(compute()) : api.get(EP.lawyers.earnings(lawyerId), { signal })
  },

  /** payload: { name, email, phone, city, fee, specializations, languages, modes, bio } -> new Lawyer (verified: 'pending') */
  apply: payload => {
    if (!USE_MOCKS) return api.post(EP.lawyers.apply, payload)
    const lawyer = {
      id: uid('lw'), name: payload.name, verified: 'pending', title: 'Advocate',
      specializations: payload.specializations, city: payload.city, fee: Number(payload.fee),
      rating: 0, reviewCount: 0, experienceYears: Number(payload.experienceYears) || 0,
      languages: payload.languages, modes: payload.modes, bio: payload.bio,
      credentials: payload.credentials || [], reviews: [], availableDays: [], slotTimes: [],
    }
    MOCK_LAWYERS.push(lawyer)
    // The single demo lawyer account now represents this new applicant, so signing in as "Lawyer" shows their pending status.
    Object.assign(MOCK_USER_LAWYER, {
      lawyerId: lawyer.id, name: lawyer.name, firstName: lawyer.name.split(' ')[0], initials: initials(lawyer.name),
      email: payload.email, phone: payload.phone, city: payload.city,
    })
    return mock(lawyer, 700)
  },
}
