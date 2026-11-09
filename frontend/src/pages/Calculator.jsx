import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle, ArrowRight, BadgeCheck, Calculator as CalcIcon, CheckCircle2, ChevronRight, Clock3, Download, FileText, House, Info,
  Landmark, Lightbulb, Loader2, RotateCcw, Scale, ShieldCheck, Users, Save
} from 'lucide-react'
import { Breadcrumb, Select } from '../components/common'
import { useUI } from '../components/UIContext'
import { PageSkeleton, QueryBoundary } from '../components/States'
import { useQuery } from '../hooks/useApi'
import { calculatorService } from '../api/services/calculatorService'
import { formatDate, formatDateTime } from '../utils/format'

// Every figure is worked out on the server (POST /calculators/:type/calculate) from the law and the published rates; the browser only
// collects the inputs. `meta` (GET /calculators) says which calculators exist, how far each can be trusted and why one is not offered.

const num = s => Number(String(s).replace(/[^\d.]/g, '')) || 0
const pkr = n => `PKR ${Math.round(n).toLocaleString('en-US')}`
const fmtInput = s => { const n = String(s).replace(/[^\d]/g, ''); return n ? Number(n).toLocaleString('en-US') : '' }
const YESNO = ['No', 'Yes']
const STATUS = ['Filer', 'Non-filer']

// Field `type`: select | money | number | date. `show(values)` hides a field; `optional` fields may be left empty.
const CALCS = {
  limitation: {
    icon: Clock3, name: 'Limitation Period', sub: 'Check legal time limits', title: 'Limitation Period Calculator', resultLabel: 'Last Date to File',
    desc: 'Find the last date to file a suit or appeal under the Limitation Act, 1908, moved to the next working day when the court is closed.',
    fields: meta => [
      { k: 'kind', label: 'Type of Proceeding', type: 'select', options: (meta.options.limitation || []).map(o => ({ value: o.key, label: o.label })), def: meta.options.limitation?.[0]?.key },
      { k: 'court', label: 'Court', type: 'select', options: Object.entries(meta.options.courts || {}).map(([value, label]) => ({ value, label })), def: 'lhc', help: 'Used for court holidays: if the last day is a Sunday or a public holiday, the next day the court is open counts (section 4).' },
      { k: 'date', label: 'Date the Time Starts Running', type: 'date', def: '', help: 'The date the cause of action arose, or the date of the decree or order being appealed. That day itself is not counted.' },
      { k: 'copyDays', label: 'Days to Get the Certified Copy', type: 'number', def: '0', optional: true, show: (v, m) => m.options.limitation?.find(o => o.key === v.kind)?.appeal, help: 'Days between applying for and receiving the copy of the decree or order. This time is not counted (section 12).' },
    ],
    note: 'The period is only as good as the start date. If time was spent in a wrong court in good faith, section 14 may exclude it: ask a lawyer.',
  },
  inheritance: {
    icon: Users, name: 'Inheritance Share', sub: 'Estimate inheritance distribution', title: 'Inheritance Share Calculator', resultLabel: 'Estate Distributed',
    desc: 'Fixed shares of a Muslim\'s estate under Hanafi law, as followed in Pakistan, for a spouse, children and parents.',
    fields: () => [
      { k: 'amount', label: 'Total Estate Value (PKR)', type: 'money', def: '', help: 'What is left after funeral costs, debts and any lawful will.' },
      { k: 'spouse', label: 'Surviving Spouse', type: 'select', options: ['Wife', 'Husband', 'None'], def: 'None' },
      { k: 'wives', label: 'Number of Wives', type: 'number', def: '1', show: v => v.spouse === 'Wife' },
      { k: 'sons', label: 'Number of Sons', type: 'number', def: '0', optional: true },
      { k: 'daughters', label: 'Number of Daughters', type: 'number', def: '0', optional: true },
      { k: 'father', label: 'Father Alive', type: 'select', options: YESNO, def: 'No' },
      { k: 'mother', label: 'Mother Alive', type: 'select', options: YESNO, def: 'No' },
    ],
    note: 'Grandchildren, brothers and sisters, grandparents and other relatives are not counted. A succession certificate or a court decides the real shares.',
  },
  compensation: {
    icon: ShieldCheck, name: 'Compensation', sub: 'Gratuity and notice pay', title: 'Compensation Calculator', resultLabel: 'Estimated Compensation',
    desc: 'Gratuity and pay in lieu of notice on termination of a workman, under Standing Order 12 of the Standing Orders Ordinance, 1968.',
    fields: () => [
      { k: 'salary', label: 'Last Monthly Wage (PKR)', type: 'money', def: '' },
      { k: 'years', label: 'Years of Service', type: 'number', def: '' },
      { k: 'months', label: 'Extra Months of Service', type: 'number', def: '0', optional: true, help: 'More than six extra months counts as another year.' },
      { k: 'reason', label: 'Reason for Separation', type: 'select', options: ['Termination without misconduct', 'Retrenchment', 'Resignation', 'Retirement'], def: 'Termination without misconduct' },
      { k: 'workman', label: 'Type of Workman', type: 'select', options: ['Permanent', 'Temporary / probationer'], def: 'Permanent' },
      { k: 'providentFund', label: 'Employer Provident Fund', type: 'select', options: YESNO, def: 'No', help: 'Yes if the employer also paid into a provident fund for you.' },
    ],
    note: 'This is the legal minimum for establishments covered by the Standing Orders. A contract or collective agreement can give more.',
  },
  stamp: {
    icon: FileText, name: 'Stamp Duty', sub: 'Punjab property sale deeds', title: 'Stamp Duty Calculator', resultLabel: 'Estimated Stamp Duty',
    desc: 'Stamp duty on the sale of immovable property in the Punjab.',
    fields: () => [
      { k: 'amount', label: 'Value in the Deed (PKR)', type: 'money', def: '', help: 'The registrar can test this against the district collector\'s valuation.' },
      { k: 'instrument', label: 'Type of Instrument', type: 'select', options: ['Sale / conveyance of immovable property'], def: 'Sale / conveyance of immovable property' },
    ],
    note: 'The Punjab rate was changed in April 2026 and is taken from news reports, not the official gazette. Check with the sub-registrar before paying.',
  },
  property: {
    icon: House, name: 'Property Transfer', sub: 'Duty and advance taxes', title: 'Property Transfer Calculator', resultLabel: 'Buyer\'s Total',
    desc: 'Stamp duty and federal advance taxes (sections 236C and 236K) on a property sale in the Punjab, for the buyer and the seller.',
    fields: () => [
      { k: 'amount', label: 'Property Value (PKR)', type: 'money', def: '' },
      { k: 'sellerStatus', label: 'Seller Tax Status', type: 'select', options: STATUS, def: 'Filer' },
      { k: 'buyerStatus', label: 'Buyer Tax Status', type: 'select', options: STATUS, def: 'Filer' },
    ],
    note: 'Tax rates for the year to June 2027 come from news and tax commentary, not the FBR text. "Filer" means on the FBR Active Taxpayers List.',
  },
}
const COURT_FEE = { icon: Landmark, name: 'Court Fee', sub: 'Not available', title: 'Court Fee Calculator' }

const initial = (key, meta) => Object.fromEntries(CALCS[key].fields(meta).map(f => [f.k, f.def ?? '']))
const visible = (key, meta, values) => CALCS[key].fields(meta).filter(f => !f.show || f.show(values, meta))

// Form values -> API inputs (money strings become numbers; hidden and empty optional fields are left out)
function toInputs(key, meta, values) {
  const out = {}
  for (const f of visible(key, meta, values)) {
    const raw = values[f.k]
    if (f.type === 'money' || f.type === 'number') { if (String(raw ?? '').trim() !== '') out[f.k] = num(raw) } else if (String(raw ?? '').trim() !== '') out[f.k] = raw
  }
  return out
}

const CONFIDENCE = {
  law: { Icon: BadgeCheck, cls: 'calc-conf-law', title: 'Based on the text of the law', text: 'Worked out from the law as it is in the law library and settled rules.' },
  reported: { Icon: AlertTriangle, cls: 'calc-conf-rep', title: 'Based on news reports: please verify', text: 'The official text could not be read, so the rates come from news and commentary.' },
}

export default function Calculator() {
  const query = useQuery(signal => calculatorService.list(signal), [])
  return <QueryBoundary query={query} skeleton={<PageSkeleton cards={3} rows={2} />}>{meta => <CalculatorPage meta={meta} />}</QueryBoundary>
}

function CalculatorPage({ meta }) {
  const navigate = useNavigate()
  const { toast } = useUI()
  const [key, setKey] = useState('limitation')
  const [values, setValues] = useState(() => initial('limitation', meta))
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [calculating, setCalculating] = useState(false)
  const [savedId, setSavedId] = useState(null)
  const [busy, setBusy] = useState(null)
  const unavailable = key === 'court' ? meta.unavailable?.find(u => u.key === 'court') || { reason: 'The court fee calculator is not available.' } : null
  const c = CALCS[key]
  const fields = useMemo(() => (c ? visible(key, meta, values) : []), [c, key, meta, values])
  const confidence = result ? CONFIDENCE[result.confidence] || CONFIDENCE.reported : null

  useEffect(() => { setResult(null); setSavedId(null); setError('') }, [key])

  const pick = k => { setKey(k); if (CALCS[k]) setValues(initial(k, meta)) }
  const calculate = async () => {
    const missing = fields.find(f => !f.optional && !String(values[f.k] ?? '').trim())
    if (missing) { setError(`Please enter ${missing.label.toLowerCase()}.`); return }
    setError(''); setCalculating(true); setSavedId(null)
    try {
      setResult(await calculatorService.calculate(key, toInputs(key, meta, values)))
    } catch (e) {
      setResult(null)
      setError((e.message || 'Could not calculate. Please check your inputs.').replace(/^[a-zA-Z]+: /, ''))
    } finally {
      setCalculating(false)
    }
  }
  const reset = () => { setValues(initial(key, meta)); setResult(null); setSavedId(null); setError('') }

  const ensureSaved = async () => {
    if (savedId) return savedId
    const { id } = await calculatorService.save({ type: key, inputs: toInputs(key, meta, values) })
    setSavedId(id)
    return id
  }
  const save = async () => {
    setBusy('save')
    try { await ensureSaved(); toast('Calculation saved to your Legal Vault') } catch (e) { toast(e.message, 'info') } finally { setBusy(null) }
  }
  const downloadSummary = async () => {
    setBusy('download')
    try { await calculatorService.downloadSummary(await ensureSaved(), `${c.title.replace(/\s+/g, '_')}_Summary.pdf`); toast('Downloading calculation summary (PDF)') } catch (e) { toast(e.message, 'info') } finally { setBusy(null) }
  }
  const setV = k => v => setValues(p => ({ ...p, [k]: v }))
  const main = result ? (result.text ?? pkr(result.total)) : '-'

  return (
    <div className="calc">
      <div className="page-head">
        <div>
          <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Legal Calculator' }]} />
          <h1 className="page-title">Legal Calculator</h1>
          <p className="page-sub">Work out limitation dates, inheritance shares, compensation and property costs.</p>
        </div>
        <div className="calc-tip"><Lightbulb size={24} /><p>Every result is worked out from the law or published rates and says how far it can be trusted{meta.verifiedOn ? ` (data checked on ${formatDate(meta.verifiedOn)})` : ''}.<br />For a real case, confirm with a qualified lawyer.</p></div>
      </div>

      <div className="calc-grid">
        <aside className="card calc-cats">
          <h2 className="cb-h2">Calculator Categories</h2>
          <ul>
            {Object.entries(CALCS).map(([k, v]) => (
              <li key={k}>
                <button className={key === k ? 'active' : ''} onClick={() => pick(k)}>
                  <v.icon size={28} strokeWidth={1.6} />
                  <span><b>{v.name}</b><small>{v.sub}</small></span>
                  {key === k && <ChevronRight size={20} />}
                </button>
              </li>
            ))}
            {(meta.unavailable || []).some(u => u.key === 'court') && (
              <li>
                <button className={`${key === 'court' ? 'active' : ''} calc-off`} onClick={() => pick('court')}>
                  <COURT_FEE.icon size={28} strokeWidth={1.6} />
                  <span><b>{COURT_FEE.name}</b><small>{COURT_FEE.sub}</small></span>
                  {key === 'court' && <ChevronRight size={20} />}
                </button>
              </li>
            )}
          </ul>
          <div className="calc-help">
            <div className="calc-help-head"><Scale size={32} strokeWidth={1.5} /><div><b>Not sure which calculator to use?</b><span>Ask LegalMate, it can explain the law behind each one.</span></div></div>
            <button className="btn btn-outline-navy btn-block" onClick={() => navigate('/chat')}>Ask LegalMate <ArrowRight size={17} /></button>
          </div>
        </aside>

        {unavailable ? (
          <section className="card calc-form calc-unavail">
            <div className="calc-form-head"><h2><COURT_FEE.icon size={32} strokeWidth={1.6} /> {COURT_FEE.title}</h2></div>
            <div className="calc-note"><Info size={22} fill="#13335b" color="#fff" /><p><b>Why there is no figure:</b> {unavailable.reason}</p></div>
            <p className="calc-unavail-text">The court fee is stated in the schedule to the Court Fees Act and in each province's amendments. Ask LegalMate which Act applies to your court, or check with the court's fee clerk.</p>
            <button className="btn btn-orange btn-lg" onClick={() => navigate('/chat')}>Ask LegalMate <ArrowRight size={17} /></button>
          </section>
        ) : (
          <section className="card calc-form">
            <div className="calc-form-head">
              <h2><c.icon size={32} strokeWidth={1.6} /> {c.title}</h2>
              <p>{c.desc}</p>
            </div>
            {fields.map(f => (
              <div key={f.k} className="field calc-field">
                <span className="field-label">{f.label}{!f.optional && <span className="req">*</span>}</span>
                {f.type === 'select' && <Select value={values[f.k]} onChange={setV(f.k)} options={f.options} />}
                {f.type === 'money' && <input className="input" inputMode="numeric" value={values[f.k]} onChange={e => setV(f.k)(fmtInput(e.target.value))} placeholder="0" />}
                {f.type === 'number' && <input className="input" type="number" min="0" value={values[f.k]} onChange={e => setV(f.k)(e.target.value)} />}
                {f.type === 'date' && <input className="input" type="date" value={values[f.k]} onChange={e => setV(f.k)(e.target.value)} />}
                {f.help && <small className="calc-help-text">{f.help}</small>}
              </div>
            ))}
            <div className="calc-note"><Info size={22} fill="#13335b" color="#fff" /><p><b>Note:</b> {c.note}</p></div>
            {error && <div className="calc-error" role="alert"><AlertTriangle size={18} /><p>{error}</p></div>}
            <div className="calc-btns">
              <button className="btn btn-orange btn-xl calc-go" onClick={calculate} disabled={calculating}>{calculating ? <Loader2 size={22} className="spin" /> : <CalcIcon size={22} />} Calculate</button>
              <button className="btn btn-ghost btn-xl calc-reset" onClick={reset}><RotateCcw size={20} /> Reset</button>
            </div>
          </section>
        )}

        <section className={`card calc-result ${calculating && result ? 'is-refreshing' : ''}`}>
          {unavailable ? (
            <div className="calc-empty"><AlertTriangle size={44} strokeWidth={1.4} /><b>No figure shown</b><p>A wrong court fee is worse than none, so this calculator stays off until its rates can be checked against an official source.</p></div>
          ) : !result && calculating ? <PageSkeleton cards={1} rows={1} /> : result ? (
            <>
              <div className="calc-res-head"><CheckCircle2 size={30} fill="#22a45a" color="#fff" /><div><b>Estimated Result</b><span>Calculated on {formatDateTime(result.calculatedAt)}</span></div></div>
              {confidence && (
                <div className={`calc-conf ${confidence.cls}`}><confidence.Icon size={20} /><div><b>{confidence.title}</b><span>{confidence.text}{result.verifiedOn ? ` Data checked on ${formatDate(result.verifiedOn)}.` : ''}</span></div></div>
              )}
              <p className="calc-res-label">{c.resultLabel}</p>
              <p className="calc-res-value">{main}</p>
              <div className="calc-break">
                <h3>Calculation Breakdown</h3>
                {result.rows.map(([a, b]) => <div key={a} className="calc-break-row"><span>{a}</span><span>{b}</span></div>)}
                <div className="calc-break-row calc-total"><span>{c.resultLabel}</span><span>{main}</span></div>
              </div>
              {result.notes?.length > 0 && (
                <>
                  <h3 className="calc-assume-title">Good to know</h3>
                  <ul className="calc-notes">{result.notes.map(n => <li key={n}>{n}</li>)}</ul>
                </>
              )}
              <div className="calc-source">
                <FileText size={24} />
                <div><b>Source</b><span>{result.source[0]}<br />{result.source[1]}</span></div>
                {result.sourceUrl && <a className="link small" href={result.sourceUrl} target="_blank" rel="noopener noreferrer">View Source <ArrowRight size={16} /></a>}
              </div>
              {result.assumptions?.length > 0 && (
                <>
                  <h3 className="calc-assume-title">Assumptions</h3>
                  <ol className="calc-assume">{result.assumptions.map(a => <li key={a}>{a}</li>)}</ol>
                </>
              )}
              <div className="calc-res-btns">
                <button className="btn btn-outline btn-lg" onClick={save} disabled={busy === 'save'}>{busy === 'save' ? <Loader2 size={19} className="spin" /> : <Save size={19} />} Save to Vault</button>
                <button className="btn btn-outline btn-lg" onClick={downloadSummary} disabled={busy === 'download'}>{busy === 'download' ? <Loader2 size={19} className="spin" /> : <Download size={19} />} Download Summary</button>
              </div>
            </>
          ) : (
            <div className="calc-empty"><CalcIcon size={44} strokeWidth={1.4} /><b>No result yet</b><p>Fill in the form and click Calculate.</p></div>
          )}
        </section>
      </div>
    </div>
  )
}
