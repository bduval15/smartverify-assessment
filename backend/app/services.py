import os   
from git import Repo

class GitStorageService:
    def __init__(self, repo_path: str = "../policy_data_store"):
        self.repo_path = repo_path
        self.repo = Repo(self.repo_path)

    def write_policy(self, tenant_id: str, filename: str, content: str) -> str:
        tenant_folder_path = os.path.join(self.repo_path, tenant_id)
        full_file_path = os.path.join(tenant_folder_path, filename)

        os.makedirs(tenant_folder_path, exist_ok=True)
        with open(full_file_path, "w") as f:
            f.write(content)

        self.repo.index.add([full_file_path])
        commit = self.repo.index.commit(f"Add/Update policy {filename} for tenant {tenant_id}")

        return commit.hexsha

    def delete_policy(self, tenant_id: str, filename: str):


        pass

    def validate_cedar_syntax(file_content: str) -> bool:


        pass