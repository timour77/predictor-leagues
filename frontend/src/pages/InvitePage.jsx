import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Page, Loading, ErrorMsg } from '../components/Page'
import { Avatar } from '../components/Avatar'
import { inviteLink, shareInvite } from '../services/telegram'
import { competitionName, dateOnly, memberName } from '../utils/format'

export function InvitePage({ leagueId, nav }) {
  const [league, setLeague] = useState(null)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => { api.league(leagueId).then(setLeague).catch(e => setError(e.message)) }, [leagueId])

  const open = () => nav.replace({ name: 'league', id: leagueId })
  if (!league) return <Page title="Invite friends" onBack={nav.back}><ErrorMsg error={error} />{!error && <Loading />}</Page>

  const link = inviteLink(league.invite_code)
  async function copy() {
    try { await navigator.clipboard.writeText(link); setCopied(true) } catch { setCopied(false) }
  }

  return (
    <Page title="Invite friends" onBack={nav.back}>
      <div className="card center">
        <div style={{ fontSize: 40 }}>✉️</div>
        <b>{league.name}</b>
        <div className="muted sm">{league.competition_ids.map(competitionName).join(', ')} · {dateOnly(league.window_start)} → {dateOnly(league.window_end)}</div>
      </div>
      <div className="card sm muted" style={{ wordBreak: 'break-all' }}>{link}</div>
      <button className="btn btn-primary btn-block" onClick={() => shareInvite(league.invite_code, league.name)}>Share in Telegram</button>
      <button className="btn btn-ghost btn-block" style={{ margin: '8px 0 16px' }} onClick={copy}>{copied ? 'Copied ✓' : 'Copy link'}</button>
      <b>Members ({league.members.length})</b>
      {league.members.map(m => (
        <div key={m.user_id} className="row gap" style={{ marginTop: 6 }}>
          <Avatar member={m} />{memberName(m)}
          {m.user_id === league.creator_id && <span className="badge">Creator</span>}
        </div>
      ))}
      <p className="muted sm" style={{ margin: '12px 0' }}>Anyone with the link can join for free until the first match kicks off.</p>
      <button className="btn btn-block" onClick={open}>Go to League</button>
    </Page>
  )
}
