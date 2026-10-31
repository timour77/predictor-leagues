import { Avatar } from '../components/Avatar'
import { memberName } from '../utils/format'

export function MembersTab({ league, nav }) {
  return (
    <>
      <div className="card">
        {league.members.map(m => (
          <div key={m.user_id} className="row gap" style={{ padding: '5px 0' }}>
            <Avatar member={m} />{memberName(m)}<span className="grow" />
            {m.user_id === league.creator_id && <span className="badge">Creator</span>}
          </div>
        ))}
      </div>
      {league.status === 'open' && (
        <button className="btn btn-block" onClick={() => nav.push({ name: 'invite', id: league.id })}>Invite more</button>
      )}
    </>
  )
}
