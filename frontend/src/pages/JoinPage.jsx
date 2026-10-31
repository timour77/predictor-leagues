import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Page, Loading, ErrorMsg } from '../components/Page'
import { competitionName, dateOnly, dateTime } from '../utils/format'

export function JoinPage({ code, nav }) {
  const [league, setLeague] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.invitePreview(code).then(setLeague).catch(e => setError(e.message)) }, [code])

  async function join() {
    setBusy(true); setError('')
    try {
      const l = await api.join(code)
      nav.replace({ name: 'league', id: l.id })
    } catch (e) { setError(e.message); setBusy(false) }
  }

  const closed = league && (league.status !== 'open' || new Date(league.join_closes_at) <= new Date())

  return (
    <Page title="Invitation" onBack={nav.back}>
      <ErrorMsg error={error} />
      {!league && !error && <Loading />}
      {league && (
        <>
          <div className="card center">
            <div style={{ fontSize: 40 }}>⚽</div>
            <h2 style={{ margin: '6px 0' }}>{league.name}</h2>
            <div className="muted sm">{league.competition_ids.map(competitionName).join(', ')}</div>
            <div className="muted sm">{dateOnly(league.window_start)} → {dateOnly(league.window_end)}</div>
            <div className="muted sm">{league.member_count} member{league.member_count === 1 ? '' : 's'}</div>
            <div className="muted sm">Joining closes {dateTime(league.join_closes_at)}</div>
          </div>
          <div className="card sm"><b>Free to join.</b> Predict exact scores: 1 point for the outcome, +3 for the exact score. The winner gets a 🏆 Trophy.</div>
          {league.is_member
            ? <button className="btn btn-primary btn-block" onClick={() => nav.replace({ name: 'league', id: league.id })}>Open League</button>
            : <button className="btn btn-success btn-block" disabled={busy || closed} onClick={join}>{closed ? 'Joining closed' : 'Join League: free'}</button>}
        </>
      )}
    </Page>
  )
}
