import { useState } from 'react'
import { api } from '../services/api'
import { openInvoice, openLegal } from '../services/telegram'

// Tips are offered only from the profile and the Settlement banner (ADR 0002), never during
// join or predict. If the Payments endpoint is not deployed the sheet reports it politely.
export function TipSheet({ onClose }) {
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  async function tip(stars) {
    setBusy(true); setMsg('')
    try {
      const { invoice_url } = await api.createTipInvoice(stars)
      const status = await openInvoice(invoice_url)
      if (status === 'paid') { setMsg('Thank you! ⭐'); return }
      if (status === 'unsupported') setMsg('Open this app inside Telegram to leave a tip.')
    } catch (e) {
      setMsg(e.status === 404 || e.status === 405 ? 'Tips are not available yet.' : e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" onClick={e => e.stopPropagation()}>
        <b>Leave a tip ⭐</b>
        <p className="muted sm">Voluntary. It doesn't change points, standings or anything in a League.</p>
        <p className="muted sm">
          By tipping you confirm you have read and agree to the{' '}
          <a href="/terms" onClick={e => { e.preventDefault(); openLegal('terms') }}>Terms</a>.{' '}
          See also the <a href="/privacy" onClick={e => { e.preventDefault(); openLegal('privacy') }}>Privacy policy</a>.
          Need a refund? Send /paysupport to the bot.
        </p>
        <div className="row gap" style={{ margin: '12px 0' }}>
          {[10, 50, 100].map(n => (
            <button key={n} className="btn btn-ghost grow" disabled={busy} onClick={() => tip(n)}>{n} ⭐</button>
          ))}
        </div>
        {msg && <p className="sm" style={{ marginBottom: 8 }}>{msg}</p>}
        <button className="btn btn-block" onClick={onClose}>Close</button>
      </div>
    </div>
  )
}
