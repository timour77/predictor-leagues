import { memberName } from '../utils/format'

export function Avatar({ member, done }) {
  return (
    <span className={`avatar ${done ? 'done' : ''}`} title={memberName(member)}>
      {member.photo_url
        ? <img src={member.photo_url} alt="" />
        : memberName(member)[0]?.toUpperCase()}
    </span>
  )
}
