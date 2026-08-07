from io import BytesIO
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError

from app import models
from app.routers import policies
from app.services import GitStorageService


TENANT = "tenant_A"
FILENAME = "failure-test.cedar"
CONTENT = "permit(principal, action, resource);"


def query_result(db, result):
    db.query.return_value.filter_by.return_value.first.return_value = result


def existing_policy():
    policy = Mock(spec=models.PolicyMetadata)
    policy.git_hash = "previous-commit"
    return policy


def policy_upload(
    filename=FILENAME,
    content=CONTENT,
):
    return UploadFile(
        filename=filename,
        file=BytesIO(content.encode("utf-8")),
    )


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
            policy_upload(),
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
            policy_upload(),
            db,
            git_service,
        ),
        500,
        "Failed to save policy metadata",
    )
    db.rollback.assert_called_once()
    git_service.delete_policy.assert_called_once_with(TENANT, FILENAME)


def test_delete_does_not_remove_file_without_metadata(git_service):
    git_service.write_policy(TENANT, FILENAME, CONTENT)
    db = Mock()
    query_result(db, None)

    assert_http_error(
        lambda: policies.delete_policy(TENANT, FILENAME, db, git_service),
        404,
        "Policy not found",
    )
    assert git_service.read_policy(TENANT, FILENAME) == CONTENT
    db.delete.assert_not_called()


def test_delete_maps_storage_failure_to_500():
    db = Mock()
    query_result(db, existing_policy())
    git_service = Mock(spec=GitStorageService)
    git_service.read_policy.return_value = CONTENT
    git_service.delete_policy.side_effect = RuntimeError("storage unavailable")

    assert_http_error(
        lambda: policies.delete_policy(TENANT, FILENAME, db, git_service),
        500,
        "Failed to delete policy",
    )


def test_delete_reports_missing_git_content():
    db = Mock()
    query_result(db, existing_policy())
    git_service = Mock(spec=GitStorageService)
    git_service.read_policy.side_effect = FileNotFoundError("missing commit")

    assert_http_error(
        lambda: policies.delete_policy(TENANT, FILENAME, db, git_service),
        404,
        "Policy file not found in Git storage",
    )


def test_delete_reports_missing_working_tree_file():
    db = Mock()
    query_result(db, existing_policy())
    git_service = Mock(spec=GitStorageService)
    git_service.read_policy.return_value = CONTENT
    git_service.delete_policy.side_effect = FileNotFoundError("missing file")

    assert_http_error(
        lambda: policies.delete_policy(TENANT, FILENAME, db, git_service),
        404,
        "Policy not found",
    )


def test_delete_reports_metadata_cleanup_failure():
    policy = existing_policy()
    db = Mock()
    query_result(db, policy)
    db.commit.side_effect = SQLAlchemyError("database unavailable")
    git_service = Mock(spec=GitStorageService)
    git_service.read_policy.return_value = CONTENT

    assert_http_error(
        lambda: policies.delete_policy(TENANT, FILENAME, db, git_service),
        500,
        "rolled back",
    )
    db.rollback.assert_called_once()
    git_service.write_policy.assert_called_once_with(TENANT, FILENAME, CONTENT)


def test_delete_preserves_original_error_when_git_restore_fails():
    db = Mock()
    query_result(db, existing_policy())
    db.commit.side_effect = SQLAlchemyError("database unavailable")
    git_service = Mock(spec=GitStorageService)
    git_service.read_policy.return_value = CONTENT
    git_service.write_policy.side_effect = RuntimeError("restore unavailable")

    assert_http_error(
        lambda: policies.delete_policy(TENANT, FILENAME, db, git_service),
        500,
        "rolled back",
    )


def test_update_maps_storage_failure_to_500():
    db = Mock()
    query_result(db, existing_policy())
    git_service = Mock(spec=GitStorageService)
    git_service.read_policy.return_value = CONTENT
    git_service.write_policy.side_effect = RuntimeError("storage unavailable")

    assert_http_error(
        lambda: policies.update_policy(
            TENANT,
            policy_upload(),
            db,
            git_service,
        ),
        500,
        "Failed to update policy",
    )


def test_update_reports_missing_git_content():
    db = Mock()
    query_result(db, existing_policy())
    git_service = Mock(spec=GitStorageService)
    git_service.read_policy.side_effect = FileNotFoundError("missing commit")

    assert_http_error(
        lambda: policies.update_policy(
            TENANT,
            policy_upload(),
            db,
            git_service,
        ),
        404,
        "Policy file not found in Git storage",
    )


def test_update_reports_metadata_failure():
    db = Mock()
    query_result(db, existing_policy())
    db.commit.side_effect = SQLAlchemyError("database unavailable")
    git_service = Mock(spec=GitStorageService)
    git_service.read_policy.return_value = CONTENT
    git_service.write_policy.side_effect = ["commit-hash", "rollback-hash"]

    assert_http_error(
        lambda: policies.update_policy(
            TENANT,
            policy_upload(),
            db,
            git_service,
        ),
        500,
        "Failed to save policy metadata",
    )
    db.rollback.assert_called_once()
    assert git_service.write_policy.call_args_list[-1].args == (
        TENANT,
        FILENAME,
        CONTENT,
    )


def test_update_preserves_original_error_when_git_restore_fails():
    db = Mock()
    query_result(db, existing_policy())
    db.commit.side_effect = SQLAlchemyError("database unavailable")
    git_service = Mock(spec=GitStorageService)
    git_service.read_policy.return_value = CONTENT
    git_service.write_policy.side_effect = [
        "commit-hash",
        RuntimeError("restore unavailable"),
    ]

    assert_http_error(
        lambda: policies.update_policy(
            TENANT,
            policy_upload(),
            db,
            git_service,
        ),
        500,
        "Failed to save policy metadata",
    )


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


def test_download_maps_unexpected_storage_failure_to_500():
    policy = Mock(spec=models.PolicyMetadata)
    db = Mock()
    query_result(db, policy)
    git_service = Mock(spec=GitStorageService)
    git_service.read_policy.side_effect = RuntimeError("storage unavailable")

    assert_http_error(
        lambda: policies.download_policy(TENANT, FILENAME, db, git_service),
        500,
        "Failed to download policy",
    )


def test_download_reports_missing_metadata():
    db = Mock()
    query_result(db, None)
    git_service = Mock(spec=GitStorageService)

    assert_http_error(
        lambda: policies.download_policy(TENANT, FILENAME, db, git_service),
        404,
        "Policy not found",
    )


def test_history_maps_storage_failure_to_500():
    git_service = Mock(spec=GitStorageService)
    git_service.policy_history.side_effect = RuntimeError("storage unavailable")

    assert_http_error(
        lambda: policies.policy_history(TENANT, FILENAME, git_service),
        500,
        "Failed to retrieve policy history",
    )
