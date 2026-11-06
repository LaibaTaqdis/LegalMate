// Mock data for the Find a Lawyer marketplace (search, profile, booking, payment). See BACKEND_API.md.
export const MOCK_LAWYERS = [
  {
    id: 'lw_Laiba', name: 'Laiba', verified: 'verified', title: 'Advocate High Court',
    specializations: ['Contract Law', 'Corporate Law', 'Startup Advisory'], city: 'Islamabad',
    fee: 3500, rating: 4.9, reviewCount: 128, experienceYears: 9,
    languages: ['Urdu', 'English'], modes: ['video', 'phone', 'in_person'],
    bio: 'Laiba advises freelancers and small businesses on service agreements, NDAs and dispute resolution, with a focus on protecting independent contractors under Pakistani contract law.',
    credentials: [{ label: 'LLB, Punjab University', value: '2015' }, { label: 'Bar Council License', value: 'PB-33421' }, { label: 'Registered with', value: 'Lahore High Court Bar' }],
    reviews: [
      { author: 'Bilal H.', rating: 5, text: 'Explained the liability clauses clearly and got our contract signed within a week.' },
      { author: 'Sana K.', rating: 5, text: 'Very responsive and practical advice for a first-time freelancer.' },
    ],
    availableDays: [1, 2, 3, 4, 5], slotTimes: ['9:00 AM', '11:30 AM', '2:00 PM', '4:00 PM'],
  },
  {
    id: 'lw_faisal', name: 'Faisal Khan', verified: 'verified', title: 'Advocate Supreme Court',
    specializations: ['Employment & Labour Law'], city: 'Islamabad',
    fee: 2800, rating: 4.6, reviewCount: 74, experienceYears: 6,
    languages: ['Urdu', 'English', 'Punjabi'], modes: ['video', 'in_person'],
    bio: 'Faisal represents employees in wrongful termination, unpaid wages and workplace harassment matters across Punjab and the capital.',
    credentials: [{ label: 'LLB, University of Punjab', value: '2018' }, { label: 'Bar Council License', value: 'PB-40021' }, { label: 'Registered with', value: 'Islamabad High Court Bar' }],
    reviews: [{ author: 'Usman T.', rating: 4, text: 'Helped me negotiate a fair severance package.' }],
    availableDays: [1, 3, 5], slotTimes: ['10:00 AM', '1:00 PM', '5:00 PM'],
  },
  {
    id: 'lw_sara', name: 'Sara Riaz', verified: 'pending', title: 'Advocate High Court',
    specializations: ['Startup & IP Advisory', 'Corporate Law'], city: 'Rawalpindi',
    fee: 4000, rating: 5.0, reviewCount: 12, experienceYears: 3,
    languages: ['Urdu', 'English'], modes: ['video', 'phone'],
    bio: 'Sara works with early-stage founders on incorporation, trademark filing and investor-facing agreements.',
    credentials: [{ label: 'LLB, Bahria University', value: '2021' }, { label: 'Bar Council License', value: 'PB-51290' }, { label: 'Registered with', value: 'Rawalpindi Bar Association' }],
    reviews: [{ author: 'Hina J.', rating: 5, text: 'Guided us through trademark registration end to end.' }],
    availableDays: [2, 3, 4], slotTimes: ['11:00 AM', '3:00 PM'],
  },
  {
    id: 'lw_bilal', name: 'Bilal Ahmed', verified: 'verified', title: 'Advocate District Courts',
    specializations: ['Family Law', 'Property Law'], city: 'Lahore',
    fee: 2000, rating: 4.7, reviewCount: 203, experienceYears: 14,
    languages: ['Urdu', 'English'], modes: ['phone', 'in_person'],
    bio: 'Bilal has handled family and property disputes for over a decade, with particular experience in inheritance and tenancy matters.',
    credentials: [{ label: 'LLB, Punjab University', value: '2010' }, { label: 'Bar Council License', value: 'PB-19042' }, { label: 'Registered with', value: 'Lahore Bar Association' }],
    reviews: [{ author: 'Kiran M.', rating: 5, text: 'Resolved our inheritance dispute patiently and clearly.' }],
    availableDays: [0, 1, 2, 3, 4], slotTimes: ['9:30 AM', '12:00 PM', '4:30 PM'],
  },
  {
    id: 'lw_hira', name: 'Hira Nadeem', verified: 'verified', title: 'Advocate High Court',
    specializations: ['Criminal Law'], city: 'Karachi',
    fee: 5000, rating: 4.8, reviewCount: 96, experienceYears: 11,
    languages: ['Urdu', 'English', 'Sindhi'], modes: ['video', 'phone', 'in_person'],
    bio: 'Hira defends clients in FIR quashing, bail applications and cybercrime cases across Sindh.',
    credentials: [{ label: 'LLB, University of Karachi', value: '2013' }, { label: 'Bar Council License', value: 'SB-27710' }, { label: 'Registered with', value: 'Sindh High Court Bar' }],
    reviews: [{ author: 'Owais R.', rating: 5, text: 'Got my bail application filed the same day.' }],
    availableDays: [1, 2, 4, 5], slotTimes: ['10:30 AM', '1:30 PM', '6:00 PM'],
  },
  {
    id: 'lw_zainab', name: 'Zainab Farooq', verified: 'verified', title: 'Advocate High Court',
    specializations: ['Family Law'], city: 'Lahore',
    fee: 1800, rating: 4.9, reviewCount: 156, experienceYears: 8,
    languages: ['Urdu', 'English'], modes: ['video', 'in_person'],
    bio: 'Zainab focuses on khula, custody and maintenance cases, with a client-first, low-conflict approach.',
    credentials: [{ label: 'LLB, LUMS', value: '2016' }, { label: 'Bar Council License', value: 'PB-35510' }, { label: 'Registered with', value: 'Lahore High Court Bar' }],
    reviews: [{ author: 'Mahnoor S.', rating: 5, text: 'Made a very difficult process feel manageable.' }],
    availableDays: [1, 2, 3, 4, 5, 6], slotTimes: ['9:00 AM', '11:00 AM', '3:00 PM'],
  },
]

/** Mutable in-memory store so bookings created on the client side stay visible to the lawyer/admin phases. */
export const MOCK_BOOKINGS = [
  {
    id: 'bkg_seed1', lawyerId: 'lw_Laiba', lawyerName: 'Laiba', clientId: 'usr_arfah', clientName: 'Arfah Rizwan',
    date: '2026-09-30', time: '11:30 AM', type: 'video', durationMin: 30, status: 'confirmed',
    paymentMethod: 'bank_transfer', paymentStatus: 'bank_pending_verification', fee: 3500, platformFee: 150, total: 3650,
    createdAt: '2026-09-26T09:00:00Z',
  },
  {
    id: 'bkg_seed2', lawyerId: 'lw_zainab', lawyerName: 'Zainab Farooq', clientId: 'usr_arfah', clientName: 'Arfah Rizwan',
    date: '2026-09-22', time: '9:00 AM', type: 'in_person', durationMin: 30, status: 'completed',
    paymentMethod: 'cash', paymentStatus: 'paid', fee: 1800, platformFee: 150, total: 1950,
    createdAt: '2026-09-18T09:00:00Z',
  },
  {
    id: 'bkg_seed3', lawyerId: 'lw_bilal', lawyerName: 'Bilal Ahmed', clientId: 'usr_hina', clientName: 'Hina Jamil',
    date: '2026-10-02', time: '4:30 PM', type: 'phone', durationMin: 30, status: 'confirmed',
    paymentMethod: 'cash', paymentStatus: 'cash_pending', fee: 2000, platformFee: 150, total: 2150,
    createdAt: '2026-09-27T14:00:00Z',
  },
]
