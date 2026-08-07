// Allow policy downloads during the tenant's configured business hours.
permit(
    principal,
    action == Action::"DownloadPolicy, this has been edited",
    resource
)
when {
    principal.tenantId == resource.tenantId &&
    context.hour >= 9 &&
    context.hour < 17
};
