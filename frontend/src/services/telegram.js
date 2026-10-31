// Telegram Mini App bridge. `initData` is signed by Telegram and verified by the backend on
// every request. VITE_DEV_INIT_DATA lets a local build run outside Telegram against a dev backend.
const tg = window.Telegram?.WebApp

export function getInitData() {
  return tg?.initData || import.meta.env.VITE_DEV_INIT_DATA || ''
}

export function startParam() {
  return tg?.initDataUnsafe?.start_param || new URLSearchParams(window.location.search).get('startapp') || ''
}

export function initTelegram() {
  tg?.ready()
  tg?.expand()
}

export function inviteLink(code) {
  const base = import.meta.env.VITE_BOT_APP_LINK || 'https://t.me/predictor_bot/app'
  return `${base}?startapp=join_${code}`
}

export function shareInvite(code, leagueName) {
  const url = inviteLink(code)
  const text = `Join my League "${leagueName}" on Predictor Leagues`
  const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`
  if (tg?.openTelegramLink) tg.openTelegramLink(shareUrl)
  else window.open(shareUrl, '_blank')
}

export function openInvoice(url) {
  return new Promise((resolve) => {
    if (tg?.openInvoice) tg.openInvoice(url, (status) => resolve(status))
    else resolve('unsupported')
  })
}

export function showBackButton(onBack) {
  const bb = tg?.BackButton
  if (!bb) return () => {}
  if (onBack) {
    bb.onClick(onBack)
    bb.show()
    return () => { bb.offClick(onBack); bb.hide() }
  }
  bb.hide()
  return () => {}
}
