import { api } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock } from '../mock'
import { MOCK_EMERGENCY } from '../mocks/legalAid'
import { MOCK_LAWYERS } from '../mocks/marketplace'

const savedIds = new Set()

// Our lawyer's modes: video/phone/in_person -> the single display string the Legal Aid UI expects.
function modeLabel(l) {
  const remote = l.modes.includes('video') || l.modes.includes('phone')
  const inPerson = l.modes.includes('in_person')
  if (remote && inPerson) return 'Online & In-person'
  return inPerson ? 'In-person' : 'Online'
}

// availableDays/slotTimes -> { label, nextSlotLabel } the way the original availability field looked.
function availabilityFor(l) {
  const today = new Date(); today.setHours(0, 0, 0, 0)
  for (let i = 0; i < 14; i++) {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() + i)
    if (l.availableDays.includes(d.getDay())) {
      const label = i === 0 ? 'Available Today' : i === 1 ? 'Available Tomorrow' : 'Available This Week'
      return { label, nextSlotLabel: l.slotTimes[0] ? `Next slot: ${l.slotTimes[0]}` : 'Contact to schedule' }
    }
  }
  return { label: 'By Request', nextSlotLabel: 'Contact to schedule' }
}

const toProvider = l => ({
  id: l.id, kind: 'lawyer', name: l.name, verified: l.verified === 'verified',
  practiceAreas: l.specializations, languages: l.languages, city: l.city, distanceKm: null,
  modes: modeLabel(l), availability: availabilityFor(l), fee: 'paid',
  rating: l.rating, reviewCount: l.reviewCount, experienceLabel: `${l.experienceYears} years experience`,
  bio: l.bio, saved: savedIds.has(l.id),
})

function mockSearch({ q, area, city, language, fee, mode, availability, sort = 'relevance' }) {
  let list = MOCK_LAWYERS.map(toProvider).filter(p => {
    const text = `${p.name} ${p.practiceAreas.join(' ')} ${p.city}`.toLowerCase()
    if (q && !q.toLowerCase().split(/\s+/).every(w => text.includes(w))) return false
    if (area && !p.practiceAreas.some(a => a.includes(area.split(' ')[0]))) return false
    if (city && p.city !== city) return false
    if (language && !p.languages.includes(language)) return false
    if (fee && p.fee !== fee) return false
    if (mode && p.modes !== mode) return false
    if (availability && p.availability.label !== availability) return false
    return true
  })
  if (sort === 'rating') list = [...list].sort((a, b) => b.rating - a.rating)
  if (sort === 'distance') list = [...list].sort((a, b) => (a.distanceKm ?? 1e9) - (b.distanceKm ?? 1e9))
  return { items: list, total: list.length, mapImageUrl: '/assets/img/legal-aid-map.jpg' }
}

export const legalAidService = {
  /**
   * filters: { q, area, city, language, fee: 'free'|'paid', mode, availability, sort: 'relevance'|'rating'|'distance', page }
   * -> { items: Provider[], total, mapImageUrl? }
   */
  search: (filters, signal) => (USE_MOCKS ? mock(mockSearch(filters)) : api.get(EP.legalAid.providers, { query: filters, signal })),

  setSaved: (id, saved) => {
    if (!USE_MOCKS) return api.put(EP.legalAid.saved(id), { saved })
    if (saved) savedIds.add(id); else savedIds.delete(id)
    return mock(null, 100)
  },

  /** -> { items: [{ number, label, icon }] } */
  emergencyContacts: signal => (USE_MOCKS ? mock({ items: MOCK_EMERGENCY }, 0) : api.get(EP.legalAid.emergency, { signal })),
}
