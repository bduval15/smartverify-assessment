// Allow policy managers to upload or replace policies for their own tenant.
permit(
    principal,
    action,
    resource
)
when {
    (action == Action::"UploadPolicy" ||
     action == Action::"ReplacePolicy") &&
    principal.role == "policy-manager" &&
    principal.tenantId == resource.tenantId
};
