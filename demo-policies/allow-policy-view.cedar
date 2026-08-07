// Allow users to view policies belonging to their own tenant.
permit(
    principal,
    action == Action::"ViewPolicy",
    resource
)
when {
    principal.tenantId == resource.tenantId
};
