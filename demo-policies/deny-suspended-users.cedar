// Deny every action when the customer user is suspended.
forbid(
    principal,
    action,
    resource
)
when {
    principal.suspended
};
