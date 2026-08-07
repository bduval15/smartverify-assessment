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

function downloadBlob(blob, filename) {
  const downloadUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(downloadUrl)
}

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

  function clearSelection() {
    setSelectedContent(null)
    setSelectedHistory(null)
    setMessage('')
    setError('')
    setBusy('list')
  }

  function changeUser(nextUserId) {
    const nextUser = users.find((user) => user.user_id === nextUserId)
    if (!nextUser) {
      return
    }
    setUserId(nextUserId)
    setTenantId(nextUser.tenant_ids[0])
    clearSelection()
  }

  function changeTenant(nextTenantId) {
    setTenantId(nextTenantId)
    clearSelection()
  }

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
