import os   
import subprocess
import tempfile

from git import Repo

class GitStorageService:
    
    def __init__(self, repo_path: str = "../policy_data_store"):
        self.repo_path = repo_path
        self.repo = Repo(self.repo_path)

    def _get_paths(self, tenant_id: str, filename: str):
        tenant_folder_path = os.path.join(self.repo_path, tenant_id)
        full_file_path = os.path.join(tenant_folder_path, filename)
        return tenant_folder_path, full_file_path

    def write_policy(self, tenant_id: str, filename: str, content: str) -> str:
        tenant_folder_path, full_file_path = self._get_paths(tenant_id, filename)

        os.makedirs(tenant_folder_path, exist_ok=True)
        with open(full_file_path, "w") as f:
            f.write(content)

        self.repo.index.add([full_file_path])
        commit = self.repo.index.commit(f"Add/Update policy {filename} for tenant {tenant_id}")

        return commit.hexsha

    def delete_policy(self, tenant_id: str, filename: str):
        _, full_file_path = self._get_paths(tenant_id, filename)

        if not os.path.exists(full_file_path):
            raise FileNotFoundError(f"Policy file {filename} for tenant {tenant_id} does not exist.")

        os.remove(full_file_path)

        self.repo.index.remove([full_file_path])
        commit = self.repo.index.commit(f"Delete policy {filename} for tenant {tenant_id}")

        return commit.hexsha

    @staticmethod
    def validate_cedar_syntax(file_content: str) -> bool:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".cedar") as temp_file:
            temp_file.write(file_content.encode())
            temp_file_path = temp_file.name

        try:
            result = subprocess.run(
                ["cedar", "check", temp_file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result.returncode == 0:
                return True
            else:
                error_message = result.stderr.strip() or result.stdout.strip()
                raise ValueError(f"Cedar syntax validation failed: {error_message}")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)