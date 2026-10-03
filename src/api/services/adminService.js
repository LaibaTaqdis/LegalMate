import { api } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock } from '../mock'
import { MOCK_BOOKINGS, MOCK_LAWYERS } from '../mocks/marketplace'
import { MOCK_ADMIN_STATS, MOCK_ADMIN_USERS } from '../mocks/admin'

const users = [...MOCK_ADMIN_USERS]

export const adminService = {
  /** -> { totals, deltas, trend: [{ day, bookings }], recentActivity } */
  stats: signal => (USE_MOCKS ? mock(MOCK_ADMIN_STATS) : api.get(EP.admin.stats, { signal })),

  /** -> { items: Lawyer[] } every lawyer regardless of verification status */
  lawyers: signal => (USE_MOCKS ? mock({ items: MOCK_LAWYERS }) : api.get(EP.admin.lawyers, { signal })),

  /** status: 'verified'|'pending'|'rejected' -> updated Lawyer */
  setLawyerStatus: (id, status) => {
    if (!USE_MOCKS) return api.put(EP.admin.lawyer(id), { verified: status })
    const lawyer = MOCK_LAWYERS.find(l => l.id === id)
    lawyer.verified = status
    return mock(lawyer, 300)
  },

  /** -> { items: AdminUser[] } */
  users: signal => (USE_MOCKS ? mock({ items: users }) : api.get(EP.admin.users, { signal })),

  /** status: 'active'|'suspended' -> updated AdminUser */
  setUserStatus: (id, status) => {
    if (!USE_MOCKS) return api.put(EP.admin.user(id), { status })
    const u = users.find(x => x.id === id)
    u.status = status
    return mock(u, 300)
  },

  /** -> { items: Booking[] } every booking on the platform */
  bookings: signal => (USE_MOCKS ? mock({ items: MOCK_BOOKINGS }) : api.get(EP.admin.bookings, { signal })),

  /** Marks a bank-transfer booking as verified once the funds are confirmed received. */
  markBookingPaid: id => {
    if (!USE_MOCKS) return api.post(EP.admin.bookingPaid(id))
    const booking = MOCK_BOOKINGS.find(b => b.id === id)
    booking.paymentStatus = 'paid'
    return mock(booking, 300)
  },
}
