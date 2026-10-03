// Shape of GET /analyses/:id (see BACKEND_API.md)
export const MOCK_ANALYSIS = {
  id: 'tenancy',
  status: 'completed', // queued | processing | completed | failed
  progress: 100,
  document: {
    id: 'tenancy', vaultDocumentId: 'tenancy', name: 'Tenancy Agreement.pdf', fileType: 'pdf', documentType: 'Tenancy Agreement',
    pages: 12, sizeBytes: 2.4 * 1024 * 1024, uploadedAt: '2026-09-22T10:24:00',
  },
  overallRisk: { level: 'Medium', note: 'Some important issues require attention.' },
  counts: { clauses: 8, deadlines: 2, missing: 3 },
  summary: 'This tenancy agreement is a fixed-term rental contract between the landlord and tenant for a period of 12 months, starting from 1st January 2026 to 31st December 2026. The monthly rent is PKR 45,000, with a security deposit of PKR 90,000. The agreement includes standard terms for rent payment, property use and maintenance. However, there are some clauses that may be unfavourable to the tenant, including a broad termination clause and additional charges for repairs. You should review the highlighted risks and consider seeking legal advice for negotiation.',
  clauses: [
    { id: 'c1', title: 'Tenancy Duration', reference: 'Clause 2.1', risk: 'Low', summary: 'Fixed term of 12 months.', detail: 'The tenancy runs from 1st January 2026 to 31st December 2026 with no automatic renewal. Renewal requires a fresh written agreement.' },
    { id: 'c2', title: 'Rent and Payment Terms', reference: 'Clause 3.1', risk: 'Low', summary: 'Monthly rent: PKR 45,000 (due by 5th).', detail: 'Rent is payable by bank transfer on or before the 5th of each month. A late fee of PKR 1,000 applies after a 7-day grace period.' },
    { id: 'c3', title: 'Security Deposit', reference: 'Clause 4.1', risk: 'Medium', summary: 'Deposit: PKR 90,000 (refundable with conditions).', detail: 'The deposit is refundable within 30 days of vacating, less deductions for damage. The clause does not define “normal wear and tear”.' },
    { id: 'c4', title: 'Termination by Landlord', reference: 'Clause 6.2', risk: 'High', summary: 'Broad rights to terminate with short notice.', detail: 'The landlord may terminate with 30 days’ notice without giving a specific reason, which is unfavourable to the tenant during a fixed term.' },
    { id: 'c5', title: 'Maintenance and Repairs', reference: 'Clause 7.1', risk: 'Medium', summary: 'Repairs may be charged to tenant in several cases.', detail: 'The tenant bears the cost of “all repairs arising from use”, which could include major structural repairs.' },
    { id: 'c6', title: 'Subletting', reference: 'Clause 8.1', risk: 'Low', summary: 'Subletting not allowed without written consent.', detail: 'Standard restriction; consent should not be unreasonably withheld.' },
    { id: 'c7', title: 'Utilities', reference: 'Clause 9.2', risk: 'Low', summary: 'Tenant pays electricity, gas and water bills.', detail: 'Bills must be paid on time and receipts shared with the landlord on request.' },
    { id: 'c8', title: 'Dispute Resolution', reference: 'Clause 12.1', risk: 'Medium', summary: 'Disputes referred to the Rent Controller, Islamabad.', detail: 'Consistent with the Rent Act; no arbitration clause is included.' },
  ],
  risks: [
    { id: 'r1', title: 'Early Termination Risk', description: 'Landlord can terminate with 30 days notice without specific reason.', level: 'High' },
    { id: 'r2', title: 'Repair Cost Liability', description: 'Tenant may be liable for major repairs under broad conditions.', level: 'Medium' },
    { id: 'r3', title: 'Non-refundable Charges', description: 'Some charges (e.g., administrative fees) may not be refundable.', level: 'Medium' },
    { id: 'r4', title: 'Deposit Deductions', description: '“Normal wear and tear” is not defined, allowing broad deductions.', level: 'Medium' },
    { id: 'r5', title: 'Late Payment Penalty', description: 'Late fee applies after a short grace period.', level: 'Low' },
  ],
  riskDistribution: { high: 2, medium: 4, low: 2 },
  obligations: ['Pay rent by the 5th of each month.', 'Pay all utility bills on time.', 'Keep the premises in good condition.', 'Give 30 days’ written notice before vacating.'],
  importantDates: ['1 Jan 2026 - Tenancy starts.', '31 Dec 2026 - Tenancy ends (renewal notice due 30 Nov 2026).'],
  missingInformation: ['Definition of “normal wear and tear”.', 'Inventory list of furniture and fixtures.', 'Signatures of two witnesses.'],
  citations: [
    { id: 'l1', title: 'The Rent Act, 2009', reference: 'Section 4 - Tenancy Agreement', type: 'Act', url: null },
    { id: 'l2', title: 'Transfer of Property Act, 1882', reference: 'Section 105 - Lease of Immovable Property', type: 'Act', url: null },
    { id: 'l3', title: 'Superior Courts Judgment', reference: 'PLD 2018 SC 123', type: 'Judgment', url: null },
  ],
  recommendedActions: ['Consider negotiating the termination clause.', 'Clarify repair and maintenance responsibilities.', 'Ensure all payments and deposits are properly documented.'],
}

// Upload queue shown on first visit in mock mode (matches the design).
export const MOCK_UPLOAD_QUEUE = [
  { key: 'demo1', name: 'Rental_Agreement.pdf', sizeBytes: 2.4 * 1024 * 1024, type: 'pdf', progress: 100, status: 'done', documentId: 'tenancy' },
  { key: 'demo2', name: 'Employment_Notice.docx', sizeBytes: 1.1 * 1024 * 1024, type: 'docx', progress: 65, status: 'uploading', documentId: null },
]
