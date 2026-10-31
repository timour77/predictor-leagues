import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import { Page, Loading, ErrorMsg } from '../components/Page'
import { TipSheet } from '../components/TipSheet'
import { MatchesTab } from './MatchesTab'
import { StandingsTab } from './StandingsTab'
import { HistoryTab } from './HistoryTab'
import { MembersTab } from './MembersTab'
import { dateOnly, memberName } from '../utils/format'

const TABS = [['matches', 'Matches'], ['standings', 'Standings'], ['history', 'History'], ['members', 'Members']]

export function LeaguePage({ leagueId, me, nav }) {
  const [league, setLeague] = useState(null)
  const [standings, setStandings] = useState(null)
  const [tab, setTab] = useState('matches')
  const [tip, setTip] = useState(false)
  const [error, setError] = useState('')

  const loadStandings = useCallback(
    () => api.standings(leagueId).then(setStandings).catch(e => setError(e.message)), [leagueId])

  useEffect(() => {
    api.league(leagueId).then(setLeague).catch(e => setError(e.message))
    loadStandings()
  }, [leagueId, loadStandings])

  if (!league) return <Page title="League" onBack={nav.back}><ErrorMsg error={error} />{!error && <Loading />}</Page>

  // Settlement decides the winners (nobody wins if nothing was scored), so trust `winner_ids`.
  const winners = (league.winner_ids ?? [])
    .map(id => league.members.find(m => m.user_id === id) ?? { user_id: id })

  return (
    <Page title={league.name} onBack={nav.home}>
      {league.status === 'cancelled' && (
        <div className="card danger-border"><b>League cancelled</b>
          <div className="sm muted">Fewer than 2 Members when the Window started. The Creator was notified.</div></div>
      )}
      {league.status === 'open' && (
        <div className="card warn-border"><b>Starts {dateOnly(league.window_start)}</b>
          <div className="sm muted">{league.members.length} member{league.members.length === 1 ? '' : 's'}. You can already predict. Needs 2+ to start.</div>
          <button className="btn btn-sm" style={{ marginTop: 8 }} onClick={() => nav.push({ name: 'invite', id: league.id })}>Invite friends</button></div>
      )}
      {winners.length > 0 && (
        <div className="card warn-border center">
          <div style={{ fontSize: 42 }}>🏆</div>
          <b>{winners.map(memberName).join(' & ')} won {league.name}</b>
          <div className="sm muted">{winners.some(w => w.user_id === me.id) ? 'Trophy added to your profile!' : 'Trophy added to their profile.'}</div>
          <div className="sm muted" style={{ marginTop: 8 }}>
            Had fun? <a href="#tip" onClick={e => { e.preventDefault(); setTip(true) }}>Leave a tip to the developer ⭐</a>
          </div>
        </div>
      )}
      <ErrorMsg error={error} />
      <div className="tabs">
        {TABS.map(([k, label]) => (
          <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>
      {tab === 'matches' && <MatchesTab league={league} onChanged={loadStandings} />}
      {tab === 'standings' && <StandingsTab standings={standings} me={me} />}
      {tab === 'history' && <HistoryTab league={league} />}
      {tab === 'members' && <MembersTab league={league} nav={nav} />}
      {tip && <TipSheet onClose={() => setTip(false)} />}
    </Page>
  )
}
