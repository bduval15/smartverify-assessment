import os
import subprocess
from types import SimpleNamespace

import pytest

from app.services import GitStorageService


def test_git_storage_write_read_history_and_delete(git_service):
    tenant = "tenant_A"
    filename = "service_test.cedar"
    first_content = "permit(principal, action, resource);"
    second_content = "permit(principal, action, resource) when { true };"

    first_hash = git_service.write_policy(tenant, filename, first_content)
    second_hash = git_service.write_policy(tenant, filename, second_content)

    assert len(first_hash) == 40
    assert len(second_hash) == 40
    assert first_hash != second_hash
    assert git_service.read_policy(tenant, filename) == second_content

    _, full_path = git_service._get_paths(tenant, filename)
    assert full_path.is_file()

    history = git_service.policy_history(tenant, filename)
    assert [entry["commit_hash"] for entry in history] == [second_hash, first_hash]
    assert all(entry["date"] is not None for entry in history)

    delete_hash = git_service.delete_policy(tenant, filename)
    assert len(delete_hash) == 40
    assert not full_path.exists()
    assert git_service.policy_history(tenant, filename)[0]["commit_hash"] == delete_hash


@pytest.mark.parametrize(
    ("tenant_id", "filename"),
    [
        ("", "policy.cedar"),
        ("..", "policy.cedar"),
        ("tenant_A/subtenant", "policy.cedar"),
        ("tenant_A", ""),
        ("tenant_A", ".."),
        ("tenant_A", "../outside.cedar"),
        ("tenant_A", r"folder\outside.cedar"),
    ],
)
def test_git_storage_rejects_unsafe_paths(git_service, tenant_id, filename):
    with pytest.raises(ValueError):
        git_service.write_policy(tenant_id, filename, "content")


def test_git_storage_read_nonexistent_invalid():
    repo_path = os.path.join(os.getcwd(), "missing-repository")

    with pytest.raises(FileNotFoundError):
        GitStorageService(repo_path)


def test_git_storage_delete_nonexistent_policy(git_service):
    with pytest.raises(FileNotFoundError):
        git_service.delete_policy("tenant_A", "nonexistent_file_999.cedar")


def test_cedar_syntax_validation_returns_false_when_cli_is_missing(monkeypatch):
    monkeypatch.delenv("CEDAR_EXECUTABLE", raising=False)
    monkeypatch.setattr("app.services.shutil.which", lambda _: None)

    assert GitStorageService.validate_cedar_syntax("permit();") is False


@pytest.mark.parametrize(("return_code", "expected"), [(0, True), (1, False)])
def test_cedar_syntax_validation_uses_cli_and_removes_temp_file(
    monkeypatch, return_code, expected
):
    observed = {}
    monkeypatch.setenv("CEDAR_EXECUTABLE", "cedar-test")

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        observed["temp_exists_during_call"] = os.path.exists(command[-1])
        return SimpleNamespace(returncode=return_code)

    monkeypatch.setattr("app.services.subprocess.run", fake_run)

    assert GitStorageService.validate_cedar_syntax("permit();") is expected
    assert observed["command"][:3] == ["cedar-test", "check-parse", "-p"]
    assert observed["temp_exists_during_call"] is True
    assert observed["kwargs"]["timeout"] == 10
    assert not os.path.exists(observed["command"][-1])


def test_cedar_syntax_validation_handles_cli_error_and_removes_temp_file(monkeypatch):
    observed = {}
    monkeypatch.setenv("CEDAR_EXECUTABLE", "cedar-test")

    def fake_run(command, **_):
        observed["temp_path"] = command[-1]
        raise subprocess.TimeoutExpired(command, timeout=10)

    monkeypatch.setattr("app.services.subprocess.run", fake_run)

    assert GitStorageService.validate_cedar_syntax("permit();") is False
    assert not os.path.exists(observed["temp_path"])
