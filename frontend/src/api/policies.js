import { apiRequest } from './client.js'

/** Build the shared policy mutation path with safely encoded query values. */
function policyPath(tenantId, filename) {
  const tenant = encodeURIComponent(tenantId)
  const file = filename
    ? `&filename=${encodeURIComponent(filename)}`
    : ''
  return `/api/policies?tenant_id=${tenant}${file}`
}

/** Fetch the metadata-indexed policies visible in one tenant. */
export async function listPolicies(userId, tenantId) {
  const response = await apiRequest(
    `/api/policies/list?tenant_id=${encodeURIComponent(tenantId)}`,
    userId,
  )
  const payload = await response.json()
  return payload.policies
}

/** Upload or replace a policy using multipart form data. */
export async function savePolicy(userId, tenantId, file, method) {
  const formData = new FormData()
  formData.append('file', file)
  await apiRequest(policyPath(tenantId), userId, { method, body: formData })
}

/** Fetch committed Cedar content for in-browser viewing. */
export async function getPolicyContent(userId, tenantId, filename) {
  const response = await apiRequest(
    `/api/policies/content?tenant_id=${encodeURIComponent(
      tenantId,
    )}&filename=${encodeURIComponent(filename)}`,
    userId,
  )
  const payload = await response.json()
  return payload.policy
}

/** Fetch the Git commit history for one tenant policy path. */
export async function getPolicyHistory(userId, tenantId, filename) {
  const response = await apiRequest(
    `/api/policies/history?tenant_id=${encodeURIComponent(
      tenantId,
    )}&filename=${encodeURIComponent(filename)}`,
    userId,
  )
  const payload = await response.json()
  return payload.history
}

/** Fetch a policy as a downloadable response Blob. */
export async function getPolicyDownload(userId, tenantId, filename) {
  const response = await apiRequest(
    `/api/policies/download?tenant_id=${encodeURIComponent(
      tenantId,
    )}&filename=${encodeURIComponent(filename)}`,
    userId,
  )
  return response.blob()
}

/** Delete one policy identified by tenant and filename. */
export async function removePolicy(userId, tenantId, filename) {
  await apiRequest(policyPath(tenantId, filename), userId, {
    method: 'DELETE',
  })
}
