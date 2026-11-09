import { api, download } from '../client'
import { isMock } from '../config'
import { EP } from '../endpoints'
import { mock, mockDownload, uid } from '../mock'

const MOCK = () => isMock('calculators')

/**
 * Normalises a calculation result to the shape the page renders:
 *   { total?, text?, rows: [[label, value]], source: [title, reference], sourceUrl, assumptions, notes, confidence: 'law'|'reported', verifiedOn, calculatedAt }
 * The API returns rows as [{ label, value }] and source as { title, reference, url }.
 */
function normalize(r) {
  return {
    ...r,
    rows: (r.rows || []).map(x => (Array.isArray(x) ? x : [x.label, x.value])),
    source: Array.isArray(r.source) ? r.source : [r.source?.title, r.source?.reference],
    sourceUrl: r.source?.url || null,
    calculatedAt: r.calculatedAt || new Date().toISOString(),
  }
}

// Demo mode has no rules engine: it says so instead of showing invented numbers.
const demoResult = type => ({
  type, text: 'Demo', confidence: 'reported', verifiedOn: null,
  rows: [{ label: 'Demo mode', value: 'Connect the backend (add "calculators" to VITE_REAL_SERVICES) for real figures' }],
  notes: ['Calculations are worked out on the server from the law and official rates. Nothing is calculated in the browser.'],
  source: { title: 'LegalMate demo', reference: 'No real rule was applied', url: null },
})
const DEMO_META = {
  verifiedOn: null,
  items: ['limitation', 'inheritance', 'compensation', 'stamp', 'property'].map(key => ({ key, confidence: 'reported' })),
  unavailable: [{ key: 'court', name: 'Court Fee', reason: 'Court fee scales differ by province and could not be verified, so no figure is shown.' }],
  options: {
    limitation: [{ key: 'residuary', label: 'Any other suit (6 years)', appeal: false }, { key: 'appeal_district', label: 'Civil appeal to the District Judge (30 days)', appeal: true }],
    courts: { lhc: 'Lahore High Court / Punjab courts', ihc: 'Islamabad High Court / ICT courts', sc: 'Supreme Court of Pakistan', fcc: 'Federal Constitutional Court' },
  },
}
const DEMO_HOLIDAYS = {
  verifiedOn: null, note: 'Demo data.', notYetAnnounced: '', courts: {},
  items: [{ id: 'demo_1', title: 'Quaid-e-Azam Day', kind: 'holiday', courtNames: ['All courts (public holiday)'], start: '2026-12-25', end: '2026-12-25', days: 1, status: 'notified', ongoing: false, daysUntil: 46, source: 'Demo', url: null }],
}

export const calculatorService = {
  /** -> { verifiedOn, items: [{ key, name, confidence }], unavailable: [{ key, name, reason }], options: { limitation: [{ key, label, appeal }], courts: { key: name } } } */
  list: signal => (MOCK() ? mock(DEMO_META, 150) : api.get(EP.calculators.list, { signal })),

  /** type: 'limitation' | 'inheritance' | 'compensation' | 'stamp' | 'property'. inputs: plain values (money already parsed to numbers). Worked out on the server. */
  calculate: async (type, inputs) => normalize(MOCK() ? await mock(demoResult(type), 250) : await api.post(EP.calculators.calculate(type), { inputs })),

  /** Saves the calculation to the user's Legal Vault (the server works it out again from the inputs). -> { id } */
  save: ({ type, inputs }) => (MOCK() ? mock({ id: uid('calc') }) : api.post(EP.calculators.saved, { type, inputs })),

  /** Downloads a PDF summary of a saved calculation. */
  downloadSummary: (id, filename = 'Calculation_Summary.pdf') => (MOCK() ? mockDownload() : download(EP.calculators.summary(id), filename)),

  /** Court holidays and vacations. params: { limit, court, all } -> { items, verifiedOn, note, notYetAnnounced, courts } */
  holidays: (params, signal) => (MOCK() ? mock(DEMO_HOLIDAYS, 150) : api.get(EP.calendar.courtHolidays, { query: params, signal })),
}
