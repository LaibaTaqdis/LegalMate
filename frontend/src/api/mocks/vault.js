// In-memory "database" used by vaultService while the vault service is on mock data (demo mode only).
const iso = daysAgo => new Date(Date.now() - daysAgo * 86400000).toISOString()

export const vaultDb = {
  items: [
    {
      id: 'vi_1', kind: 'answer', title: 'Can my landlord increase the rent during the contract?', favourite: true, noteCount: 1, tag: 'Property Law', risk: null, language: 'en',
      summary: 'In general, your landlord cannot increase the rent in the middle of a fixed-term rental contract unless the contract allows it or both parties agree.',
      savedAt: iso(2), updatedAt: iso(2), trashedAt: null, conversationId: null, sourceId: null, confidence: 87,
      content: {
        question: 'Can my landlord increase the rent during the contract?',
        answer: {
          language: 'en', lawTitle: 'What the law says', intro: ['In general, your landlord cannot increase the rent in the middle of a fixed-term rental contract unless the contract allows it or ', { b: 'both parties' }, ' agree. ', { cite: 1 }],
          law: ['The terms of a written rental agreement are binding on both the landlord and the tenant and cannot be changed except by mutual consent. ', { cite: 1 }],
          steps: [['Read your rental agreement for a rent increase clause.'], ['Reply in writing if the landlord asks for more rent. ', { cite: 1 }]],
          important: 'Do not stop paying rent without legal advice.', outro: '', followUps: [],
          sources: [{ id: 1, title: 'The Rent Act, 2009', section: 'Section 4 - Tenancy Agreement', type: 'Act', quote: '“The terms of a written tenancy agreement shall be binding on the landlord and the tenant.”', jurisdiction: 'Punjab', status: 'in_force', pages: 'p. 4', url: null, quoteVerified: true, note: null }],
          confidence: { score: 87 }, disclaimer: 'This is general legal information, not legal advice.',
        },
      },
    },
    {
      id: 'vi_2', kind: 'analysis', title: 'Rental Agreement.pdf', favourite: false, noteCount: 0, tag: 'Tenancy Agreement', risk: 'Medium', language: null,
      summary: 'A twelve month rental agreement. The landlord can end it on 30 days notice and the deposit terms are unclear.',
      savedAt: iso(5), updatedAt: iso(5), trashedAt: null, conversationId: null, sourceId: null, confidence: null, content: null,
    },
  ],
  notes: { vi_1: [{ id: 'vn_1', text: 'Ask the landlord for the notice in writing.', createdAt: iso(1) }] },
  activity: { vi_1: [{ action: 'noted', createdAt: iso(1) }, { action: 'saved', createdAt: iso(2) }] },
}

// part B: your own files (demo data)
export const vaultFilesDb = {
  storage: { usedBytes: 1_800_000, quotaBytes: 50 * 1024 * 1024 },
  folders: [{ id: 'fo_1', name: 'Property', color: '#fbbf24', fileCount: 1 }, { id: 'fo_2', name: 'Family', color: '#34d399', fileCount: 0 }],
  files: [
    { id: 'vf_1', name: 'Tenancy Agreement.pdf', fileType: 'pdf', category: 'Contracts', folderId: 'fo_1', folderName: 'Property', sizeBytes: 1_200_000, pages: 6,
      favourite: true, noteCount: 0, textStatus: 'ready', hasText: true, uploadedAt: iso(9), updatedAt: iso(9), trashedAt: null },
    { id: 'vf_2', name: 'Rent receipt.jpg', fileType: 'jpg', category: 'Personal', folderId: null, folderName: null, sizeBytes: 600_000, pages: 1,
      favourite: false, noteCount: 0, textStatus: 'ready', hasText: true, uploadedAt: iso(3), updatedAt: iso(3), trashedAt: null },
  ],
  notes: {},
  activity: {},
}
