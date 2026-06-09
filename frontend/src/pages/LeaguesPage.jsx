import { useState, useEffect } from 'react'
import { api } from '../services/api'

function Avatar({ photoUrl, username, size = 32 }) {
  if (photoUrl) {
    return <img src={photoUrl} alt="" style={{ width: size, height: size, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }} />
  }
  return (
    <div style={{ width: size, height: size, borderRadius: '50%', background: 'var(--primary)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: size * 0.4, flexShrink: 0 }}>
      {username[0].toUpperCase()}
    </div>
  )
}

function CreateLeagueModal({ onClose, onCreate }) {
  const [name, setName] = useState('')
  const [entryFee, setEntryFee] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleCreate() {
    if (!name.trim()) return
    setLoading(true)
    setError(null)
    try {
      const league = await api.createLeague(name.trim(), entryFee)
      onCreate(league)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'flex-end', zIndex: 100 }}>
      <div style={{ background: 'var(--bg)', borderRadius: '16px 16px 0 0', padding: 24, width: '100%', boxSizing: 'border-box' }}>
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 20 }}>Создать лигу</div>

        <div className="section-label" style={{ marginBottom: 6 }}>Название</div>
        <input
          className="input"
          style={{ marginBottom: 16 }}
          placeholder="Лига друзей"
          value={name}
          onChange={e => setName(e.target.value)}
          autoFocus
        />

        <div className="section-label" style={{ marginBottom: 6 }}>Взнос (Telegram Stars)</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {[0, 50, 100, 250].map(v => (
            <button
              key={v}
              className={`btn btn-sm ${entryFee === v ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setEntryFee(v)}
            >
              {v === 0 ? 'Бесплатно' : `⭐ ${v}`}
            </button>
          ))}
        </div>
        {entryFee > 0 && (
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 20 }}>
            Призовой фонд растёт с каждым участником: {entryFee} Stars × N человек
          </div>
        )}

        {error && <div className="error-msg" style={{ marginBottom: 12 }}>{error}</div>}

        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost btn-block" onClick={onClose}>Отмена</button>
          <button className="btn btn-primary btn-block" onClick={handleCreate} disabled={loading || !name.trim()}>
            {loading ? '...' : 'Создать'}
          </button>
        </div>
      </div>
    </div>
  )
}

function JoinLeagueModal({ onClose, onJoin }) {
  const [code, setCode] = useState('')
  const [league, setLeague] = useState(null)
  const [loading, setLoading] = useState(false)
  const [joining, setJoining] = useState(false)
  const [error, setError] = useState(null)

  async function handleLookup() {
    const inviteCode = code.trim().split('/').pop()
    if (!inviteCode) return
    setLoading(true)
    setError(null)
    try {
      const l = await api.getLeague(inviteCode)
      setLeague(l)
    } catch (e) {
      setError('Лига не найдена')
    } finally {
      setLoading(false)
    }
  }

  async function handleJoin() {
    setJoining(true)
    setError(null)
    try {
      const result = await api.joinLeague(league.invite_code)
      if (result.status === 'joined') {
        onJoin(league)
        return
      }
      // Paid league — open Telegram Stars invoice
      const tg = window.Telegram?.WebApp
      if (!tg) throw new Error('Telegram WebApp not available')
      tg.openInvoice(result.invoice_url, async (status) => {
        if (status === 'paid') {
          // Confirm with backend (also handled via webhook, but do it here for instant UX)
          await api.confirmPayment(league.id, 'pending').catch(() => {})
          onJoin(league)
        } else if (status === 'cancelled') {
          setError('Оплата отменена')
          setJoining(false)
        } else {
          setError('Ошибка оплаты')
          setJoining(false)
        }
      })
    } catch (e) {
      setError(e.message)
      setJoining(false)
    }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'flex-end', zIndex: 100 }}>
      <div style={{ background: 'var(--bg)', borderRadius: '16px 16px 0 0', padding: 24, width: '100%', boxSizing: 'border-box' }}>
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 20 }}>Вступить в лигу</div>

        <div className="section-label" style={{ marginBottom: 6 }}>Инвайт-код или ссылка</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <input
            className="input"
            style={{ flex: 1 }}
            placeholder="abc123XY"
            value={code}
            onChange={e => { setCode(e.target.value); setLeague(null); setError(null) }}
          />
          <button className="btn btn-primary btn-sm" onClick={handleLookup} disabled={loading || !code.trim()}>
            {loading ? '...' : 'Найти'}
          </button>
        </div>

        {league && (
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>{league.name}</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              {league.member_count} участников
              {league.entry_fee > 0 && <span style={{ marginLeft: 8, color: 'var(--warning)', fontWeight: 600 }}>⭐ {league.entry_fee}</span>}
              {league.prize_pool > 0 && <span style={{ marginLeft: 8, color: 'var(--success)' }}>Призовой фонд: ⭐ {league.prize_pool}</span>}
            </div>
            {league.is_member && <div style={{ marginTop: 6, fontSize: 12, color: 'var(--success)' }}>✓ Ты уже участник</div>}
          </div>
        )}

        {error && <div className="error-msg" style={{ marginBottom: 12 }}>{error}</div>}

        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost btn-block" onClick={onClose}>Отмена</button>
          {league && !league.is_member && (
            <button className="btn btn-primary btn-block" onClick={handleJoin} disabled={joining}>
              {joining ? '...' : league.entry_fee > 0 ? `Оплатить ⭐ ${league.entry_fee}` : 'Вступить'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function LeaguePage({ league: initialLeague, currentUserId, onBack }) {
  const [league] = useState(initialLeague)
  const [leaderboard, setLeaderboard] = useState([])
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.getLeagueLeaderboard(league.invite_code)
      .then(setLeaderboard)
      .finally(() => setLoading(false))
  }, [league.invite_code])

  function copyInvite() {
    const link = `https://t.me/share/url?url=${encodeURIComponent(league.invite_code)}`
    navigator.clipboard.writeText(league.invite_code).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="page">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <button className="btn btn-ghost btn-sm" onClick={onBack}>← Назад</button>
        <div style={{ flex: 1, fontSize: 18, fontWeight: 700 }}>{league.name}</div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Участников</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{league.member_count}</div>
          </div>
          {league.entry_fee > 0 && (
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Призовой фонд</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--warning)' }}>⭐ {league.prize_pool}</div>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--bg2)', borderRadius: 8, padding: '8px 12px' }}>
          <code style={{ flex: 1, fontSize: 14, color: 'var(--text-secondary)' }}>{league.invite_code}</code>
          <button className="btn btn-ghost btn-sm" onClick={copyInvite}>
            {copied ? '✓' : 'Копировать'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loader"><div className="spinner" />Загрузка...</div>
      ) : leaderboard.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🏆</div>
          <div className="empty-state-text">Пока нет прогнозов</div>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {leaderboard.map((entry) => (
            <div
              key={entry.user_id}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
                borderBottom: '1px solid var(--border)',
                background: entry.user_id === currentUserId ? 'var(--primary-subtle)' : undefined,
              }}
            >
              <span style={{ width: 24, textAlign: 'center', fontWeight: 700, color: entry.rank <= 3 ? 'var(--warning)' : 'var(--text-muted)', fontSize: 14 }}>
                {entry.rank === 1 ? '🥇' : entry.rank === 2 ? '🥈' : entry.rank === 3 ? '🥉' : entry.rank}
              </span>
              <Avatar photoUrl={entry.photo_url} username={entry.username} size={32} />
              <span style={{ flex: 1, fontWeight: entry.user_id === currentUserId ? 700 : 400 }}>
                {entry.username}
                {entry.user_id === currentUserId && <span className="me-tag">Я</span>}
              </span>
              <span className="points-badge">{entry.total_points} pts</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function LeaguesPage({ user }) {
  const [leagues, setLeagues] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [showJoin, setShowJoin] = useState(false)
  const [selectedLeague, setSelectedLeague] = useState(null)

  useEffect(() => {
    api.getMyLeagues()
      .then(setLeagues)
      .finally(() => setLoading(false))
  }, [])

  function handleCreated(league) {
    setLeagues(prev => [league, ...prev])
    setShowCreate(false)
    setSelectedLeague(league)
  }

  function handleJoined(league) {
    setLeagues(prev => prev.find(l => l.id === league.id) ? prev : [league, ...prev])
    setShowJoin(false)
    setSelectedLeague(league)
  }

  if (selectedLeague) {
    return (
      <LeaguePage
        league={selectedLeague}
        currentUserId={user?.id}
        onBack={() => setSelectedLeague(null)}
      />
    )
  }

  return (
    <div className="page">
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <button className="btn btn-primary btn-block" onClick={() => setShowCreate(true)}>
          + Создать лигу
        </button>
        <button className="btn btn-ghost btn-block" onClick={() => setShowJoin(true)}>
          Вступить
        </button>
      </div>

      {loading ? (
        <div className="loader"><div className="spinner" />Загрузка...</div>
      ) : leagues.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🏅</div>
          <div className="empty-state-text">У тебя пока нет лиг. Создай свою или вступи по инвайту.</div>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {leagues.map(league => (
            <button
              key={league.id}
              className="participant-row"
              onClick={() => setSelectedLeague(league)}
            >
              <div style={{ flex: 1, textAlign: 'left' }}>
                <div style={{ fontWeight: 600, marginBottom: 2 }}>{league.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  {league.member_count} участников
                  {league.entry_fee > 0 && <span style={{ marginLeft: 8, color: 'var(--warning)' }}>⭐ {league.entry_fee} взнос</span>}
                  {league.is_creator && <span style={{ marginLeft: 8, color: 'var(--primary)' }}>Организатор</span>}
                </div>
              </div>
              {league.prize_pool > 0 && (
                <span style={{ fontWeight: 700, color: 'var(--warning)', fontSize: 14 }}>⭐ {league.prize_pool}</span>
              )}
            </button>
          ))}
        </div>
      )}

      {showCreate && <CreateLeagueModal onClose={() => setShowCreate(false)} onCreate={handleCreated} />}
      {showJoin && <JoinLeagueModal onClose={() => setShowJoin(false)} onJoin={handleJoined} />}
    </div>
  )
}
