// Shapes of GET /case-briefs/draft and GET /case-briefs/:id (see BACKEND_API.md)

export const COURTS = ['Sessions Court, Islamabad', 'Civil Court, Lahore', 'High Court, Islamabad', 'High Court, Lahore', 'District Court, Karachi', 'Supreme Court of Pakistan']

export const MOCK_DRAFT = {
  id: 'draft_1',
  title: 'Ahmad Khan vs State',
  court: 'Sessions Court, Islamabad',
  caseNumber: 'Criminal Appeal No. 123/2026',
  parties: 'Ahmad Khan (Appellant) vs State (Respondent)',
  filingDate: '2026-03-12',
  nextHearingDate: '2026-10-25',
  facts: 'The appellant was charged under Section 379 PPC for alleged theft. He maintains his innocence and claims false implication. The incident occurred on 10 March 2026 at a commercial plaza in Islamabad.',
  issues: 'Whether the evidence is sufficient to prove theft under Section 379 PPC?\nWhether there was a violation of due process during arrest and investigation?',
  briefType: null, // 'summary' | 'lawyer' | 'personal'
  attachments: [{ id: 'att_fir', name: 'FIR_Copy.pdf', sizeBytes: 2.4 * 1024 * 1024, fileType: 'pdf' }],
  savedAt: new Date(Date.now() - 2 * 60000).toISOString(),
}

// Section content uses simple blocks: { type: 'p', text } | { type: 'kv', label, text } | { type: 'ol'|'ul', items }
export const MOCK_BRIEF = {
  id: 'ahmad-khan-vs-state',
  status: 'completed', // generating | completed | failed
  title: 'Ahmad Khan vs State',
  caseNumber: 'Criminal Appeal No. 123/2026',
  court: 'Sessions Court, Islamabad',
  briefType: 'summary',
  createdAt: '2026-09-22T10:24:00',
  updatedAt: '2026-09-22T11:02:00',
  pages: 8,
  sizeBytes: 1.2 * 1024 * 1024,
  nextHearing: { date: '2026-10-25', court: 'Sessions Court, Islamabad' },
  sections: [
    { number: 'I.', title: 'Case Title', blocks: [{ type: 'p', text: 'Ahmad Khan vs State' }] },
    { number: 'II.', title: 'Parties', blocks: [{ type: 'kv', label: 'Appellant', text: 'Ahmad Khan' }, { type: 'kv', label: 'Respondent', text: 'State' }] },
    { number: 'III.', title: 'Facts', blocks: [{ type: 'p', text: 'The appellant was charged under Section 379 PPC for alleged theft. He maintains his innocence and claims false implication. The incident occurred on 10 March 2026 at a commercial plaza in Islamabad.' }] },
    { number: 'IV.', title: 'Issues', blocks: [{ type: 'ol', items: ['Whether the evidence is sufficient to prove theft under Section 379 PPC?', 'Whether there was a violation of due process during arrest and investigation?'] }] },
    { number: 'V.', title: 'Applicable Law', blocks: [{ type: 'ul', items: ['Section 379 PPC (Punishment for theft)', 'Section 342 CrPC (Examination of the accused)', 'Relevant case law on circumstantial evidence'] }] },
    { number: 'VI.', title: 'Arguments', blocks: [
      { type: 'kv', label: "Appellant's Arguments", text: 'The prosecution relies solely on circumstantial evidence; no recovery was made from the appellant and the CCTV footage was not produced before the trial court.' },
      { type: 'kv', label: "Respondent's Arguments", text: "The complainant identified the appellant and the timeline supports the prosecution's version." },
    ] },
    { number: 'VII.', title: 'Evidence', blocks: [{ type: 'ul', items: ['FIR No. 214/2026, Police Station Kohsar', 'Statement of the complainant under Section 161 CrPC', 'Site plan and recovery memo'] }] },
    { number: 'VIII.', title: 'Important Dates', blocks: [{ type: 'ul', items: ['Incident: 10 March 2026', 'Filing of appeal: 12 March 2026', 'Next hearing: 25 October 2026'] }] },
  ],
  relatedDocuments: [
    { id: 'tenancy', name: 'FIR Copy.pdf', sizeBytes: 2.4 * 1024 * 1024, fileType: 'pdf' },
    { id: 'judgment', name: 'Case Diary.pdf', sizeBytes: 1.8 * 1024 * 1024, fileType: 'docx' },
    { id: 'notice', name: 'Court Order.pdf', sizeBytes: 1.1 * 1024 * 1024, fileType: 'xlsx' },
  ],
  sharing: {
    invites: [
      { id: 'inv_1', contact: 'sara.ali@example.com', permission: 'View' },
      { id: 'inv_2', contact: 'm.razak@lawfirm.pk', permission: 'Edit' },
    ],
    link: { enabled: true, url: 'https://legalmate.pk/s/brief/AK-2026-9f3k2', expiresIn: '7 days', requirePassword: false },
  },
}
