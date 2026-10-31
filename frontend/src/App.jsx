import { useEffect, useState, useCallback } from 'react'
import { api } from './services/api'
import { getInitData, initTelegram, startParam, showBackButton } from './services/telegram'
import { HomePage } from './pages/HomePage'
import { CreateLeaguePage } from './pages/CreateLeaguePage'
import { InvitePage } from './pages/InvitePage'
import { JoinPage } from './pages/JoinPage'
import { LeaguePage } from './pages/LeaguePage'
import { ProfilePage } from './pages/ProfilePage'

function initialRoute() {
  const p = startParam()
  if (p.startsWith('join_')) return { name: 'join', code: p.slice(5) }
  // Reminder deep link: straight to the League; no param (or a bad one) lands on the Leagues list.
  const league = /^league_(\d+)$/.exec(p)
  return league ? { name: 'league', id: Number(league[1]) } : { name: 'home' }
}

export default function App() {
  const [me, setMe] = useState(null)
  const [error, setError] = useState('')
  const [stack, setStack] = useState([initialRoute()])
  const route = stack[stack.length - 1]

  const push = useCallback((r) => setStack(s => [...s, r]), [])
  const back = useCallback(() => setStack(s => (s.length > 1 ? s.slice(0, -1) : [{ name: 'home' }])), [])
  const replace = useCallback((r) => setStack(s => [...s.slice(0, -1), r]), [])
  const home = useCallback(() => setStack([{ name: 'home' }]), [])

  useEffect(() => {
    initTelegram()
    if (!getInitData()) { setError('Open this app from Telegram.'); return }
    api.me().then(setMe).catch(e => setError(e.message))
  }, [])

  useEffect(() => showBackButton(stack.length > 1 ? back : null), [stack.length, back])

  if (error) return <div className="center-screen"><div style={{ fontSize: 32 }}>⚽</div><p>{error}</p></div>
  if (!me) return <div className="center-screen"><div className="spinner" /></div>

  const nav = { push, back, replace, home }
  return (
    <main className="app">
      {route.name === 'home' && <HomePage me={me} nav={nav} />}
      {route.name === 'create' && <CreateLeaguePage nav={nav} />}
      {route.name === 'invite' && <InvitePage leagueId={route.id} nav={nav} />}
      {route.name === 'join' && <JoinPage code={route.code} nav={nav} />}
      {route.name === 'league' && <LeaguePage key={route.id} leagueId={route.id} me={me} nav={nav} />}
      {route.name === 'profile' && <ProfilePage me={me} nav={nav} />}
      <div className="attribution">Football data provided by the Football-Data.org API</div>
    </main>
  )
}
