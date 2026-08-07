// Allow tenant administrators to delete policies in their own tenant.
permit(
    principal,
    action == Action::"DeletePolicy",
    resource
)
when {
    principal.role == "admin" &&
    principal.tenantId == resource.tenantId
};
