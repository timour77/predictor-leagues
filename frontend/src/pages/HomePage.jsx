import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Page, Loading, ErrorMsg } from '../components/Page'
import { competitionName, dateOnly, statusBadge } from '../utils/format'

export function HomePage({ me, nav }) {
  const [leagues, setLeagues] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.myLeagues().then(r => setLeagues(r.leagues)).catch(e => setError(e.message))
  }, [])

  return (
    <Page title="Predictor Leagues" right={
      <button className="btn btn-ghost btn-sm" onClick={() => nav.push({ name: 'profile' })}>👤</button>}>
      <div className="row" style={{ marginBottom: 10 }}>
        <b className="grow">My Leagues</b>
        <button className="btn btn-primary btn-sm" onClick={() => nav.push({ name: 'create' })}>+ New League</button>
      </div>
      <ErrorMsg error={error} />
      {!leagues && !error && <Loading />}
      {leagues?.length === 0 && (
        <div className="empty">No Leagues yet. Create one and invite your friends, or open an invite link.</div>
      )}
      {leagues?.map(l => {
        const badge = statusBadge(l)
        return (
          <div key={l.id} className="card clickable" onClick={() => nav.push({ name: 'league', id: l.id })}>
            <div className="row"><b className="grow">{l.name}</b><span className={`badge ${badge.tone}`}>{badge.label}</span></div>
            <div className="muted sm">{l.competition_ids.map(competitionName).join(', ')}</div>
            <div className="muted sm">{dateOnly(l.window_start)} → {dateOnly(l.window_end)}{l.creator_id === me.id ? ' · you are Creator' : ''}</div>
          </div>
        )
      })}
    </Page>
  )
}
