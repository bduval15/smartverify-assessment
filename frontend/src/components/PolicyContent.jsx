/** Render the selected policy's committed Cedar text. */
export default function PolicyContent({ policy, onClose }) {
  if (!policy) {
    return null
  }

  return (
    <section aria-labelledby="content-heading">
      <div className="section-heading">
        <h2 id="content-heading">{policy.filename}</h2>
        <button type="button" className="secondary" onClick={onClose}>
          Close
        </button>
      </div>
      <pre>{policy.content}</pre>
    </section>
  )
}
