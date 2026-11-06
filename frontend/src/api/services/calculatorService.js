import { api, download } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock, mockDownload, uid } from '../mock'

/**
 * Normalises a calculation result to the shape the page renders:
 *   { total?, text?, rows: [[label, value]], source: [title, reference], sourceUrl, assumptions, calculatedAt }
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

export const calculatorService = {
  /**
   * type: 'court' | 'stamp' | 'inheritance' | 'compensation' | 'limitation' | 'property'
   * inputs: plain values (money already parsed to numbers)
   * `mockCompute` is the local formula used while VITE_USE_MOCKS=true.
   */
  calculate: async (type, inputs, { mockCompute } = {}) =>
    normalize(USE_MOCKS ? await mock(mockCompute(inputs), 250) : await api.post(EP.calculators.calculate(type), { inputs })),

  /** Saves the calculation to the user's vault. -> { id } */
  save: ({ type, inputs, result }) => (USE_MOCKS ? mock({ id: uid('calc') }) : api.post(EP.calculators.saved, { type, inputs, result })),

  /** Downloads a PDF summary of a saved calculation. */
  downloadSummary: (id, filename = 'Calculation_Summary.pdf') => (USE_MOCKS ? mockDownload() : download(EP.calculators.summary(id), filename)),
}
