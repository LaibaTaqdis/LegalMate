import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, Calculator as CalcIcon, CheckCircle2, ChevronRight, Clock3, Download, FileText, House, Info,
  Landmark, Lightbulb, Loader2, RotateCcw, Scale, ShieldCheck, Users, Save
} from 'lucide-react'
import { Breadcrumb, Select } from '../components/common'
import { useUI } from '../components/UIContext'
import { PageSkeleton } from '../components/States'
import { calculatorService } from '../api/services/calculatorService'
import { formatDateTime } from '../utils/format'

// Field definitions drive the form. `compute` is the local formula used only in mock mode;
// with a backend the result comes from POST /calculators/:type/calculate.

const PROVINCES = ['Punjab', 'Sindh', 'Khyber Pakhtunkhwa', 'Balochistan', 'Islamabad Capital Territory']
const pkr = n => `PKR ${Math.round(n).toLocaleString('en-US')}`
const num = s => Number(String(s).replace(/[^\d.]/g, '')) || 0
const fmtInput = s => { const n = String(s).replace(/[^\d]/g, ''); return n ? Number(n).toLocaleString('en-US') : '' }

const CALCS = {
  court: {
    icon: Landmark, name: 'Court Fee', sub: 'Estimate court filing fees', title: 'Court Fee Calculator',
    desc: 'Estimate the court fee for filing a case in civil courts based on the value of the claim and jurisdiction.',
    fields: [
      { k: 'province', label: 'Province / Jurisdiction', type: 'select', options: PROVINCES, def: 'Punjab' },
      { k: 'caseType', label: 'Type of Case', type: 'select', options: ['Civil Suit (Money Claim)', 'Suit for Declaration', 'Suit for Possession', 'Family Suit', 'Rent Case'], def: 'Civil Suit (Money Claim)' },
      { k: 'amount', label: 'Claim Amount (PKR)', type: 'money', def: '1,000,000', help: 'Enter the total value of your claim in Pakistani Rupees.' },
    ],
    note: 'Court fees may vary based on court, case type and latest government notifications. This is an estimate only.',
    resultLabel: 'Estimated Court Fee',
    compute: v => {
      const rates = { 'Punjab': 2.5, 'Sindh': 2.5, 'Khyber Pakhtunkhwa': 2.25, 'Balochistan': 2, 'Islamabad Capital Territory': 2.5 }
      const flat = { 'Family Suit': 25, 'Rent Case': 500 }
      const amount = num(v.amount)
      const rate = rates[v.province]
      if (flat[v.caseType] !== undefined) {
        return { total: flat[v.caseType], rows: [['Claim Amount', pkr(amount)], ['Case Type', v.caseType], ['Fixed Court Fee', pkr(flat[v.caseType])]], source: ['Court Fees Act, 1870 (As Amended)', 'Schedule II - Fixed Fees'] }
      }
      const gross = (amount * rate) / 100
      const total = Math.min(50000, Math.max(500, gross - 500))
      return {
        total,
        rows: [['Claim Amount', pkr(amount)], [`Applicable Rate (${rate}%)`, pkr(gross)], ['Minimum Fee', pkr(500)], ['Maximum Fee', pkr(50000)]],
        source: ['Court Fees Act, 1870 (As Amended)', 'Schedule I - Article 1A (Civil Suits)'],
        assumptions: ['Standard civil court fee structure applies.', 'No additional fees (process fee, summons, etc.) included.', `Based on current government rates for ${v.province}.`, 'This is an estimate and may vary by court.'],
      }
    },
  },
  stamp: {
    icon: FileText, name: 'Stamp Duty', sub: 'Calculate stamp duty charges', title: 'Stamp Duty Calculator',
    desc: 'Estimate stamp duty payable on property transfers, sale deeds and agreements.',
    fields: [
      { k: 'province', label: 'Province / Jurisdiction', type: 'select', options: PROVINCES, def: 'Punjab' },
      { k: 'instrument', label: 'Type of Instrument', type: 'select', options: ['Sale Deed', 'Gift Deed', 'Lease Agreement', 'Power of Attorney'], def: 'Sale Deed' },
      { k: 'amount', label: 'Property / Instrument Value (PKR)', type: 'money', def: '5,000,000', help: 'Use the DC rate or FBR valuation, whichever is higher.' },
    ],
    note: 'Stamp duty rates are notified by provincial governments and change periodically.',
    resultLabel: 'Estimated Stamp Duty',
    compute: v => {
      const rate = { 'Sale Deed': 1, 'Gift Deed': 1, 'Lease Agreement': 0.5, 'Power of Attorney': 0 }[v.instrument]
      const amount = num(v.amount)
      const total = v.instrument === 'Power of Attorney' ? 1200 : (amount * rate) / 100
      return { total, rows: [['Instrument Value', pkr(amount)], ['Instrument', v.instrument], [`Stamp Duty Rate (${rate}%)`, pkr(total)]], source: ['Stamp Act, 1899 (As Amended)', `Schedule I - ${v.province}`] }
    },
  },
  inheritance: {
    icon: Users, name: 'Inheritance Share', sub: 'Estimate inheritance distribution', title: 'Inheritance Share Calculator',
    desc: 'Estimate the share of each heir under Islamic law of succession as applied in Pakistan.',
    fields: [
      { k: 'amount', label: 'Total Estate Value (PKR)', type: 'money', def: '12,000,000', help: 'After paying debts and funeral expenses.' },
      { k: 'spouse', label: 'Surviving Spouse', type: 'select', options: ['Wife', 'Husband', 'None'], def: 'Wife' },
      { k: 'sons', label: 'Number of Sons', type: 'number', def: '2' },
      { k: 'daughters', label: 'Number of Daughters', type: 'number', def: '1' },
    ],
    note: 'Actual shares depend on all surviving heirs (parents, siblings, etc.). Consult a lawyer for a succession certificate.',
    resultLabel: 'Estate Distributed',
    compute: v => {
      const estate = num(v.amount)
      const sons = num(v.sons), daughters = num(v.daughters)
      const hasKids = sons + daughters > 0
      const spouseShare = v.spouse === 'Wife' ? (hasKids ? 1 / 8 : 1 / 4) : v.spouse === 'Husband' ? (hasKids ? 1 / 4 : 1 / 2) : 0
      const rest = estate * (1 - spouseShare)
      const units = sons * 2 + daughters || 1
      const rows = [['Total Estate', pkr(estate)]]
      if (spouseShare) rows.push([`${v.spouse} (${spouseShare === 1 / 8 ? '1/8' : spouseShare === 1 / 4 ? '1/4' : '1/2'})`, pkr(estate * spouseShare)])
      if (sons) rows.push([`Each Son (${sons})`, pkr((rest / units) * 2)])
      if (daughters) rows.push([`Each Daughter (${daughters})`, pkr(rest / units)])
      return { total: estate, rows, source: ['Muslim Family Laws Ordinance, 1961', 'Islamic Law of Succession (Faraid)'] }
    },
  },
  compensation: {
    icon: ShieldCheck, name: 'Compensation', sub: 'Estimate compensation amounts', title: 'Compensation Calculator',
    desc: 'Estimate gratuity or compensation payable on termination of employment.',
    fields: [
      { k: 'salary', label: 'Last Monthly Wage (PKR)', type: 'money', def: '85,000' },
      { k: 'years', label: 'Years of Service', type: 'number', def: '4' },
      { k: 'reason', label: 'Reason for Separation', type: 'select', options: ['Termination without cause', 'Retrenchment', 'Resignation', 'Retirement'], def: 'Termination without cause' },
    ],
    note: 'Gratuity is generally 30 days’ wages for every completed year of service for eligible workers.',
    resultLabel: 'Estimated Compensation',
    compute: v => {
      const w = num(v.salary), y = num(v.years)
      const gratuity = w * y
      const notice = v.reason === 'Resignation' || v.reason === 'Retirement' ? 0 : w
      return { total: gratuity + notice, rows: [['Monthly Wage', pkr(w)], [`Gratuity (${y} years × 30 days)`, pkr(gratuity)], ['Notice Pay in Lieu', pkr(notice)]], source: ['Standing Orders Ordinance, 1968', 'Standing Order 12 - Termination'] }
    },
  },
  limitation: {
    icon: Clock3, name: 'Limitation Period', sub: 'Check legal time limits', title: 'Limitation Period Calculator',
    desc: 'Find the last date to file a suit or appeal under the Limitation Act, 1908.',
    fields: [
      { k: 'kind', label: 'Type of Proceeding', type: 'select', options: ['Suit for recovery of money (3 years)', 'Appeal from decree (90 days)', 'Suit for possession of immovable property (12 years)', 'Revision petition (90 days)'], def: 'Suit for recovery of money (3 years)' },
      { k: 'date', label: 'Date Cause of Action Arose', type: 'date', def: '2026-03-10' },
    ],
    note: 'Time spent in bona fide proceedings in a wrong court may be excluded under Section 14.',
    resultLabel: 'Last Date to File',
    compute: v => {
      const d = new Date(v.date || Date.now())
      const k = v.kind
      if (k.includes('3 years')) d.setFullYear(d.getFullYear() + 3)
      else if (k.includes('12 years')) d.setFullYear(d.getFullYear() + 12)
      else d.setDate(d.getDate() + 90)
      const days = Math.ceil((d - new Date()) / 86400000)
      return { text: d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }), rows: [['Proceeding', k.split(' (')[0]], ['Limitation Period', k.match(/\((.*)\)/)[1]], ['Days Remaining', days > 0 ? `${days} days` : 'Expired']], source: ['Limitation Act, 1908', 'First Schedule'] }
    },
  },
  property: {
    icon: House, name: 'Property Transfer', sub: 'Calculate property transfer costs', title: 'Property Transfer Calculator',
    desc: 'Estimate the total government charges payable when transferring property.',
    fields: [
      { k: 'province', label: 'Province / Jurisdiction', type: 'select', options: PROVINCES, def: 'Punjab' },
      { k: 'amount', label: 'Property Value (PKR)', type: 'money', def: '10,000,000' },
      { k: 'filer', label: 'Tax Status', type: 'select', options: ['Filer', 'Non-filer'], def: 'Filer' },
    ],
    note: 'Advance tax rates under Sections 236C/236K differ for filers and non-filers.',
    resultLabel: 'Estimated Transfer Cost',
    compute: v => {
      const a = num(v.amount)
      const stamp = a * 0.01, cvt = a * 0.02, tmaFee = a * 0.01
      const adv = a * (v.filer === 'Filer' ? 0.03 : 0.105)
      return { total: stamp + cvt + tmaFee + adv, rows: [['Property Value', pkr(a)], ['Stamp Duty (1%)', pkr(stamp)], ['Capital Value Tax (2%)', pkr(cvt)], ['TMA / Registration (1%)', pkr(tmaFee)], [`Advance Tax (${v.filer})`, pkr(adv)]], source: ['Income Tax Ordinance, 2001', 'Sections 236C & 236K'] }
    },
  },
}

const initial = key => Object.fromEntries(CALCS[key].fields.map(f => [f.k, f.def]))

// Form values -> API inputs (money strings become numbers, number fields become numbers)
const toInputs = (key, values) => Object.fromEntries(CALCS[key].fields.map(f => [f.k, f.type === 'money' || f.type === 'number' ? num(values[f.k]) : values[f.k]]))

export default function Calculator() {
  const navigate = useNavigate()
  const { toast } = useUI()
  const [key, setKey] = useState('court')
  const [values, setValues] = useState(initial('court'))
  const [result, setResult] = useState(null)
  const [calculating, setCalculating] = useState(false)
  const [savedId, setSavedId] = useState(null)
  const [busy, setBusy] = useState(null)
  const c = CALCS[key]
  const calcAt = result ? formatDateTime(result.calculatedAt) : ''

  const run = async (k, v) => {
    setCalculating(true)
    setSavedId(null)
    try {
      setResult(await calculatorService.calculate(k, toInputs(k, v), { mockCompute: CALCS[k].compute }))
    } catch (e) {
      toast(e.message || 'Could not calculate. Please check your inputs.', 'info')
    } finally {
      setCalculating(false)
    }
  }

  // Show the default estimate on first load, as in the design.
  useEffect(() => { run('court', initial('court')) }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const pick = k => { setKey(k); const v = initial(k); setValues(v); run(k, v) }
  const calculate = () => {
    const missing = c.fields.find(f => !String(values[f.k] ?? '').trim())
    if (missing) return toast(`Please enter ${missing.label.toLowerCase()}`, 'info')
    run(key, values)
  }
  const reset = () => { const v = Object.fromEntries(c.fields.map(f => [f.k, f.type === 'select' ? f.def : ''])); setValues(v); setResult(null); setSavedId(null) }

  const ensureSaved = async () => {
    if (savedId) return savedId
    const { id } = await calculatorService.save({ type: key, inputs: toInputs(key, values), result })
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
  const main = useMemo(() => (result ? (result.text ?? pkr(result.total)) : '-'), [result])

  return (
    <div className="calc">
      <div className="page-head">
        <div>
          <Breadcrumb items={[{ label: 'Home', to: '/dashboard' }, { label: 'Legal Calculator' }]} />
          <h1 className="page-title">Legal Calculator</h1>
          <p className="page-sub">Estimate common legal fees, amounts and deadlines.</p>
        </div>
        <div className="calc-tip"><Lightbulb size={24} /><p>These calculators provide estimates based on current laws and rates.<br />For complex matters, consult a qualified lawyer.</p></div>
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
          </ul>
          <div className="calc-help">
            <div className="calc-help-head"><Scale size={32} strokeWidth={1.5} /><div><b>Not sure which calculator to use?</b><span>Explore our guides or ask LegalMate for help.</span></div></div>
            <button className="btn btn-outline-navy btn-block" onClick={() => navigate('/chat')}>Ask LegalMate <ArrowRight size={17} /></button>
          </div>
        </aside>

        <section className="card calc-form">
          <div className="calc-form-head">
            <h2><c.icon size={32} strokeWidth={1.6} /> {c.title}</h2>
            <p>{c.desc}</p>
          </div>
          {c.fields.map(f => (
            <div key={f.k} className="field calc-field">
              <span className="field-label">{f.label}<span className="req">*</span></span>
              {f.type === 'select' && <Select value={values[f.k]} onChange={setV(f.k)} options={f.options} />}
              {f.type === 'money' && <input className="input" inputMode="numeric" value={values[f.k]} onChange={e => setV(f.k)(fmtInput(e.target.value))} placeholder="0" />}
              {f.type === 'number' && <input className="input" type="number" min="0" value={values[f.k]} onChange={e => setV(f.k)(e.target.value)} />}
              {f.type === 'date' && <input className="input" type="date" value={values[f.k]} onChange={e => setV(f.k)(e.target.value)} />}
              {f.help && <small className="calc-help-text">{f.help}</small>}
            </div>
          ))}
          <div className="calc-note"><Info size={22} fill="#13335b" color="#fff" /><p><b>Note:</b> {c.note}</p></div>
          <div className="calc-btns">
            <button className="btn btn-orange btn-xl calc-go" onClick={calculate} disabled={calculating}>{calculating ? <Loader2 size={22} className="spin" /> : <CalcIcon size={22} />} Calculate</button>
            <button className="btn btn-ghost btn-xl calc-reset" onClick={reset}><RotateCcw size={20} /> Reset</button>
          </div>
        </section>

        <section className={`card calc-result ${calculating && result ? 'is-refreshing' : ''}`}>
          {!result && calculating ? <PageSkeleton cards={1} rows={1} /> : result ? (
            <>
              <div className="calc-res-head"><CheckCircle2 size={30} fill="#22a45a" color="#fff" /><div><b>Estimated Result</b><span>Calculated on {calcAt}</span></div></div>
              <p className="calc-res-label">{c.resultLabel}</p>
              <p className="calc-res-value">{main}</p>
              <div className="calc-break">
                <h3>Calculation Breakdown</h3>
                {result.rows.map(([a, b]) => <div key={a} className="calc-break-row"><span>{a}</span><span>{b}</span></div>)}
                <div className="calc-break-row calc-total"><span>{c.resultLabel}</span><span>{main}</span></div>
              </div>
              <div className="calc-source">
                <FileText size={24} />
                <div><b>Applicable Rate / Source</b><span>{result.source[0]}<br />{result.source[1]}</span></div>
                {result.sourceUrl
                  ? <a className="link small" href={result.sourceUrl} target="_blank" rel="noreferrer">View Source <ArrowRight size={16} /></a>
                  : <button className="link small" onClick={() => toast(`Opening ${result.source[0]}`, 'info')}>View Source <ArrowRight size={16} /></button>}
              </div>
              {result.assumptions && (
                <>
                  <h3 className="calc-assume-title">Assumptions</h3>
                  <ol className="calc-assume">{result.assumptions.map(a => <li key={a}>{a}</li>)}</ol>
                </>
              )}
              <div className="calc-res-btns">
                <button className="btn btn-outline btn-lg" onClick={save} disabled={busy === 'save'}>{busy === 'save' ? <Loader2 size={19} className="spin" /> : <Save size={19} />} Save Calculation</button>
                <button className="btn btn-outline btn-lg" onClick={downloadSummary} disabled={busy === 'download'}>{busy === 'download' ? <Loader2 size={19} className="spin" /> : <Download size={19} />} Download Summary</button>
              </div>
            </>
          ) : (
            <div className="calc-empty"><CalcIcon size={44} strokeWidth={1.4} /><b>No result yet</b><p>Fill in the form and click Calculate to see your estimate.</p></div>
          )}
        </section>
      </div>
    </div>
  )
}
