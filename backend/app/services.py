import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from git import Repo
from git.exc import NoSuchPathError


DEFAULT_REPOSITORY_PATH = Path(__file__).resolve().parents[2] / "policy_data_store"


class GitStorageService:
    def __init__(self, repo_path: str | Path | None = None):
        configured_path = repo_path or os.getenv("POLICY_REPOSITORY_PATH")
        self.repo_path = Path(configured_path or DEFAULT_REPOSITORY_PATH).resolve()
        try:
            self.repo = Repo(self.repo_path)
        except NoSuchPathError as error:
            raise FileNotFoundError(
                f"Policy repository does not exist: {self.repo_path}"
            ) from error

    @staticmethod
    def _validate_path_component(value: str, field_name: str) -> None:
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
        commit = self.repo.index.commit(
            f"Add/Update policy {filename} for tenant {tenant_id}"
        )

        return commit.hexsha

    def read_policy(self, tenant_id: str, filename: str) -> str:
        _, full_file_path = self._get_paths(tenant_id, filename)
        return full_file_path.read_text(encoding="utf-8")

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
    def validate_cedar_syntax(file_content: str) -> bool:
        cedar_executable = os.getenv("CEDAR_EXECUTABLE") or shutil.which("cedar")
        if not cedar_executable:
            return False

        temp_file_path = ""
        try:
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
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
