import { useCallback, useEffect, useState } from 'react'
import { isApiOnline } from '../api/client.js'
import {
  getPolicyContent,
  getPolicyDownload,
  getPolicyHistory,
  listPolicies,
  removePolicy,
  savePolicy as savePolicyRequest,
} from '../api/policies.js'
import { getDemoUsers } from '../api/users.js'

/** Trigger a browser download for a response Blob and release its object URL. */
function downloadBlob(blob, filename) {
  // Object URLs save the real response body without navigating away; revoking
  // the URL immediately prevents the Blob from being retained in memory.
  const downloadUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(downloadUrl)
}

/** Coordinate policy API operations and all state shared by the page sections. */
export default function usePolicyManager() {
  const [users, setUsers] = useState([])
  const [userId, setUserId] = useState('')
  const [tenantId, setTenantId] = useState('')
  const [policies, setPolicies] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [selectedContent, setSelectedContent] = useState(null)
  const [selectedHistory, setSelectedHistory] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('list')
  const [apiOnline, setApiOnline] = useState(false)

  const authorizedTenants =
    users.find((user) => user.user_id === userId)?.tenant_ids || []

  /** Refresh the selected tenant's metadata list on demand. */
  const loadPolicies = useCallback(async () => {
    if (!userId || !tenantId) {
      return
    }
    setBusy('list')
    setError('')
    try {
      setPolicies(await listPolicies(userId, tenantId))
    } catch (requestError) {
      setPolicies([])
      setError(requestError.message)
    } finally {
      setBusy('')
    }
  }, [tenantId, userId])

  useEffect(() => {
    void isApiOnline().then(setApiOnline)
  }, [])

  useEffect(() => {
    // Access options come from the backend to avoid duplicating security
    // configuration in React. The server remains authoritative on every call.
    getDemoUsers()
      .then((demoUsers) => {
        setUsers(demoUsers)
        if (demoUsers.length > 0) {
          setUserId(demoUsers[0].user_id)
          setTenantId(demoUsers[0].tenant_ids[0])
        }
      })
      .catch((requestError) => {
        setError(requestError.message)
        setBusy('')
      })
  }, [])

  useEffect(() => {
    if (!userId || !tenantId) {
      return undefined
    }

    // Ignore a slower response after the user switches tenants, preventing an
    // old tenant's list from replacing the newly selected tenant's results.
    let active = true

    listPolicies(userId, tenantId)
      .then((tenantPolicies) => {
        if (active) {
          setPolicies(tenantPolicies)
        }
      })
      .catch((requestError) => {
        if (active) {
          setPolicies([])
          setError(requestError.message)
        }
      })
      .finally(() => {
        if (active) {
          setBusy('')
        }
      })

    return () => {
      active = false
    }
  }, [tenantId, userId])

  /** Clear tenant-specific panels and messages before changing access scope. */
  function clearSelection() {
    setSelectedContent(null)
    setSelectedHistory(null)
    setMessage('')
    setError('')
    setBusy('list')
  }

  /** Select a demo user and default to the first tenant they may access. */
  function changeUser(nextUserId) {
    const nextUser = users.find((user) => user.user_id === nextUserId)
    if (!nextUser) {
      return
    }
    setUserId(nextUserId)
    setTenantId(nextUser.tenant_ids[0])
    clearSelection()
  }

  /** Select another tenant within the current user's authorized options. */
  function changeTenant(nextTenantId) {
    setTenantId(nextTenantId)
    clearSelection()
  }

  /** Upload or strictly replace the currently selected local file. */
  async function savePolicy(method) {
    if (!selectedFile) {
      setError('Choose a Cedar file first.')
      return
    }

    setBusy(method)
    setMessage('')
    setError('')
    try {
      await savePolicyRequest(userId, tenantId, selectedFile, method)
      setMessage(
        method === 'POST'
          ? `${selectedFile.name} uploaded.`
          : `${selectedFile.name} replaced.`,
      )
      setSelectedFile(null)
      await loadPolicies()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy('')
    }
  }

  /** Load committed Cedar content and close the history panel. */
  async function viewContent(filename) {
    setBusy(`content:${filename}`)
    setError('')
    setSelectedHistory(null)
    try {
      setSelectedContent(await getPolicyContent(userId, tenantId, filename))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy('')
    }
  }

  /** Load Git history and close the content panel. */
  async function viewHistory(filename) {
    setBusy(`history:${filename}`)
    setError('')
    setSelectedContent(null)
    try {
      const commits = await getPolicyHistory(userId, tenantId, filename)
      setSelectedHistory({ filename, commits })
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy('')
    }
  }

  /** Download one committed policy without navigating away from the page. */
  async function downloadPolicy(filename) {
    setBusy(`download:${filename}`)
    setError('')
    try {
      const blob = await getPolicyDownload(userId, tenantId, filename)
      downloadBlob(blob, filename)
      setMessage(`${filename} downloaded.`)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy('')
    }
  }

  /** Confirm and delete one policy, then refresh the metadata list. */
  async function deletePolicy(filename) {
    if (!window.confirm(`Delete ${filename}?`)) {
      return
    }

    setBusy(`delete:${filename}`)
    setMessage('')
    setError('')
    try {
      await removePolicy(userId, tenantId, filename)
      setMessage(`${filename} deleted.`)
      setSelectedContent(null)
      setSelectedHistory(null)
      await loadPolicies()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy('')
    }
  }

  return {
    apiOnline,
    authorizedTenants,
    busy,
    changeTenant,
    changeUser,
    deletePolicy,
    downloadPolicy,
    error,
    loadPolicies,
    message,
    policies,
    savePolicy,
    selectedContent,
    selectedFile,
    selectedHistory,
    setSelectedContent,
    setSelectedFile,
    setSelectedHistory,
    tenantId,
    userId,
    users,
    viewContent,
    viewHistory,
  }
}
