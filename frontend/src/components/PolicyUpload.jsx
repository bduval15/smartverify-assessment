import { useEffect, useRef } from 'react'

export default function PolicyUpload({
  selectedFile,
  busy,
  onFileChange,
  onSave,
}) {
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (!selectedFile && fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [selectedFile])

  return (
    <section aria-labelledby="upload-heading">
      <h2 id="upload-heading">Upload or replace a policy</h2>
      <div className="upload-row">
        <input
          ref={fileInputRef}
          type="file"
          accept=".cedar,text/plain,application/cedar"
          onChange={(event) => onFileChange(event.target.files[0] || null)}
        />
        <button
          type="button"
          disabled={Boolean(busy)}
          onClick={() => onSave('POST')}
        >
          Upload new
        </button>
        <button
          type="button"
          className="secondary"
          disabled={Boolean(busy)}
          onClick={() => onSave('PUT')}
        >
          Replace existing
        </button>
      </div>
      <small>
        "Replace existing" uses the selected file's name to identify the policy.
      </small>
    </section>
  )
}
