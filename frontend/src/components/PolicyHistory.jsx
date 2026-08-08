/** Render Git commits associated with the selected policy path. */
export default function PolicyHistory({ history, onClose }) {
  if (!history) {
    return null
  }

  return (
    <section aria-labelledby="history-heading">
      <div className="section-heading">
        <h2 id="history-heading">History: {history.filename}</h2>
        <button type="button" className="secondary" onClick={onClose}>
          Close
        </button>
      </div>
      {history.commits.length === 0 ? (
        <p>No commits found.</p>
      ) : (
        <ul className="history">
          {history.commits.map((commit) => (
            <li key={commit.commit_hash}>
              <code>{commit.commit_hash.slice(0, 8)}</code>
              <span>{commit.message}</span>
              <time>{new Date(commit.date).toLocaleString()}</time>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
