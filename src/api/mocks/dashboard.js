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
    usedBytes: 1.8e9,
    quotaBytes: 5e9,
    breakdown: [
      { category: 'documents', label: 'Documents', bytes: 842e6 },
      { category: 'briefs', label: 'Case Briefs', bytes: 420e6 },
      { category: 'images', label: 'Images', bytes: 320e6 },
      { category: 'other', label: 'Other', bytes: 218e6 },
    ],
  },
  resources: [
    { id: 'res_tenancy', category: 'property', title: 'Tenancy Laws in Pakistan', summary: 'Know your rights as a tenant or lan...', link: '/chat/tenant-rights' },
    { id: 'res_labour', category: 'labour', title: 'Labour Laws Guide', summary: 'A complete guide to employee rights.', link: '/chat/employment' },
    { id: 'res_family', category: 'family', title: 'Family Law Basics', summary: 'Understand marriage, divorce and custody.', link: '/chat/custody' },
  ],
  deadlines: [
    { id: 'dl_1', title: 'Court Hearing - Civil Case', location: 'District Court, Islamabad', dueDate: '2026-09-25', daysLeft: 3 },
    { id: 'dl_2', title: 'Document Submission', location: 'Labour Tribunal', dueDate: '2026-10-10', daysLeft: 18 },
    { id: 'dl_3', title: 'Reply to Legal Notice', location: 'Regarding rental dispute', dueDate: '2026-10-15', daysLeft: 23 },
  ],
  whatsapp: { connected: true },
}
