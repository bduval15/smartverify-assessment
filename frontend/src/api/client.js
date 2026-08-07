export const API_URL = (
  import.meta.env.VITE_API_URL || 'http://localhost:8000'
).replace(/\/$/, '')

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

export function publicApiRequest(path, options = {}) {
  return request(path, options)
}

export function apiRequest(path, userId, options = {}) {
  return request(path, {
    ...options,
    headers: {
      'user-id': userId,
      ...options.headers,
    },
  })
}

export async function isApiOnline() {
  try {
    const response = await fetch(`${API_URL}/`)
    return response.ok
  } catch {
    return false
  }
}
