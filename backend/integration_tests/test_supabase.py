import os
import uuid
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy import create_engine, text


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def integration_database_url() -> str | None:
    return (
        os.getenv("SUPABASE_TEST_DATABASE_URL")
        or dotenv_values(BACKEND_ROOT / ".env").get("DATABASE_URL")
    )


@pytest.mark.integration
def test_real_postgresql_policy_metadata_round_trip():
    database_url = integration_database_url()
    if not database_url:
        pytest.skip("Supabase integration database URL is not configured")

    engine = create_engine(database_url, pool_pre_ping=True)
    policy_id = str(uuid.uuid4())
    tenant_id = f"integration_{uuid.uuid4().hex}"
    filename = "supabase-integration.cedar"

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            version = connection.execute(text("SELECT version()"))
            assert "PostgreSQL" in version.scalar_one()

            connection.execute(
                text(
                    """
                    INSERT INTO policy_metadata
                        (id, tenant_id, filename, git_hash)
                    VALUES
                        (:id, :tenant_id, :filename, :git_hash)
                    """
                ),
                {
                    "id": policy_id,
                    "tenant_id": tenant_id,
                    "filename": filename,
                    "git_hash": "integration-test-hash",
                },
            )
            stored = connection.execute(
                text(
                    """
                    SELECT tenant_id, filename, git_hash
                    FROM policy_metadata
                    WHERE id = :id
                    """
                ),
                {"id": policy_id},
            ).mappings().one()

            assert stored == {
                "tenant_id": tenant_id,
                "filename": filename,
                "git_hash": "integration-test-hash",
            }
        finally:
            transaction.rollback()
            engine.dispose()
