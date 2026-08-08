import { publicApiRequest } from './client.js'

/** Load seeded customer, user, and tenant mappings from the backend. */
export async function getDemoUsers() {
  const response = await publicApiRequest('/api/users')
  const payload = await response.json()
  return payload.users
}
