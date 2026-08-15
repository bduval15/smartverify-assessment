from typing import TypedDict

from fastapi import APIRouter, Depends, Header, HTTPException


class UserAccess(TypedDict):
    """Describe one seeded user's customer and tenant authorization scope."""

    customer_id: str
    tenant_ids: list[str]


# Keep authorization data in the backend so the browser never becomes the
# source of truth for tenant access. Users 1 and 2 intentionally share a
# customer while having different tenant scopes.
DEMO_USERS: dict[str, UserAccess] = {
    "user_1": {
        "customer_id": "customer_1",
        "tenant_ids": ["tenant_A"],
    },
    "user_2": {
        "customer_id": "customer_1",
        "tenant_ids": ["tenant_A", "tenant_B"],
    },
    "user_3": {
        "customer_id": "customer_2",
        "tenant_ids": ["tenant_C"],
    },
}

router = APIRouter(prefix="/api/users", tags=["Demo users"])


def get_current_user_access(
    user_id: str | None = Header(default=None),
) -> UserAccess:
    """Resolve a seeded user header or reject an unknown identity."""

    if user_id is None or user_id not in DEMO_USERS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return DEMO_USERS[user_id]


def get_authorized_tenants(
    user_access: UserAccess = Depends(get_current_user_access),
) -> list[str]:
    """Return the tenant IDs that the authenticated demo user may access."""

    return user_access["tenant_ids"]


@router.get("")
def list_demo_users():
    """Expose non-secret seeded access options for the demo user selector."""

    # This discovery endpoint only populates the assessment's user selector.
    # Protected routes still validate every user-id and tenant independently.
    return {
        "users": [
            {
                "user_id": user_id,
                "customer_id": access["customer_id"],
                "tenant_ids": access["tenant_ids"],
            }
            for user_id, access in DEMO_USERS.items()
        ]
    }
