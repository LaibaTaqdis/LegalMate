// Mock data for the Admin dashboard and management pages. See BACKEND_API.md.
export const MOCK_ADMIN_STATS = {
  totals: { users: 482, pendingLawyers: 1, activeBookings: 2, revenueMonth: 186500 },
  deltas: { users: '+8% this month', revenue: '+12% this month' },
  trend: [
    { day: 'Mon', bookings: 3 }, { day: 'Tue', bookings: 5 }, { day: 'Wed', bookings: 4 },
    { day: 'Thu', bookings: 7 }, { day: 'Fri', bookings: 6 }, { day: 'Sat', bookings: 2 }, { day: 'Sun', bookings: 1 },
  ],
  recentActivity: [
    { id: 'act_1', text: 'Sara Riaz applied to join as a verified lawyer', timeLabel: '2h ago' },
    { id: 'act_2', text: 'Arfah Rizwan booked a consultation with Laiba', timeLabel: '5h ago' },
    { id: 'act_3', text: 'Bilal Ahmed completed a consultation with Hina Jamil', timeLabel: 'Yesterday' },
    { id: 'act_4', text: 'New client account registered: Kiran Malik', timeLabel: 'Yesterday' },
  ],
}

export const MOCK_ADMIN_USERS = [
  { id: 'usr_arfah', name: 'Arfah Rizwan', email: 'arfah.khan@example.com', role: 'client', status: 'active', joinedAt: '2026-06-02' },
  { id: 'usr_hina', name: 'Hina Jamil', email: 'hina.jamil@example.com', role: 'client', status: 'active', joinedAt: '2026-07-14' },
  { id: 'usr_kiran', name: 'Kiran Malik', email: 'kiran.malik@example.com', role: 'client', status: 'active', joinedAt: '2026-09-27' },
  { id: 'usr_owais', name: 'Owais Rana', email: 'owais.rana@example.com', role: 'client', status: 'suspended', joinedAt: '2026-05-20' },
  { id: 'usr_lawyer_Laiba', name: 'Laiba', email: 'Laiba.malik@example.com', role: 'lawyer', status: 'active', joinedAt: '2026-03-11' },
  { id: 'usr_lawyer_faisal', name: 'Faisal Khan', email: 'faisal.khan@example.com', role: 'lawyer', status: 'active', joinedAt: '2026-04-02' },
  { id: 'usr_lawyer_sara', name: 'Sara Riaz', email: 'sara.riaz@example.com', role: 'lawyer', status: 'active', joinedAt: '2026-08-30' },
]
