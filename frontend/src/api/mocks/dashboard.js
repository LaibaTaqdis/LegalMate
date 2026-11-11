// Shape of GET /dashboard (see BACKEND_API.md). Timestamps are ISO strings without a zone,
// so they render in the user's local time exactly as in the design.
export const MOCK_DASHBOARD = {
  activity: [
    { id: 'act_1', type: 'chat', title: 'Tenancy rights in Pakistan', subtitle: 'Chat with LegalMate', occurredAt: '2026-09-23T10:24:00', status: 'completed', link: '/chat/tenant-rights' },
    { id: 'act_2', type: 'document', title: 'Rental Agreement.pdf', subtitle: 'Document analysed', occurredAt: '2026-09-22T16:15:00', status: 'analysed', link: '/documents/analysis/tenancy' },
    { id: 'act_3', type: 'brief', title: 'Employment Dispute Brief', subtitle: 'Case brief generated', occurredAt: '2026-09-21T11:30:00', status: 'completed', link: '/case-briefs/ahmad-khan-vs-state' },
    { id: 'act_4', type: 'calculator', title: 'Notice Period Calculator', subtitle: 'Legal calculator used', occurredAt: '2026-09-20T15:12:00', status: 'viewed', link: '/calculator' },
    { id: 'act_5', type: 'resource', title: 'CNIC Verification Guide', subtitle: 'Viewed legal resource', occurredAt: '2026-09-18T09:45:00', status: 'viewed', link: '/vault' },
  ],
  vault: {
    usedBytes: 1.8e8,
    quotaBytes: 5e8,
    filesEnabled: true,
    fileCount: 6,
    savedCount: 4,
    breakdown: [
      { category: 'documents', label: 'Documents', bytes: 142e6 },
      { category: 'images', label: 'Photos', bytes: 38e6 },
    ],
  },
  resources: [
    { id: 'res_tenancy', category: 'property', title: 'Tenancy Laws in Pakistan', summary: 'Know your rights as a tenant or lan...', link: '/chat/tenant-rights' },
    { id: 'res_labour', category: 'labour', title: 'Labour Laws Guide', summary: 'A complete guide to employee rights.', link: '/chat/employment' },
    { id: 'res_family', category: 'family', title: 'Family Law Basics', summary: 'Understand marriage, divorce and custody.', link: '/chat/custody' },
  ],
  holidays: {
    verifiedOn: '2026-11-09',
    note: 'Demo data. With the backend connected, dates come from news reports of the courts notifications.',
    notYetAnnounced: '',
    courts: {},
    items: [
      { id: 'demo_h1', title: 'Quaid-e-Azam Day', kind: 'holiday', courtNames: ['All courts (public holiday)'], start: '2026-12-25', end: '2026-12-25', days: 1, status: 'notified', ongoing: false, daysUntil: 46, source: 'Demo', url: null },
      { id: 'demo_h2', title: 'Winter vacation (Lahore High Court)', kind: 'vacation', courtNames: ['Lahore High Court'], start: '2026-12-28', end: '2027-01-09', days: 13, status: 'expected', ongoing: false, daysUntil: 49, source: 'Demo', url: null },
    ],
  },
  riskPreview: [{ id: 'demo_a1', name: 'Rental Agreement.pdf', level: 'Medium', occurredAt: '2026-09-22T16:15:00', link: '/analysis/tenancy' }],
  forYou: {
    selected: 'citizen',
    verifiedOn: '2026-11-11',
    note: 'Demo cards. With the backend connected, each card opens a chat with a ready question, answered from the law library with its sources.',
    personas: [
      {
        key: 'young_adult', userType: 'Young adult', title: 'For young adults', subtitle: 'Know your rights: renting, first jobs, police and online safety.', checklist: [],
        calculators: [{ key: 'compensation', name: 'Compensation', why: 'What you may be owed when a job ends.', recommended: true }],
        topics: [
          { id: 'ya_rent', title: 'Renting a room or flat', text: 'What your landlord can and cannot do.', icon: 'house', action: 'ask', question: 'What are my rights as a tenant?', link: null, basis: ['Punjab Rented Premises Act, 2009'] },
          { id: 'ya_doc', title: 'Check an agreement before you sign', text: 'Upload a rental, job or loan agreement.', icon: 'file', action: 'analyse', question: null, link: '/analysis/new', basis: [] },
        ],
      },
      {
        key: 'citizen', userType: 'Citizen', title: 'Everyday legal questions', subtitle: 'The questions people ask most.', checklist: [],
        calculators: [{ key: 'limitation', name: 'Limitation Period', why: 'How long you have to act on a claim.', recommended: true }],
        topics: [
          { id: 'ct_rent', title: 'Tenant and landlord', text: 'Rent, eviction and the deposit.', icon: 'house', action: 'ask', question: 'What are the rights of a tenant and a landlord?', link: null, basis: ['Punjab Rented Premises Act, 2009'] },
          { id: 'ct_doc', title: 'Understand a legal document', text: 'Upload a notice, agreement or letter.', icon: 'file', action: 'analyse', question: null, link: '/analysis/new', basis: [] },
        ],
      },
    ],
  },
  whatsapp: { connected: true },
}
