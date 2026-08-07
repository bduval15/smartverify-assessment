import AccessPanel from './components/AccessPanel.jsx'
import AppHeader from './components/AppHeader.jsx'
import PolicyContent from './components/PolicyContent.jsx'
import PolicyHistory from './components/PolicyHistory.jsx'
import PolicyList from './components/PolicyList.jsx'
import PolicyUpload from './components/PolicyUpload.jsx'
import usePolicyManager from './hooks/usePolicyManager.js'

function App() {
  const manager = usePolicyManager()

  return (
    <main>
      <AppHeader apiOnline={manager.apiOnline} />

      <AccessPanel
        users={manager.users}
        userId={manager.userId}
        tenantId={manager.tenantId}
        authorizedTenants={manager.authorizedTenants}
        onUserChange={manager.changeUser}
        onTenantChange={manager.changeTenant}
      />

      <PolicyUpload
        selectedFile={manager.selectedFile}
        busy={manager.busy}
        onFileChange={manager.setSelectedFile}
        onSave={manager.savePolicy}
      />

      {manager.message && (
        <p className="notice success">{manager.message}</p>
      )}
      {manager.error && <p className="notice error">{manager.error}</p>}

      <PolicyList
        tenantId={manager.tenantId}
        policies={manager.policies}
        busy={manager.busy}
        onRefresh={manager.loadPolicies}
        onView={manager.viewContent}
        onDownload={manager.downloadPolicy}
        onHistory={manager.viewHistory}
        onDelete={manager.deletePolicy}
      />

      <PolicyContent
        policy={manager.selectedContent}
        onClose={() => manager.setSelectedContent(null)}
      />

      <PolicyHistory
        history={manager.selectedHistory}
        onClose={() => manager.setSelectedHistory(null)}
      />
    </main>
  )
}

export default App
