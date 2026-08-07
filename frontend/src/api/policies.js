import { apiRequest } from './client.js'

function policyPath(tenantId, filename) {
  const tenant = encodeURIComponent(tenantId)
  const file = filename
    ? `&filename=${encodeURIComponent(filename)}`
    : ''
  return `/api/policies?tenant_id=${tenant}${file}`
}

export async function listPolicies(userId, tenantId) {
  const response = await apiRequest(
    `/api/policies/list?tenant_id=${encodeURIComponent(tenantId)}`,
    userId,
  )
  const payload = await response.json()
  return payload.policies
}

export async function savePolicy(userId, tenantId, file, method) {
  const formData = new FormData()
  formData.append('file', file)
  await apiRequest(policyPath(tenantId), userId, { method, body: formData })
}

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

export async function getPolicyDownload(userId, tenantId, filename) {
  const response = await apiRequest(
    `/api/policies/download?tenant_id=${encodeURIComponent(
      tenantId,
    )}&filename=${encodeURIComponent(filename)}`,
    userId,
  )
  return response.blob()
}

export async function removePolicy(userId, tenantId, filename) {
  await apiRequest(policyPath(tenantId, filename), userId, {
    method: 'DELETE',
  })
}
