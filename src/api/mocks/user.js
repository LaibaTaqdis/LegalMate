export const MOCK_USER = {
  id: 'usr_arfah',
  name: 'Arfah Rizwan',
  firstName: 'Arfah',
  initials: 'AR',
  role: 'client',
  roleLabel: 'Citizen Account',
  email: 'Arfah.khan@example.com',
  phone: '300 1234567',
  phoneCountryCode: '+92',
  cnic: '35202-1234567-1',
  cnicVerified: true,
  city: 'Islamabad',
  address: 'House 12, Street 4, G-11/2, Islamabad',
  avatarUrl: null,
  preferredLanguage: 'en',
}

// A lawyer signing in sees their own listing (`lw_Laiba`, see mocks/marketplace.js) as "my profile" in the lawyer portal.
export const MOCK_USER_LAWYER = {
  id: 'usr_lawyer_Laiba',
  lawyerId: 'lw_Laiba',
  name: 'Laiba',
  firstName: 'Laiba',
  initials: 'AM',
  role: 'lawyer',
  roleLabel: 'Lawyer Account',
  email: 'Laiba.malik@example.com',
  phone: '321 4459081',
  phoneCountryCode: '+92',
  city: 'Islamabad',
  avatarUrl: null,
  preferredLanguage: 'en',
}

export const MOCK_USER_ADMIN = {
  id: 'usr_admin_Isha',
  name: 'Isha',
  firstName: 'Isha',
  initials: 'HI',
  role: 'admin',
  roleLabel: 'Admin Account',
  email: 'isha@legalmate.pk',
  phone: '300 9998877',
  phoneCountryCode: '+92',
  city: 'Islamabad',
  avatarUrl: null,
  preferredLanguage: 'en',
}

export const MOCK_TOKENS = { accessToken: 'mock-access-token', refreshToken: 'mock-refresh-token' }

export const MOCK_NOTIFICATIONS = {
  unreadCount: 3,
  items: [
    { id: 'ntf_1', type: 'deadline', title: 'Court Hearing - Civil Case', text: 'Hearing on 25 Sep at District Court, Islamabad.', createdAt: '2026-09-23T08:00:00Z', timeLabel: '2h ago', read: false, link: '/dashboard' },
    { id: 'ntf_2', type: 'analysis', title: 'Analysis complete', text: 'Tenancy Agreement.pdf has been analysed.', createdAt: '2026-09-23T05:00:00Z', timeLabel: '5h ago', read: false, link: '/documents/analysis/tenancy' },
    { id: 'ntf_3', type: 'chat', title: 'New answer ready', text: 'LegalMate answered your tenancy question.', createdAt: '2026-09-22T10:00:00Z', timeLabel: 'Yesterday', read: false, link: '/chat/tenant-rights' },
  ],
}

export const MOCK_SETTINGS = {
  security: { twoFactorEnabled: true, loginAlerts: true },
  sessions: [
    { id: 'ses_1', device: 'Windows · Chrome', deviceType: 'laptop', location: 'Islamabad, Pakistan', lastActiveLabel: 'Active now', current: true },
    { id: 'ses_2', device: 'Android · LegalMate App', deviceType: 'phone', location: 'Rawalpindi, Pakistan', lastActiveLabel: '2 hours ago', current: false },
    { id: 'ses_3', device: 'macOS · Safari', deviceType: 'desktop', location: 'Lahore, Pakistan', lastActiveLabel: '3 days ago', current: false },
  ],
  preferences: {
    notifications: { email: true, sms: false, whatsapp: true, deadlines: true, analysis: true, news: false },
    region: { language: 'English', province: 'Islamabad Capital Territory', dateFormat: 'DD/MM/YYYY', timezone: '(GMT+05:00) Pakistan Standard Time' },
    privacy: { saveChatHistory: true, shareUsageData: false, autoDeleteChats: '12 months' },
    appearance: { theme: 'light', density: 'Comfortable' },
    offline: { autoDownload: true },
  },
  integrations: [
    { provider: 'whatsapp', connected: true, account: '+92 300 1234567' },
    { provider: 'google', connected: false, account: null },
  ],
  storage: { usedBytes: 1.8e9, quotaBytes: 5e9 },
}
