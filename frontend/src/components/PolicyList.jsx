export default function PolicyList({
  tenantId,
  policies,
  busy,
  onRefresh,
  onView,
  onDownload,
  onHistory,
  onDelete,
}) {
  return (
    <section aria-labelledby="policies-heading">
      <div className="section-heading">
        <h2 id="policies-heading">Policies for {tenantId}</h2>
        <button
          type="button"
          className="secondary"
          disabled={Boolean(busy)}
          onClick={onRefresh}
        >
          Refresh
        </button>
      </div>

      {busy === 'list' ? (
        <p>Loading policies...</p>
      ) : policies.length === 0 ? (
        <p>No policies found.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {policies.map((policy) => (
                <tr key={policy.id}>
                  <td>{policy.filename}</td>
                  <td className="actions">
                    <button
                      type="button"
                      onClick={() => onView(policy.filename)}
                      disabled={Boolean(busy)}
                    >
                      View
                    </button>
                    <button
                      type="button"
                      onClick={() => onDownload(policy.filename)}
                      disabled={Boolean(busy)}
                    >
                      Download
                    </button>
                    <button
                      type="button"
                      onClick={() => onHistory(policy.filename)}
                      disabled={Boolean(busy)}
                    >
                      History
                    </button>
                    <button
                      type="button"
                      className="danger"
                      onClick={() => onDelete(policy.filename)}
                      disabled={Boolean(busy)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
