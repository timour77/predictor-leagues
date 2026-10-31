export function Page({ title, onBack, right, children }) {
  return (
    <>
      <header className="topbar">
        {onBack && <button className="btn btn-ghost btn-sm" onClick={onBack}>‹</button>}
        <span className="grow topbar-title">{title}</span>
        {right}
      </header>
      <div className="page">{children}</div>
    </>
  )
}

export function Loading() { return <div className="center-screen"><div className="spinner" /></div> }

export function ErrorMsg({ error }) { return error ? <div className="error-msg">{error}</div> : null }
