import { publicApiRequest } from './client.js'

export async function getDemoUsers() {
  const response = await publicApiRequest('/api/users')
  const payload = await response.json()
  return payload.users
}
