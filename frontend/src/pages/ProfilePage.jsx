import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Page } from '../components/Page'
import { Avatar } from '../components/Avatar'
import { TipSheet } from '../components/TipSheet'
import { memberName } from '../utils/format'

export function ProfilePage({ me, nav }) {
  const [tip, setTip] = useState(false)
  const [trophies, setTrophies] = useState(null)
  useEffect(() => { api.myTrophies().then(d => setTrophies(d.trophies)).catch(() => {}) }, [])
  const m = { ...me, user_id: me.id }
  return (
    <Page title="Profile" onBack={nav.back}>
      <div className="card center">
        <Avatar member={m} />
        <div><b>{memberName(m)}</b></div>
        {me.username && <div className="muted sm">@{me.username}</div>}
        {trophies?.length > 0 && <div style={{ marginTop: 6 }}>🏆 × {trophies.length}</div>}
      </div>
      {trophies?.length > 0 && (
        <div className="card">
          <b>Trophies</b>
          {trophies.map(t => (
            <div key={t.league_id} className="sm" style={{ marginTop: 4 }}>
              🏆 {t.league_name} <span className="muted">· {t.points} pts, {t.exact} exact</span>
            </div>
          ))}
        </div>
      )}
      <div className="card">
        <b>Support the developer</b>
        <div className="muted sm">Tips in ⭐ Stars. Nothing in return that affects play.</div>
        <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={() => setTip(true)}>Leave a tip</button>
      </div>
      {tip && <TipSheet onClose={() => setTip(false)} />}
    </Page>
  )
}
