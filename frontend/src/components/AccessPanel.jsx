/** Render backend-provided demo users and their authorized tenant options. */
export default function AccessPanel({
  users,
  userId,
  tenantId,
  authorizedTenants,
  onUserChange,
  onTenantChange,
}) {
  return (
    <section aria-labelledby="access-heading">
      <h2 id="access-heading">Access</h2>
      <div className="form-row">
        <label>
          User
          <select
            value={userId}
            onChange={(event) => onUserChange(event.target.value)}
          >
            {users.map((user) => (
              <option key={user.user_id} value={user.user_id}>
                {user.user_id} ({user.customer_id})
              </option>
            ))}
          </select>
        </label>

        <label>
          Tenant
          <select
            value={tenantId}
            onChange={(event) => onTenantChange(event.target.value)}
          >
            {authorizedTenants.map((tenant) => (
              <option key={tenant} value={tenant}>
                {tenant}
              </option>
            ))}
          </select>
        </label>
      </div>
    </section>
  )
}
