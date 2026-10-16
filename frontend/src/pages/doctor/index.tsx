import { FollowUps } from '../../components/FollowUps'
import { useState, useEffect, useCallback } from 'react'
import { Routes, Route, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { TEST_LOINC } from '../../data/loinc'
import { Sidebar } from '../../components/Sidebar'
import { StatusBadge, FlagBadge } from '../../components/StatusBadge'
import {
  doctorDashboard, getDoctorPatient, currentVisit, saveConsultation,
  getConsultation, savePrescriptions, getPrescriptions,
  getCatalogue, createLabOrder, getPatientReports,
  patientVisits, completeVisit, patientLabOrders, doctorPatients
} from '../../api'
import { FileText, Pill, CheckCircle, Plus, Trash, RefreshCw, Search } from 'lucide-react'

// ── Outpatient overview ───────────────────────────────────────────────────────────
function DoctorDashboard() {
  const [dash, setDash] = useState<any>(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const reload = useCallback(() => {
    return doctorDashboard().then(r => { setDash(r.data); setError('') }).catch(() => setError('Could not refresh the queue. Please retry.')).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    reload()
    // auto-refresh every 5 seconds so nurse-completed patients appear automatically
    const timer = setInterval(reload, 5_000)
    window.addEventListener('focus', reload)
  return () => { clearInterval(timer); window.removeEventListener('focus', reload) }
  }, [reload])

  const normalizedQuery = query.trim().toLowerCase()
  const matches = (...values: unknown[]) => values.some(value => String(value ?? '').toLowerCase().includes(normalizedQuery))
  const matchingPatients = (dash?.my_patients ?? []).filter((v: any) => matches(v.patient?.name, v.patient?.uhid, v.visit_ref))
  const matchingOrders = (dash?.pending_order_items ?? []).filter((o: any) => matches(o.patient, o.order_id))
  const matchingReports = (dash?.report_items ?? []).filter((r: any) => matches(r.patient, r.test, r.report_id))

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="page-title">Outpatient overview</h1>
        <button className="btn-secondary" onClick={reload} disabled={loading}>
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>
      <div className="flex gap-3 items-center mb-6">
        <div className="relative flex-1"><Search size={17} className="absolute left-3 top-3 text-slate-500" aria-hidden="true" />
          <input type="search" className="input pl-10" aria-label="Search doctor dashboard" placeholder="Search patient name, UHID, order or report ID" value={query} onChange={e => setQuery(e.target.value)} />
        </div>
        {query && <button className="btn-secondary" onClick={() => setQuery('')}>Clear</button>}
      </div>
      {error && <div role="alert" className="alert-danger mb-4">{error}</div>}
      {dash && (
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="stat-card"><div><div className="text-slate-600 text-xs">Active patients</div><div className="text-3xl font-bold text-green-800">{dash.my_patients?.length}</div></div></div>
          <div className="stat-card"><div><div className="text-slate-600 text-xs">Pending Lab Orders</div><div className="text-3xl font-bold text-amber-800">{dash.pending_orders}</div></div></div>
          <div className="stat-card"><div><div className="text-slate-600 text-xs">Released Reports</div><div className="text-3xl font-bold text-green-800">{dash.released_reports}</div></div></div>
        </div>
      )}
      <div className="card">
        <div className="section-heading"><h2 className="section-title">Patient queue</h2><span>Assigned to you · auto-refreshes every 5s</span></div>
        <div className="table-wrapper">
          <table className="table">
            <thead><tr><th>Patient</th><th>UHID</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
              {matchingPatients.map((v: any) => (
                <tr key={v.visit_id}>
                  <td className="font-medium text-slate-900">{v.patient?.name}</td>
                  <td className="text-slate-600">{v.patient?.uhid}</td>
                  <td><StatusBadge status={v.status} /></td>
                  <td><button className="btn btn-primary btn-sm" onClick={() => navigate(`/doctor/patients/${v.patient?.id}`)}>Open Chart</button></td>
                </tr>
              ))}
              {!matchingPatients.length && !loading && (
                <tr><td colSpan={4} className="text-center text-slate-500 py-8">
                  {normalizedQuery ? 'No patients match your search.' : 'No active patients assigned to you.'}<br/>
                  <span className="text-xs">Patients appear here after the receptionist creates a visit and checks them in, then the nurse records vitals.</span>
                </td></tr>
              )}
              {loading && !dash && <tr><td colSpan={4} className="text-center text-slate-400 py-8">Loading...</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
      <div className="mt-6">
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="card"><h2 className="section-title mb-3">Pending lab orders</h2>{matchingOrders.map((o: any) => <button key={o.id} className="block text-left w-full p-3 border-b border-slate-200 hover:bg-slate-50" onClick={() => navigate(`/doctor/patients/${o.patient_id}?tab=Lab%20Orders&order=${o.id}`)}>{o.patient} · {o.order_id}<div className="text-sm text-amber-800">{o.status}</div></button>)}{!matchingOrders.length && <p className="text-slate-600">No pending orders</p>}</div>
        <div className="card"><h2 className="section-title mb-3">Released reports</h2>{matchingReports.map((r: any) => <button key={r.report_id} className="block text-left w-full p-3 border-b border-slate-200 hover:bg-slate-50" onClick={() => navigate(`/doctor/patients/${r.patient_id}?tab=Reports&report=${r.report_id}`)}>{r.patient} · {r.test}<div className="text-sm text-green-800">{r.report_id}</div></button>)}{!matchingReports.length && <p className="text-slate-600">No released reports</p>}</div>
      </div>
      </div>
    </div>
  )
}

// ── Patient Page ───────────────────────────────────────────────────────────────
const TABS = ['Overview', 'Consultation', 'Lab Orders', 'Reports', 'Prescription', 'Follow-up', 'Patient History']

function PatientPage() {
  const { patientId } = useParams()
  const pid = Number(patientId)
  const [params] = useSearchParams()
  const [tab, setTab] = useState(params.get('tab') === 'History' ? 'Patient History' : params.get('tab') || 'Overview')
  const [patient, setPatient] = useState<any>(null)
  const [visit, setVisit] = useState<any>(null)

  const [loadError, setLoadError] = useState('')
  useEffect(() => {
    let active = true
    const reload = async () => {
      try {
        const p = await getDoctorPatient(pid)
        const v = await currentVisit(pid).catch(error => {
          if (error.response?.status === 404) return { data: null }
          throw error
        })
        if (active) { setPatient(p.data); setVisit(v.data); setLoadError('') }
      } catch { if (active) setLoadError('Could not refresh this patient chart. Please try again.') }
    }
    reload()
    const timer = setInterval(reload, 5000)
    window.addEventListener('focus', reload)
    return () => { active = false; clearInterval(timer); window.removeEventListener('focus', reload) }
  }, [pid])

  return (
    <div>
      <div className="mb-6">
        <h1 className="page-title">{patient?.full_name ?? 'Patient'}</h1>
        <div className="flex items-center gap-4 mt-1 text-slate-600 text-sm">
          <span>UHID: <span className="text-green-800 font-mono">{patient?.uhid}</span></span>
          {patient?.dob && <span>DOB: {patient.dob}</span>}
          {patient?.gender && <span>{patient.gender}</span>}
          {patient?.blood_group && <span className="badge-red">{patient.blood_group}</span>}
          {visit && <StatusBadge status={visit.status} />}
        </div>
      </div>

      {loadError && <div role="alert" className="alert-danger mb-4">{loadError}</div>}
      <div className="tab-bar">
        {TABS.map(t => (
          <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>

      {tab === 'Follow-up' && <FollowUps patientId={pid} />}
      {tab === 'Overview'      && <OverviewTab visit={visit} patient={patient} />}
      {tab === 'Consultation'  && visit && <ConsultationTab visitId={visit.id} patientId={pid} />}
      {tab === 'Lab Orders' && <LabOrdersTab visitId={visit?.id} patientId={pid} />}
      {tab === 'Reports'       && <ReportsTab patientId={pid} />}
      {tab === 'Prescription'  && visit && <PrescriptionTab visitId={visit.id} />}
      {tab === 'Patient History'       && <HistoryTab patientId={pid} />}
      {!visit && tab !== 'Follow-up' && tab !== 'Overview' && tab !== 'Reports' && tab !== 'Patient History' && tab !== 'Lab Orders' && (
        <div className="alert-warn">No active visit found for this patient.</div>
      )}
    </div>
  )
}

function OverviewTab({ visit, patient }: any) {
  return (
    <div className="grid grid-cols-2 gap-6">
      <div className="card">
        <h3 className="section-title mb-4">Demographics</h3>
        <dl className="flex flex-col gap-2 text-sm">
          {[['Phone', patient?.phone], ['Address', patient?.address], ['Allergies', patient?.allergies], ['ABHA ID', patient?.abha_number || 'Not linked']].map(([k, v]) => (
            <div key={k} className="flex gap-2"><dt className="text-slate-600 w-24 shrink-0">{k}:</dt><dd className="text-slate-900">{v || '—'}</dd></div>
          ))}
        </dl>
      </div>
      {visit && (
        <div className="card">
          <h3 className="section-title mb-4">Current Visit Vitals</h3>
          {visit.vitals ? (
            <dl className="grid grid-cols-2 gap-2 text-sm">
              {[
                ['Temp', `${visit.vitals.temperature}°C`],
                ['BP', `${visit.vitals.bp_systolic}/${visit.vitals.bp_diastolic}`],
                ['Pulse', `${visit.vitals.pulse} bpm`],
                ['SpO2', `${visit.vitals.spo2}%`],
                ['Height', `${visit.vitals.height_cm} cm`],
                ['Weight', `${visit.vitals.weight_kg} kg`],
              ].map(([k, v]) => (
                <div key={k} className="bg-slate-50 rounded-lg p-2">
                  <div className="text-slate-600 text-xs">{k}</div>
                  <div className="text-slate-900 font-medium">{v}</div>
                </div>
              ))}
              <div className="col-span-2 bg-slate-50 rounded-lg p-2"><div className="text-slate-600 text-xs">Chief Complaint</div><div className="text-slate-900">{visit.vitals.chief_complaint}</div></div>
              {visit.vitals.is_urgent && <div className="col-span-2 badge-red text-center">⚠ Urgent Case</div>}
            </dl>
          ) : <div className="text-slate-600 text-sm">Vitals not recorded yet</div>}
        </div>
      )}
    </div>
  )
}

function ConsultationTab({ visitId }: { visitId: number, patientId: number }) {
  const [form, setForm] = useState({ complaints: '', examination: '', diagnosis: '', notes: '' })
  const [msg, setMsg] = useState(''); const [err, setErr] = useState('')
  const navigate = useNavigate()

  useEffect(() => { getConsultation(visitId).then(r => setForm(r.data)).catch(() => {}) }, [visitId])
  const set = (k: string) => (e: any) => setForm(f => ({ ...f, [k]: e.target.value }))

  const save = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(''); setMsg('')
    try { await saveConsultation(visitId, form); setMsg('Consultation saved') }
    catch (err: any) { setErr(err.response?.data?.detail ?? 'Save failed') }
  }
  const finish = async () => {
    try { await saveConsultation(visitId, form); await completeVisit(visitId); navigate('/doctor') }
    catch (error: any) { setErr(error.response?.data?.detail || 'Could not complete visit') }
  }

  return (
    <form onSubmit={save} className="card max-w-2xl flex flex-col gap-4">
      <div className="form-group"><label className="label">Presenting Complaints</label><textarea className="input" rows={2} value={form.complaints} onChange={set('complaints')} /></div>
      <div className="form-group"><label className="label">Examination Findings</label><textarea className="input" rows={3} value={form.examination} onChange={set('examination')} /></div>
      <div className="form-group"><label className="label">Diagnosis</label><textarea className="input" rows={2} value={form.diagnosis} onChange={set('diagnosis')} /></div>
      <div className="form-group"><label className="label">Notes</label><textarea className="input" rows={2} value={form.notes} onChange={set('notes')} /></div>
      {msg && <div className="alert-success">{msg}</div>}
      {err && <div className="alert-danger">{err}</div>}
      <div className="flex gap-3">
        <button type="submit" className="btn-primary"><FileText size={15} /> Save Consultation</button>
        <button type="button" className="btn-success" onClick={finish}><CheckCircle size={15} /> Complete Visit</button>
      </div>
    </form>
  )
}

function LabOrdersTab({ visitId, patientId }: { visitId?: number; patientId: number }) {
  const [catalogue, setCatalogue] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [params] = useSearchParams()
  const [selected, setSelected] = useState<number[]>([])
  const [priority, setPriority] = useState('Routine')
  const [msg, setMsg] = useState(''); const [err, setErr] = useState('')

  useEffect(() => {
    getCatalogue().then(r => setCatalogue(r.data))
    patientLabOrders(patientId).then(r => setOrders(r.data))
  }, [visitId, patientId])

  const toggle = (id: number) => setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id])

  const order = async () => {
    if (!selected.length) return setErr('Select at least one test')
    setErr('')
    try {
      await createLabOrder({ visit_id: visitId, test_ids: selected, priority })
      setMsg('Lab order created!'); setSelected([])
      patientLabOrders(patientId).then(r => setOrders(r.data))
    } catch (err: any) { setErr(err.response?.data?.detail ?? 'Failed') }
  }

  return (
    <div className="grid grid-cols-2 gap-6">
      <div className="card">
        <h3 className="section-title mb-4">Order Tests</h3>{!visitId && <p className="alert-info mb-4">A new active visit is required to order tests. Previous orders are shown here.</p>}
        <div className="form-group mb-4">
          <label className="label">Priority</label>
          <select className="select" value={priority} onChange={e => setPriority(e.target.value)}>
            <option>Routine</option><option>Urgent</option>
          </select>
        </div>
        <div className="flex flex-col gap-2 mb-4">
          {catalogue.map(t => (
            <label key={t.id} className="flex items-center gap-3 p-3 rounded-md bg-slate-50 hover:bg-green-50 cursor-pointer border border-slate-200">
              <input type="checkbox" checked={selected.includes(t.id)} onChange={() => toggle(t.id)} className="w-4 h-4 accent-green-800" />
              <div>
                <div className="text-slate-900 text-sm font-medium">{t.name} {TEST_LOINC[t.code] && <span className="ml-2 inline-block text-xs font-normal text-green-800" title="LOINC order catalogue reference">LOINC {TEST_LOINC[t.code]}</span>}</div>
                <div className="text-slate-600 text-xs">{t.code} · {t.sample_type} · ~{t.turnaround_minutes}min</div>
              </div>
            </label>
          ))}
        </div>
        {err && <div className="alert-danger mb-3">{err}</div>}
        {msg && <div className="alert-success mb-3">{msg}</div>}
        <button className="btn-primary w-full justify-center" disabled={!visitId} onClick={order}><Plus size={15} /> Create Order</button>
      </div>
      <div className="card">
        <h3 className="section-title mb-4">Existing Orders</h3>
        <div className="flex flex-col gap-3">
          {orders.map((o: any) => (
            <div key={o.id} className={`card-sm ${params.get("order") === String(o.id) ? "ring-2 ring-green-700" : ""}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-green-800 text-sm">{o.order_id}</span>
                <div className="flex gap-2"><StatusBadge status={o.priority} /><StatusBadge status={o.status} /></div>
              </div>
              <div className="text-slate-700 text-sm">{o.tests?.map((t: any) => t.name).join(', ')}</div>
            </div>
          ))}
          {!orders.length && <div className="text-slate-600 text-sm">No orders yet</div>}
        </div>
      </div>
    </div>
  )
}

function ReportsTab({ patientId }: { patientId: number }) {
  const [params] = useSearchParams()
  const [reports, setReports] = useState<any[]>([])
  useEffect(() => { getPatientReports(patientId).then(r => setReports(r.data)).catch(() => {}) }, [patientId])

  return (
    <div className="card">
      <h3 className="section-title mb-4">Released Lab Reports</h3>
      {reports.length ? (
        <div className="table-wrapper">
          <table className="table">
            <thead><tr><th>Report ID</th><th>Test</th><th>Value</th><th>Flag</th><th>Approved By</th><th>Date</th></tr></thead>
            <tbody>
              {reports.map((r: any) => (
                <tr key={r.report_id} className={params.get("report") === r.report_id ? "bg-green-100/20" : ""}>
                  <td className="font-mono text-green-800">{r.report_id}</td>
                  <td>{r.test?.name}</td>
                  <td className="max-w-xs whitespace-normal">{r.value}<div className="text-slate-600 text-xs mt-2">Reference: {r.ref_range}</div><button className="btn-secondary btn-sm mt-2" onClick={() => { const url = URL.createObjectURL(new Blob([`ClinSync — LAB REPORT\n${r.report_id}\n${r.test?.name}\n${r.value}\nReference: ${r.ref_range}\nFlag: ${r.flag || "None"}\nApproved by: ${r.approved_by}\n${r.approved_at}`], { type: "text/plain" })); const a = document.createElement("a"); a.href = url; a.download = `${r.report_id}.txt`; a.click(); URL.revokeObjectURL(url) }}>Download</button></td>
                  <td><FlagBadge flag={r.flag} /></td>
                  <td>{r.approved_by}</td>
                  <td className="text-slate-600 text-xs">{new Date(r.approved_at).toLocaleString('en-IN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <div className="text-slate-600 text-sm">No released reports yet</div>}
    </div>
  )
}

function PrescriptionTab({ visitId }: { visitId: number }) {
  const [items, setItems] = useState<any[]>([{ medicine: '', dosage: '', frequency: '', duration: '', instructions: '', advice: '' }])
  const [msg, setMsg] = useState(''); const [err, setErr] = useState('')

  useEffect(() => { getPrescriptions(visitId).then(r => { if (r.data.length) setItems(r.data) }).catch(() => {}) }, [visitId])

  const setItem = (i: number, k: string) => (e: any) => setItems(items => items.map((item, idx) => idx === i ? { ...item, [k]: e.target.value } : item))
  const add = () => setItems(i => [...i, { medicine: '', dosage: '', frequency: '', duration: '', instructions: '', advice: '' }])
  const remove = (i: number) => setItems(items => items.filter((_, idx) => idx !== i))

  const save = async () => {
    setErr(''); setMsg('')
    try { await savePrescriptions(visitId, items.filter(p => p.medicine)); setMsg('Prescriptions saved') }
    catch (err: any) { setErr(err.response?.data?.detail ?? 'Save failed') }
  }

  return (
    <div className="card max-w-2xl">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title">Prescription</h3>
        <button className="btn-secondary btn-sm" onClick={add}><Plus size={13} /> Add Medicine</button>
      </div>
      <div className="flex flex-col gap-4">
        {items.map((item, i) => (
          <div key={i} className="card-sm">
            <div className="grid grid-cols-2 gap-3">
              <div className="form-group col-span-2"><label className="label">Medicine</label><input className="input" value={item.medicine} onChange={setItem(i, 'medicine')} /></div>
              <div className="form-group"><label className="label">Dosage</label><input className="input" value={item.dosage} onChange={setItem(i, 'dosage')} placeholder="e.g. 500mg BD" /></div>
              <div className="form-group"><label className="label">Frequency</label><input className="input" value={item.frequency} onChange={setItem(i, 'frequency')} placeholder="e.g. twice daily" /></div>
              <div className="form-group"><label className="label">Duration</label><input className="input" value={item.duration} onChange={setItem(i, 'duration')} placeholder="e.g. 5 days" /></div>
              <div className="form-group"><label className="label">Instructions</label><input className="input" value={item.instructions} onChange={setItem(i, 'instructions')} placeholder="e.g. After food" /></div>
              <div className="form-group col-span-2 flex items-end gap-2">
                <div className="flex-1"><label className="label">Advice</label><input className="input" value={item.advice} onChange={setItem(i, 'advice')} /></div>
                {items.length > 1 && <button className="btn-danger btn-sm mb-0.5" onClick={() => remove(i)}><Trash size={13} /></button>}
              </div>
            </div>
          </div>
        ))}
      </div>
      {msg && <div className="alert-success mt-4">{msg}</div>}
      {err && <div className="alert-danger mt-4">{err}</div>}
      <button className="btn-primary mt-4" onClick={save}><Pill size={15} /> Save Prescription</button>
    </div>
  )
}

function HistoryTab({ patientId }: { patientId: number }) {
  const [visits, setVisits] = useState<any[]>([])
  useEffect(() => { patientVisits(patientId).then(r => setVisits(r.data)).catch(() => {}) }, [patientId])

  return (
    <div className="card">
      {/* <h3 className="section-title mb-4">Patient History</h3>
      <section className="card-sm mb-5" aria-label="Patient history from ABHA">
        <h4 className="font-medium text-green-800 mb-2">Patient history (from ABHA)</h4>
        <p className="text-sm text-slate-600">ABHA ID: {patient?.abha_number || 'Not provided'}</p>
        <p className="text-sm text-slate-600 mt-1">No records retrieved from ABHA. ABHA record access is not connected.</p>
      </section> */}
      <h4 className="font-medium mb-3">History recorded at ClinSync</h4>
      <div className="flex flex-col gap-4">
        {visits.map((v: any) => (
          <div key={v.id} className="card-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-green-800 text-sm">{v.visit_id}</span>
              <StatusBadge status={v.status} />
            </div>
            <div className="text-slate-600 text-xs mb-2">{v.department} · {v.doctor?.full_name} · {new Date(v.appointment_time).toLocaleDateString('en-IN')}</div>
            {v.vitals && <div className="text-slate-700 text-sm">Chief Complaint: {v.vitals.chief_complaint}</div>}
            <p>Diagnosis: {v.diagnosis || 'Not recorded'}</p><p className="text-slate-600">{v.notes}</p>
            {v.prescriptions?.map((p: any, i: number) => <p key={i} className="text-sm">{p.medicine} · {p.dosage} · {p.frequency} · {p.duration} · {p.instructions}</p>)}
            {v.orders?.map((o: any) => <p key={o.order_id} className="text-sm text-green-800">{o.order_id} · {o.status}</p>)}
            {v.conditions?.map((h: any, i: number) => <p key={i}>Condition: {h.condition} · Medicines: {h.medicines}</p>)}
          </div>
        ))}
        {!visits.length && <div className="text-slate-600 text-sm">No history found</div>}
      </div>
    </div>
  )
}

export default function DoctorApp() {
  return (
    <div className="flex">
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route index element={<DoctorDashboard />} />
          <Route path="patients/:patientId" element={<PatientPage />} />
          <Route path="patients" element={<PatientListRedirect />} />
        </Routes>
      </main>
    </div>
  )
}

function PatientListRedirect() {
  const navigate = useNavigate()
  const [patients, setPatients] = useState<any[]>([])
  const [query, setQuery] = useState('')
  useEffect(() => { doctorPatients().then(r => setPatients(r.data)) }, [])
  return <div><h1 className="page-title mb-6">My Patients</h1><input aria-label="Search my patients" className="input mb-4" placeholder="Search name or UHID" value={query} onChange={e => setQuery(e.target.value)} /><div className="card">{patients.filter(p => `${p.name} ${p.uhid}`.toLowerCase().includes(query.toLowerCase())).map(p => <button key={p.id} className="block p-4 w-full text-left border-b border-slate-200 hover:bg-slate-50" onClick={() => navigate(`/doctor/patients/${p.id}`)}>{p.name}<span className="text-slate-600 ml-3">{p.uhid}</span></button>)}</div></div>
}
