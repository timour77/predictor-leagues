import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Loading, ErrorMsg } from '../components/Page'
import { competitionName, dateTime, memberName } from '../utils/format'

function Stepper({ value, onChange }) {
  return (
    <div className="step">
      <button className="stepper-btn" onClick={() => onChange(Math.min(99, value + 1))}>+</button>
      <span className="stepper-value">{value}</span>
      <button className="stepper-btn" onClick={() => onChange(Math.max(0, value - 1))}>−</button>
    </div>
  )
}

function Revealed({ leagueId, matchId, finalState }) {
  const [data, setData] = useState(null)
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (open && !data) api.matchPredictions(leagueId, matchId).then(setData).catch(() => setData({ predictions: [] }))
  }, [open, data, leagueId, matchId])
  return (
    <div style={{ marginTop: 6 }}>
      <button className="link" onClick={() => setOpen(!open)}>{open ? 'Hide' : 'Show'} everyone's predictions</button>
      {open && !data && <Loading />}
      {data && (
        <table className="table sm">
          <tbody>
            {data.predictions.map(p => (
              <tr key={p.user_id}>
                <td>{memberName(p)}</td>
                <td>{p.predicted ? `${p.home_goals} : ${p.away_goals}` : <span className="muted">missed</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function MatchCard({ league, m, memberCount, onSaved }) {
  const mine = m.prediction
  const [draft, setDraft] = useState(mine ? [mine.home_goals, mine.away_goals] : [0, 0])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const live = m.status === 'IN_PLAY' || m.status === 'PAUSED'

  async function run(fn) {
    setBusy(true); setError('')
    try { await fn(); await onSaved() } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const save = () => run(() => api.savePrediction(league.id, m.match_id, draft[0], draft[1]))
  const withdraw = () => run(async () => { await api.withdrawPrediction(league.id, m.match_id); setDraft([0, 0]) })

  const kickedOff = new Date(m.kickoff) <= new Date()
  const hasScore = m.home_goals != null && m.away_goals != null
  const dirty = !mine || mine.home_goals !== draft[0] || mine.away_goals !== draft[1]

  return (
    <div className="card">
      <div className="row sm muted">
        <span>{competitionName(m.competition_id)}</span><span className="grow" />
        {m.can_predict ? <span>Kickoff {dateTime(m.kickoff)}</span>
          : live ? <span className="badge bad">LIVE {hasScore ? `${m.home_goals}:${m.away_goals}` : ''}</span>
          : m.state === 'final' ? <span className="badge">FT {m.home_goals}:{m.away_goals}</span>
          : m.state === 'dropped' ? <span className="badge bad">Dropped</span>
          : <span className="badge">{m.status === 'POSTPONED' ? 'Postponed' : dateTime(m.kickoff)}</span>}
      </div>
      <div className="row" style={{ margin: '8px 0' }}>
        <b className="grow team">{m.home_team}</b>
        {m.can_predict ? (
          <div className="score">
            <Stepper value={draft[0]} onChange={v => setDraft([v, draft[1]])} />:
            <Stepper value={draft[1]} onChange={v => setDraft([draft[0], v])} />
          </div>
        ) : <div className="score">{mine ? `${mine.home_goals} : ${mine.away_goals}` : '— : —'}</div>}
        <b className="grow team right">{m.away_team}</b>
      </div>
      {m.can_predict ? (
        <>
          <div className="row gap">
            <button className="btn btn-primary grow" disabled={busy || !dirty} onClick={save}>{mine ? 'Update' : 'Save'} prediction</button>
            {mine && <button className="btn" disabled={busy} onClick={withdraw}>Withdraw</button>}
          </div>
          <div className="sm muted" style={{ marginTop: 6 }}>
            {mine ? `Saved ${mine.home_goals}:${mine.away_goals} · editable until kickoff` : 'Not predicted yet'}
          </div>
          <div className="sm muted">{m.predicted_count} of {memberCount} predicted · scores revealed at kickoff</div>
        </>
      ) : (
        <>
          <div className="sm muted">
            Your prediction{!mine && kickedOff && m.state !== 'dropped' && <> — <span className="bad-text">missed{m.state === 'final' ? ', 0 pts' : ''}</span></>}
            {m.state === 'final' && mine && <> · <b className="ok-text">+{m.points} pts</b></>}
          </div>
          {kickedOff && m.state !== 'dropped' && <Revealed leagueId={league.id} matchId={m.match_id} />}
        </>
      )}
      <ErrorMsg error={error} />
    </div>
  )
}

export function MatchesTab({ league, onChanged }) {
  const [matches, setMatches] = useState(null)
  const [error, setError] = useState('')
  const load = () => api.leagueMatches(league.id).then(r => setMatches(r.matches)).catch(e => setError(e.message))
  useEffect(() => { load() }, [league.id])

  const onSaved = async () => { await load(); onChanged() }
  if (error) return <ErrorMsg error={error} />
  if (!matches) return <Loading />
  if (!matches.length) return <div className="empty">No matches in this Window yet. They appear as the schedule is published.</div>
  return matches.map(m => (
    <MatchCard key={m.match_id} league={league} m={m} memberCount={league.members.length} onSaved={onSaved} />
  ))
}
