import os
import shutil
from pathlib import Path

import pytest
from dotenv import dotenv_values

from app.services import CedarValidationError, GitStorageService


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def configured_cedar_executable() -> str | None:
    configured = os.getenv("CEDAR_EXECUTABLE") or dotenv_values(
        BACKEND_ROOT / ".env"
    ).get("CEDAR_EXECUTABLE")
    if configured:
        configured_path = Path(configured)
        if configured_path.is_file():
            return str(configured_path)
        return shutil.which(configured)
    return shutil.which("cedar")


@pytest.mark.integration
def test_real_cedar_cli_accepts_valid_and_rejects_invalid_policy(monkeypatch):
    cedar_executable = configured_cedar_executable()
    if not cedar_executable:
        pytest.skip("Cedar CLI is not configured")
    monkeypatch.setenv("CEDAR_EXECUTABLE", cedar_executable)

    GitStorageService.validate_cedar_syntax(
        "permit(principal, action, resource);"
    )

    with pytest.raises(CedarValidationError, match="unexpected token"):
        GitStorageService.validate_cedar_syntax(
            "permit(principal action, resource);"
        )
