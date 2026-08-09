import os
import subprocess
from types import SimpleNamespace

import pytest

from app.services import (
    CedarValidationError,
    CedarValidatorUnavailableError,
    GitStorageService,
)


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
    assert git_service.read_policy(tenant, filename, first_hash) == first_content
    assert git_service.read_policy(tenant, filename, second_hash) == second_content

    _, full_path = git_service._get_paths(tenant, filename)
    assert full_path.is_file()

    history = git_service.policy_history(tenant, filename)
    assert [entry["commit_hash"] for entry in history] == [second_hash, first_hash]
    assert all(entry["date"] is not None for entry in history)

    delete_hash = git_service.delete_policy(tenant, filename)
    assert len(delete_hash) == 40
    assert not full_path.exists()
    assert git_service.policy_history(tenant, filename)[0]["commit_hash"] == delete_hash


def test_git_storage_reports_missing_commit_content(git_service):
    with pytest.raises(FileNotFoundError, match="Git commit"):
        git_service.read_policy(
            "tenant_A",
            "missing.cedar",
            "not-a-real-commit",
        )


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


def test_git_storage_initializes_missing_repository(git_service):
    repo_path = git_service.repo_path.parent / "automatically_initialized"

    initialized_service = GitStorageService(repo_path)
    commit_hash = initialized_service.write_policy(
        "tenant_A",
        "first-policy.cedar",
        "permit(principal, action, resource);",
    )

    assert (repo_path / ".git").is_dir()
    assert len(commit_hash) == 40
    with initialized_service.repo.config_reader() as config:
        assert config.get_value("user", "name") == (
            "SmartVerify Policy Service"
        )


def test_git_storage_delete_nonexistent_policy(git_service):
    with pytest.raises(FileNotFoundError):
        git_service.delete_policy("tenant_A", "nonexistent_file_999.cedar")


def test_cedar_syntax_validation_reports_missing_cli(monkeypatch):
    monkeypatch.delenv("CEDAR_EXECUTABLE", raising=False)
    monkeypatch.setattr("app.services.shutil.which", lambda _: None)

    with pytest.raises(
        CedarValidatorUnavailableError,
        match="CEDAR_EXECUTABLE",
    ):
        GitStorageService.validate_cedar_syntax("permit();")


def test_cedar_syntax_validation_accepts_valid_policy_and_removes_temp_file(
    monkeypatch,
):
    observed = {}
    monkeypatch.setenv("CEDAR_EXECUTABLE", "cedar-test")

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        observed["temp_exists_during_call"] = os.path.exists(command[-1])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.services.subprocess.run", fake_run)

    assert GitStorageService.validate_cedar_syntax("permit();") is None
    assert observed["command"][:3] == ["cedar-test", "check-parse", "-p"]
    assert observed["temp_exists_during_call"] is True
    assert observed["kwargs"]["timeout"] == 10
    assert observed["kwargs"]["encoding"] == "utf-8"
    assert observed["kwargs"]["errors"] == "replace"
    assert not os.path.exists(observed["command"][-1])


def test_cedar_syntax_validation_returns_actionable_parser_error(monkeypatch):
    observed = {}
    monkeypatch.setenv("CEDAR_EXECUTABLE", "cedar-test")

    def fake_run(command, **_):
        observed["temp_path"] = command[-1]
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr=f"{command[-1]}:4:12 unexpected token `}}`",
        )

    monkeypatch.setattr("app.services.subprocess.run", fake_run)

    with pytest.raises(
        CedarValidationError,
        match=r"uploaded policy:4:12 unexpected token",
    ):
        GitStorageService.validate_cedar_syntax("permit();")
    assert not os.path.exists(observed["temp_path"])


def test_cedar_syntax_validation_reports_timeout_and_removes_temp_file(monkeypatch):
    observed = {}
    monkeypatch.setenv("CEDAR_EXECUTABLE", "cedar-test")

    def fake_run(command, **_):
        observed["temp_path"] = command[-1]
        raise subprocess.TimeoutExpired(command, timeout=10)

    monkeypatch.setattr("app.services.subprocess.run", fake_run)

    with pytest.raises(CedarValidatorUnavailableError, match="timed out"):
        GitStorageService.validate_cedar_syntax("permit();")
    assert not os.path.exists(observed["temp_path"])


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (OSError("not executable"), "Unable to execute"),
        (subprocess.SubprocessError("process failed"), "failed to run"),
    ],
)
def test_cedar_syntax_validation_reports_process_errors(
    monkeypatch,
    error,
    message,
):
    monkeypatch.setenv("CEDAR_EXECUTABLE", "cedar-test")
    monkeypatch.setattr(
        "app.services.subprocess.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
    )

    with pytest.raises(CedarValidatorUnavailableError, match=message):
        GitStorageService.validate_cedar_syntax("permit();")


def test_cedar_syntax_validation_handles_temp_file_failure(monkeypatch):
    monkeypatch.setenv("CEDAR_EXECUTABLE", "cedar-test")
    monkeypatch.setattr(
        "app.services.tempfile.NamedTemporaryFile",
        lambda **_kwargs: (_ for _ in ()).throw(
            OSError("temporary directory unavailable")
        ),
    )

    with pytest.raises(
        CedarValidatorUnavailableError,
        match="Unable to execute",
    ):
        GitStorageService.validate_cedar_syntax("permit();")
