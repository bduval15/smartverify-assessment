/** Render the application title and current backend health indicator. */
export default function AppHeader({ apiOnline }) {
  return (
    <header>
      <div>
        <h1>SmartVerify Policy Manager</h1>
        <p>Manage tenant-scoped Cedar policy files.</p>
      </div>
      <span className={apiOnline ? 'status online' : 'status offline'}>
        API {apiOnline ? 'online' : 'offline'}
      </span>
    </header>
  )
}
