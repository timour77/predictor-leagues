import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Loading, ErrorMsg } from '../components/Page'

// Display-only mirror of the scoring rule (1 outcome + 3 exact); the server's Standings are authoritative.
const sign = (h, a) => Math.sign(h - a)
const points = (p, m) => (sign(p.home_goals, p.away_goals) === sign(m.home_goals, m.away_goals) ? 1 : 0)
  + (p.home_goals === m.home_goals && p.away_goals === m.away_goals ? 3 : 0)

export function HistoryTab({ league }) {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.leagueMatches(league.id).then(async ({ matches }) => {
      // Reveal happens at kickoff: only matches that are live or decided have visible scores.
      const shown = matches.filter(m => new Date(m.kickoff) <= new Date() && m.state !== 'dropped')
      const preds = await Promise.all(shown.map(m => api.matchPredictions(league.id, m.match_id)))
      setRows(shown.map((m, i) => ({ m, preds: preds[i].predictions })))
    }).catch(e => setError(e.message))
  }, [league.id])

  if (error) return <ErrorMsg error={error} />
  if (!rows) return <Loading />
  if (!rows.length) return <div className="empty">History appears once matches kick off.</div>

  return (
    <div className="card" style={{ overflowX: 'auto' }}>
      <table className="table sm">
        <thead>
          <tr><th>Match</th>{league.members.map(m => <th key={m.user_id}>{(m.first_name || m.username || '?')[0]}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map(({ m, preds }) => (
            <tr key={m.match_id}>
              <td>{m.home_team.slice(0, 3)}–{m.away_team.slice(0, 3)}<br />
                <b>{m.home_goals ?? '?'}:{m.away_goals ?? '?'}</b>{m.state !== 'final' && ' live'}</td>
              {league.members.map(mem => {
                const p = preds.find(x => x.user_id === mem.user_id)
                return (
                  <td key={mem.user_id}>
                    {p?.predicted ? `${p.home_goals}:${p.away_goals}` : '—'}
                    {m.state === 'final' && <><br /><span className="muted">+{p?.predicted ? points(p, m) : 0}</span></>}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
