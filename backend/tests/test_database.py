import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import models
from app import database


def test_database_connection_valid(db_session):
    assert db_session.execute(text("SELECT 1")).scalar_one() == 1


def test_policy_model_creation_valid(db_session):
    policy = models.PolicyMetadata(
        tenant_id="tenant_A",
        filename="valid_db.cedar",
        git_hash="hash123",
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    assert policy.id is not None
    assert policy.tenant_id == "tenant_A"
    assert policy.filename == "valid_db.cedar"
    assert policy.created_at is not None


@pytest.mark.parametrize("missing_field", ["tenant_id", "filename", "git_hash"])
def test_policy_model_rejects_missing_required_fields(db_session, missing_field):
    values = {
        "tenant_id": "tenant_A",
        "filename": "policy.cedar",
        "git_hash": "hash",
    }
    values[missing_field] = None
    db_session.add(models.PolicyMetadata(**values))

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_policy_model_enforces_unique_tenant_filename(db_session):
    db_session.add_all(
        [
            models.PolicyMetadata(
                tenant_id="tenant_A",
                filename="duplicate.cedar",
                git_hash="hash-1",
            ),
            models.PolicyMetadata(
                tenant_id="tenant_A",
                filename="duplicate.cedar",
                git_hash="hash-2",
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_get_db_closes_session(monkeypatch):
    class FakeSession:
        closed = False

        def close(self):
            self.closed = True

    session = FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)

    dependency = database.get_db()
    assert next(dependency) is session
    dependency.close()

    assert session.closed is True


def test_database_url_is_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL")

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database.get_database_url()
