export const COMPETITIONS = {
  2000: 'World Cup',
  2001: 'Champions League',
  2002: 'Bundesliga',
  2003: 'Eredivisie',
  2013: 'Brasileirão',
  2014: 'La Liga',
  2015: 'Ligue 1',
  2016: 'Championship',
  2017: 'Primeira Liga',
  2018: 'European Championship',
  2019: 'Serie A',
  2021: 'Premier League',
}

export const competitionName = (id) => COMPETITIONS[id] || `Competition ${id}`

export function dateTime(iso) {
  return new Date(iso).toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function dateOnly(d) {
  return new Date(`${d}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export function memberName(m) {
  return m.first_name || m.username || `User ${m.user_id}`
}

export function todayISO() {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

// League status as shown in the list; the backend's "settling" is still Active to a Member.
export function statusBadge(league, now = Date.now()) {
  switch (league.status) {
    case 'open': return { label: `Starts ${dateOnly(league.window_start)}`, tone: 'warn' }
    case 'active':
    case 'settling': return { label: 'Active', tone: 'ok' }
    case 'settled': return { label: '🏆 Settled', tone: '' }
    case 'cancelled': return { label: 'Cancelled', tone: 'bad' }
    default: return { label: league.status, tone: '' }
  }
}
