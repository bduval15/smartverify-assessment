from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app import models
from app.routers import policies
from app.services import GitStorageService


TENANT = "tenant_A"
FILENAME = "failure-test.cedar"
CONTENT = "permit(principal, action, resource);"


def query_result(db, result):
    db.query.return_value.filter_by.return_value.first.return_value = result


def assert_http_error(call, status_code, detail):
    with pytest.raises(HTTPException) as caught:
        call()

    assert caught.value.status_code == status_code
    assert detail in caught.value.detail


def test_default_git_service_uses_configured_repository(git_service, monkeypatch):
    monkeypatch.setenv("POLICY_REPOSITORY_PATH", str(git_service.repo_path))

    configured_service = policies.get_git_service()

    assert configured_service.repo_path == git_service.repo_path


def test_upload_maps_storage_failure_to_500():
    db = Mock()
    query_result(db, None)
    git_service = Mock(spec=GitStorageService)
    git_service.write_policy.side_effect = RuntimeError("storage unavailable")

    assert_http_error(
        lambda: policies.upload_policy(
            TENANT,
            FILENAME,
            CONTENT,
            db,
            git_service,
        ),
        500,
        "Failed to write policy",
    )


def test_upload_rolls_back_database_and_storage_on_metadata_failure():
    db = Mock()
    query_result(db, None)
    db.commit.side_effect = SQLAlchemyError("database unavailable")
    git_service = Mock(spec=GitStorageService)
    git_service.write_policy.return_value = "commit-hash"
    git_service.delete_policy.side_effect = RuntimeError("cleanup unavailable")

    assert_http_error(
        lambda: policies.upload_policy(
            TENANT,
            FILENAME,
            CONTENT,
            db,
            git_service,
        ),
        500,
        "Failed to save policy metadata",
    )
    db.rollback.assert_called_once()
    git_service.delete_policy.assert_called_once_with(TENANT, FILENAME)


def test_delete_succeeds_when_file_has_no_metadata(git_service):
    git_service.write_policy(TENANT, FILENAME, CONTENT)
    db = Mock()
    query_result(db, None)

    result = policies.delete_policy(TENANT, FILENAME, db, git_service)

    assert result == {"message": "Policy deleted successfully"}
    db.delete.assert_not_called()


def test_delete_maps_storage_failure_to_500():
    db = Mock()
    git_service = Mock(spec=GitStorageService)
    git_service.delete_policy.side_effect = RuntimeError("storage unavailable")

    assert_http_error(
        lambda: policies.delete_policy(TENANT, FILENAME, db, git_service),
        500,
        "Failed to delete policy",
    )


def test_delete_reports_metadata_cleanup_failure():
    policy = Mock(spec=models.PolicyMetadata)
    db = Mock()
    query_result(db, policy)
    db.commit.side_effect = SQLAlchemyError("database unavailable")
    git_service = Mock(spec=GitStorageService)

    assert_http_error(
        lambda: policies.delete_policy(TENANT, FILENAME, db, git_service),
        500,
        "metadata cleanup failed",
    )
    db.rollback.assert_called_once()


def test_update_maps_storage_failure_to_500():
    db = Mock()
    git_service = Mock(spec=GitStorageService)
    git_service.write_policy.side_effect = RuntimeError("storage unavailable")

    assert_http_error(
        lambda: policies.update_policy(
            TENANT,
            FILENAME,
            CONTENT,
            db,
            git_service,
        ),
        500,
        "Failed to update policy",
    )


def test_update_reports_metadata_failure():
    db = Mock()
    query_result(db, None)
    db.commit.side_effect = SQLAlchemyError("database unavailable")
    git_service = Mock(spec=GitStorageService)
    git_service.write_policy.return_value = "commit-hash"

    assert_http_error(
        lambda: policies.update_policy(
            TENANT,
            FILENAME,
            CONTENT,
            db,
            git_service,
        ),
        500,
        "Failed to save policy metadata",
    )
    db.rollback.assert_called_once()


def test_content_maps_unexpected_storage_failure_to_500():
    policy = Mock(spec=models.PolicyMetadata)
    db = Mock()
    query_result(db, policy)
    git_service = Mock(spec=GitStorageService)
    git_service.read_policy.side_effect = RuntimeError("storage unavailable")

    assert_http_error(
        lambda: policies.get_policy_content(TENANT, FILENAME, db, git_service),
        500,
        "Failed to read policy",
    )


def test_history_maps_storage_failure_to_500():
    git_service = Mock(spec=GitStorageService)
    git_service.policy_history.side_effect = RuntimeError("storage unavailable")

    assert_http_error(
        lambda: policies.policy_history(TENANT, FILENAME, git_service),
        500,
        "Failed to retrieve policy history",
    )
