// In-memory "database" used by vaultService while VITE_USE_MOCKS=true.
const MB = 1024 * 1024

export const vaultDb = {
  folders: [
    { id: 'fld_employment', name: 'Employment', color: '#3b82f6', fileCount: 4 },
    { id: 'fld_property', name: 'Property', color: '#fbbf24', fileCount: 6 },
    { id: 'fld_family', name: 'Family', color: '#8b5cf6', fileCount: 3 },
    { id: 'fld_business', name: 'Business', color: '#22c55e', fileCount: 5 },
    { id: 'fld_personal', name: 'Personal', color: '#f43f5e', fileCount: 2 },
  ],
  documents: [
    { id: 'tenancy', name: 'Tenancy Agreement.pdf', fileType: 'pdf', category: 'Contracts', folderId: 'fld_property', updatedAt: '2026-09-22T10:24:00', sizeBytes: 2.4 * MB, status: 'analysed', favourite: true, pages: 12, verified: true, tags: ['Tenancy', 'Property', 'Islamabad'], analysisId: 'tenancy' },
    { id: 'employment', name: 'Employment Notice.docx', fileType: 'docx', category: 'Notices', folderId: 'fld_employment', updatedAt: '2026-09-20T09:00:00', sizeBytes: 1.1 * MB, status: 'analysed', favourite: false, pages: 3, verified: true, tags: ['Employment'] },
    { id: 'sale-deed', name: 'Property Sale Deed.pdf', fileType: 'pdf', category: 'Property', folderId: 'fld_property', updatedAt: '2026-09-18T09:00:00', sizeBytes: 3.2 * MB, status: 'secure', favourite: false, pages: 8, verified: true, tags: ['Property'] },
    { id: 'rent-record', name: 'Monthly Rent Record.xlsx', fileType: 'xlsx', category: 'Personal', folderId: 'fld_personal', updatedAt: '2026-09-15T09:00:00', sizeBytes: 842 * 1024, status: 'secure', favourite: false, pages: 1, verified: false, tags: [] },
    { id: 'judgment', name: 'Court Judgment.pdf', fileType: 'pdf', category: 'Court Documents', folderId: 'fld_family', updatedAt: '2026-09-12T09:00:00', sizeBytes: 1.8 * MB, status: 'analysed', favourite: true, pages: 14, verified: true, tags: ['Court'] },
    { id: 'brief', name: 'Case Brief - Ali vs State.docx', fileType: 'docx', category: 'Case Briefs', folderId: 'fld_business', updatedAt: '2026-09-10T09:00:00', sizeBytes: 1.3 * MB, status: 'analysed', favourite: false, pages: 6, verified: true, tags: ['Criminal'] },
    { id: 'cnic', name: 'CNIC Copy.jpg', fileType: 'jpg', category: 'Personal', folderId: 'fld_personal', updatedAt: '2026-09-08T09:00:00', sizeBytes: 512 * MB, status: 'secure', favourite: false, pages: 1, verified: true, tags: ['Identity'] },
    { id: 'notice', name: 'Legal Notice.pdf', fileType: 'pdf', category: 'Notices', folderId: 'fld_property', updatedAt: '2026-09-05T09:00:00', sizeBytes: 1.1 * MB, status: 'analysed', favourite: false, pages: 2, verified: true, tags: ['Notice'] },
    { id: 'maintenance', name: 'Maintenance Costs.xlsx', fileType: 'xlsx', category: 'Family', folderId: 'fld_family', updatedAt: '2026-09-01T09:00:00', sizeBytes: 620 * 1024, status: 'secure', favourite: false, pages: 1, verified: false, tags: [] },
  ],
  trash: [],
  // Counts shown in the "My Files" list (the design's vault holds 24 files; only 9 are listed above).
  counts: { all: 24, Contracts: 6, Notices: 4, 'Court Documents': 5, 'Case Briefs': 3, shared: 2, favourites: 4, trash: 1 },
  totalDocuments: 19,
  storage: { usedBytes: 1.8e9, quotaBytes: 5e9 },
  notes: {
    tenancy: [
      { id: 'n1', text: 'Check if 30-day termination applies during fixed term.', createdAt: '2026-09-22T10:40:00' },
      { id: 'n2', text: 'Ask landlord about deposit refund timeline.', createdAt: '2026-09-22T10:45:00' },
      { id: 'n3', text: 'Rent due by 5th - set a reminder.', createdAt: '2026-09-22T11:02:00' },
    ],
  },
  activity: [
    { id: 'a1', type: 'analysed', text: 'Analysis completed', createdAt: '2026-09-22T10:26:00' },
    { id: 'a2', type: 'verified', text: 'Document verified', createdAt: '2026-09-22T10:25:00' },
    { id: 'a3', type: 'viewed', text: 'Viewed by you', createdAt: '2026-09-22T10:25:00' },
    { id: 'a4', type: 'uploaded', text: 'Uploaded to Property folder', createdAt: '2026-09-22T10:24:00' },
  ],
}
