import uuid

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .database import Base

class PolicyMetadata(Base):
    """Index one tenant policy and the Git commit containing its content."""

    __tablename__ = "policy_metadata"

    # Cedar content is intentionally absent: Git owns content while this table
    # remains the tenant-filtered query index.
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    git_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (UniqueConstraint("tenant_id", "filename", name="uix_tenant_filename"),)
