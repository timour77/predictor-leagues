import { useState } from 'react'
import { api } from '../services/api'
import { Page, ErrorMsg } from '../components/Page'
import { COMPETITIONS, todayISO } from '../utils/format'

function plusDays(iso, n) {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

export function CreateLeaguePage({ nav }) {
  const today = todayISO()
  const [name, setName] = useState('')
  const [comps, setComps] = useState([])
  const [from, setFrom] = useState(today)
  const [to, setTo] = useState(plusDays(today, 30))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const toggle = (id) => setComps(c => (c.includes(id) ? c.filter(x => x !== id) : [...c, id]))
  const valid = name.trim() && comps.length && from && to && to >= from

  async function submit() {
    setBusy(true); setError('')
    try {
      const league = await api.createLeague({
        name: name.trim(), competition_ids: comps, window_start: from, window_end: to,
      })
      nav.replace({ name: 'invite', id: league.id })
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  return (
    <Page title="New League" onBack={nav.back}>
      <p className="muted sm">Free to join. The winner gets a Trophy.</p>
      <label className="label">League name</label>
      <input className="input" value={name} maxLength={60} placeholder="e.g. Friday Football"
        onChange={e => setName(e.target.value)} />
      <label className="label">Competitions (one or more)</label>
      <div>
        {Object.entries(COMPETITIONS).map(([id, label]) => (
          <span key={id} className={`chip ${comps.includes(+id) ? 'on' : ''}`} onClick={() => toggle(+id)}>{label}</span>
        ))}
      </div>
      <label className="label">Window: only matches inside count</label>
      <div className="row gap">
        <input className="input" type="date" value={from} min={today} onChange={e => setFrom(e.target.value)} />
        <input className="input" type="date" value={to} min={from} onChange={e => setTo(e.target.value)} />
      </div>
      <p className="muted sm" style={{ margin: '12px 0' }}>
        Joining closes when the first match of the Window kicks off. A League needs 2+ Members by then or it is cancelled.
      </p>
      <ErrorMsg error={error} />
      <button className="btn btn-primary btn-block" disabled={!valid || busy} onClick={submit}>Create League</button>
    </Page>
  )
}
