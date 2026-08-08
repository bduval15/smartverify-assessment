export const API_URL = (
  import.meta.env.VITE_API_URL || 'http://localhost:8000'
).replace(/\/$/, '')

/** Convert FastAPI error payloads into one message suitable for the UI. */
function getErrorMessage(payload, status) {
  const detail = payload?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (detail && typeof detail === 'object') {
    return [detail.message, detail.validation_error]
      .filter(Boolean)
      .join(': ')
  }
  return `Request failed with status ${status}`
}

/** Send a request to the configured backend and throw on non-success status. */
async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
  })

  if (!response.ok) {
    let payload
    try {
      payload = await response.json()
    } catch {
      payload = null
    }
    throw new Error(getErrorMessage(payload, response.status))
  }

  return response
}

/** Send a request to an endpoint that does not require a demo user header. */
export function publicApiRequest(path, options = {}) {
  return request(path, options)
}

/** Send an authenticated demo request carrying the selected user identity. */
export function apiRequest(path, userId, options = {}) {
  // The header is intentionally simple for the assessment; the backend still
  // treats it as untrusted input and enforces the user's tenant mapping.
  return request(path, {
    ...options,
    headers: {
      'user-id': userId,
      ...options.headers,
    },
  })
}

/** Report whether the backend and its database health endpoint are available. */
export async function isApiOnline() {
  try {
    const response = await fetch(`${API_URL}/`)
    return response.ok
  } catch {
    return false
  }
}
