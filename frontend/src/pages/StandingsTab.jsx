import { Loading } from '../components/Page'
import { memberName } from '../utils/format'

const MEDAL = ['🥇', '🥈', '🥉']

export function StandingsTab({ standings, me }) {
  if (!standings) return <Loading />
  return (
    <>
      <div className="card">
        <table className="table">
          <thead><tr><th>#</th><th>Member</th><th>Exact</th><th>Pts</th></tr></thead>
          <tbody>
            {standings.standings.map(r => (
              <tr key={r.user_id} className={r.user_id === me.id ? 'me' : ''}>
                <td>{MEDAL[r.rank - 1] || r.rank}</td><td>{memberName(r)}</td><td>{r.exact}</td><td><b>{r.points}</b></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="sm muted">
        {standings.matches_scored} scored · {standings.matches_pending} to come. 1 point for the outcome, +3 for the exact score.
        Ties on points → more exact scores. Still tied → all tied Members win a Trophy.
      </div>
    </>
  )
}
