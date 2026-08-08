import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from git import Repo
from git.exc import BadName, BadObject, InvalidGitRepositoryError


DEFAULT_REPOSITORY_PATH = Path(__file__).resolve().parents[2] / "policy_data_store"


class CedarValidationError(ValueError):
    """Raised when Cedar rejects a policy's syntax."""


class CedarValidatorUnavailableError(RuntimeError):
    """Raised when the Cedar CLI cannot be used."""


class GitStorageService:
    def __init__(self, repo_path: str | Path | None = None):
        configured_path = repo_path or os.getenv("POLICY_REPOSITORY_PATH")
        self.repo_path = Path(configured_path or DEFAULT_REPOSITORY_PATH).resolve()
        self.repo_path.mkdir(parents=True, exist_ok=True)
        try:
            self.repo = Repo(self.repo_path)
        except InvalidGitRepositoryError:
            # Automatic initialization keeps first-run setup to one backend
            # command while still creating a real, independent Git repository.
            self.repo = Repo.init(self.repo_path)
            with self.repo.config_writer() as config:
                config.set_value(
                    "user",
                    "name",
                    "SmartVerify Policy Service",
                )
                config.set_value(
                    "user",
                    "email",
                    "smartverify@localhost",
                )

    @staticmethod
    def _validate_path_component(value: str, field_name: str) -> None:
        # Tenant authorization is the primary boundary; rejecting path syntax
        # adds defense in depth against traversal outside the repository.
        if (
            not value
            or value in {".", ".."}
            or Path(value).name != value
            or "/" in value
            or "\\" in value
            or "\x00" in value
        ):
            raise ValueError(f"Invalid {field_name}")

    def _get_paths(self, tenant_id: str, filename: str) -> tuple[Path, Path]:
        self._validate_path_component(tenant_id, "tenant ID")
        self._validate_path_component(filename, "filename")

        tenant_folder_path = self.repo_path / tenant_id
        full_file_path = tenant_folder_path / filename
        return tenant_folder_path, full_file_path

    def _git_relative_path(self, tenant_id: str, filename: str) -> str:
        return (Path(tenant_id) / filename).as_posix()

    def write_policy(self, tenant_id: str, filename: str, content: str) -> str:
        tenant_folder_path, full_file_path = self._get_paths(tenant_id, filename)

        tenant_folder_path.mkdir(parents=True, exist_ok=True)
        full_file_path.write_text(content, encoding="utf-8")

        relative_path = self._git_relative_path(tenant_id, filename)
        self.repo.index.add([relative_path])
        # Committing every accepted mutation makes Git version history part of
        # the storage model rather than treating the repository as a folder.
        commit = self.repo.index.commit(
            f"Add/Update policy {filename} for tenant {tenant_id}"
        )

        return commit.hexsha

    def read_policy(
        self,
        tenant_id: str,
        filename: str,
        commit_hash: str | None = None,
    ) -> str:
        _, full_file_path = self._get_paths(tenant_id, filename)
        if commit_hash is None:
            return full_file_path.read_text(encoding="utf-8")

        # API reads pass the metadata hash so uncommitted filesystem changes
        # cannot silently replace the content PostgreSQL points to.
        relative_path = self._git_relative_path(tenant_id, filename)
        try:
            commit = self.repo.commit(commit_hash)
            blob = commit.tree / relative_path
            return blob.data_stream.read().decode("utf-8")
        except (BadName, BadObject, KeyError, ValueError) as error:
            raise FileNotFoundError(
                f"Policy {filename} was not found in Git commit {commit_hash}."
            ) from error

    def delete_policy(self, tenant_id: str, filename: str) -> str:
        _, full_file_path = self._get_paths(tenant_id, filename)

        if not full_file_path.is_file():
            raise FileNotFoundError(
                f"Policy file {filename} for tenant {tenant_id} does not exist."
            )

        full_file_path.unlink()

        relative_path = self._git_relative_path(tenant_id, filename)
        self.repo.index.remove([relative_path], working_tree=False)
        commit = self.repo.index.commit(
            f"Delete policy {filename} for tenant {tenant_id}"
        )

        return commit.hexsha

    def policy_history(self, tenant_id: str, filename: str) -> list[dict]:
        self._get_paths(tenant_id, filename)
        relative_path = self._git_relative_path(tenant_id, filename)
        commits = self.repo.iter_commits(paths=relative_path)
        return [
            {
                "commit_hash": commit.hexsha,
                "message": commit.message.strip(),
                "date": commit.committed_datetime,
            }
            for commit in commits
        ]

    @staticmethod
    def validate_cedar_syntax(file_content: str) -> None:
        cedar_executable = os.getenv("CEDAR_EXECUTABLE") or shutil.which("cedar")
        if not cedar_executable:
            raise CedarValidatorUnavailableError(
                "The Cedar validator is not configured. Set CEDAR_EXECUTABLE "
                "or install `cedar` on PATH."
            )

        temp_file_path = ""
        try:
            # The official CLI accepts a policy path, so a short-lived file lets
            # it validate uploaded text without persisting rejected content.
            with tempfile.NamedTemporaryFile(delete=False, suffix=".cedar") as temp_file:
                temp_file.write(file_content.encode("utf-8"))
                temp_file_path = temp_file.name

            result = subprocess.run(
                [cedar_executable, "check-parse", "-p", temp_file_path],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                parser_error = (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or f"Cedar validator exited with status {result.returncode}."
                )
                parser_error = parser_error.replace(
                    temp_file_path, "uploaded policy"
                )
                # Preserve Cedar's actionable token/location details without
                # exposing a local temp path or returning unbounded output.
                raise CedarValidationError(parser_error[:4000])
        except subprocess.TimeoutExpired as error:
            raise CedarValidatorUnavailableError(
                "Cedar validation timed out after 10 seconds."
            ) from error
        except OSError as error:
            raise CedarValidatorUnavailableError(
                f"Unable to execute the Cedar validator: {error}"
            ) from error
        except subprocess.SubprocessError as error:
            raise CedarValidatorUnavailableError(
                f"Cedar validation failed to run: {error}"
            ) from error
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
