import { getInitData } from './telegram'

const BASE = import.meta.env.VITE_API_URL || '/api'

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `tma ${getInitData()}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 204) return null
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = new Error(typeof data.detail === 'string' ? data.detail : 'Request failed')
    err.status = res.status
    throw err
  }
  return data
}

export const api = {
  me: () => request('GET', '/me'),

  myLeagues: () => request('GET', '/leagues'),
  createLeague: (body) => request('POST', '/leagues', body),
  league: (id) => request('GET', `/leagues/${id}`),
  invitePreview: (code) => request('GET', `/leagues/invite/${code}`),
  join: (code) => request('POST', `/leagues/invite/${code}/join`),

  leagueMatches: (id) => request('GET', `/leagues/${id}/matches`),
  standings: (id) => request('GET', `/leagues/${id}/standings`),
  matchPredictions: (id, matchId) => request('GET', `/leagues/${id}/matches/${matchId}/predictions`),
  savePrediction: (id, matchId, home, away) =>
    request('PUT', `/leagues/${id}/matches/${matchId}/prediction`, { home_goals: home, away_goals: away }),
  withdrawPrediction: (id, matchId) => request('DELETE', `/leagues/${id}/matches/${matchId}/prediction`),

  // Tips (Telegram Stars, Payments module #14): returns { invoice_url }. 404/405 means the
  // endpoint is not deployed, so callers hide or soften the Tip UI.
  createTipInvoice: (amount) => request('POST', '/tips', { amount }),
}
