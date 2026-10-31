import { useState } from 'react'
import { Page } from '../components/Page'
import { Avatar } from '../components/Avatar'
import { TipSheet } from '../components/TipSheet'
import { memberName } from '../utils/format'

export function ProfilePage({ me, nav }) {
  const [tip, setTip] = useState(false)
  // `trophies` comes from /me once Settlement (#15) ships; hidden until then.
  const trophies = me.trophies ?? me.trophy_count
  const m = { ...me, user_id: me.id }
  return (
    <Page title="Profile" onBack={nav.back}>
      <div className="card center">
        <Avatar member={m} />
        <div><b>{memberName(m)}</b></div>
        {me.username && <div className="muted sm">@{me.username}</div>}
        {trophies != null && <div style={{ marginTop: 6 }}>🏆 × {trophies}</div>}
      </div>
      <div className="card">
        <b>Support the developer</b>
        <div className="muted sm">Tips in ⭐ Stars. Nothing in return that affects play.</div>
        <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={() => setTip(true)}>Leave a tip</button>
      </div>
      {tip && <TipSheet onClose={() => setTip(false)} />}
    </Page>
  )
}
