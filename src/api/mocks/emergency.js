// Mock data for GET /emergency/contacts and /emergency/personal-contacts. See BACKEND_API.md.
export const MOCK_HELPLINE = { label: 'LegalMate Legal Helpline', number: '+92 21 111 000 000', sub: 'Licensed advisors, available 24/7 for urgent legal questions.' }

export const MOCK_EMERGENCY_CATEGORIES = [
  {
    key: 'police', label: 'Police & Rescue', icon: 'shield',
    numbers: [
      { label: 'Police Helpline', number: '15' },
      { label: 'Rescue 1122 (Emergency Services)', number: '1122' },
    ],
  },
  {
    key: 'medical', label: 'Medical & Ambulance', icon: 'cross',
    numbers: [
      { label: 'Edhi Ambulance', number: '115' },
      { label: 'Chhipa Ambulance', number: '1020' },
    ],
  },
  {
    key: 'fire', label: 'Fire Brigade', icon: 'flame',
    numbers: [{ label: 'Fire Brigade', number: '16' }],
  },
  {
    key: 'women', label: 'Women & Child Safety', icon: 'users',
    numbers: [
      { label: "Women's Helpline", number: '1043' },
      { label: 'Child Protection & Welfare Bureau', number: '1121' },
    ],
  },
  {
    key: 'cyber', label: 'Cybercrime & Fraud', icon: 'shield-alert',
    numbers: [{ label: 'FIA Cybercrime Wing', number: '1991' }],
  },
  {
    key: 'highway', label: 'Roads & Highways', icon: 'car',
    numbers: [{ label: 'National Highways & Motorway Police', number: '130' }],
  },
]

export const MOCK_PERSONAL_CONTACTS = [
  { id: 'ec_1', name: 'Ahmed Raza', relation: 'Brother', phone: '+92 300 111 2233', primary: true },
  { id: 'ec_2', name: 'Sana Khalid', relation: 'Family Lawyer', phone: '+92 321 445 9081', primary: false },
]
