import os
from pathlib import Path
from github import Github, GithubException
from ibm_dmt.modules.database_backup.destinations.base import BackupDestination
from ibm_dmt.core.logger import Logger
from ibm_dmt.core.credential_store import CredentialStore


class GitHubDestination(BackupDestination):
    name = "github"

    def __init__(self, token: str = None, repo_name: str = "backups"):
        self._log = Logger.get_logger()
        self._creds = CredentialStore()
        self.token = token
        self.repo_name = repo_name
        self._gh: Github = None
        self._repo = None

    def _authenticate(self) -> bool:
        if self._gh:
            return True
        try:
            self.token = self.token or self._creds.get("github").get("token", "")
            if not self.token:
                self._log.error("GitHub token not configured")
                return False
            self._gh = Github(self.token)
            self._gh.get_user().login
            return True
        except Exception as e:
            self._log.error(f"GitHub auth failed: {e}")
            return False

    def _ensure_repo(self) -> bool:
        if self._repo:
            return True
        try:
            user = self._gh.get_user()
            try:
                self._repo = user.get_repo(self.repo_name)
            except GithubException:
                self._repo = user.create_repo(
                    self.repo_name,
                    description="IBM-DMT automated backups",
                    private=True,
                    auto_init=True,
                )
                self._log.info(f"Created repository: {self.repo_name}")
            return True
        except Exception as e:
            self._log.error(f"Failed to ensure GitHub repo: {e}")
            return False

    def upload(self, file_paths: list[str], session_name: str,
               server_ip: str, timestamp: str, metadata: dict) -> bool:
        if not self._authenticate():
            return False
        if not self._ensure_repo():
            return False

        db_type = metadata.get("db_type", "unknown")
        all_ok = True

        for fp in file_paths:
            path = Path(fp)
            remote_path = f"databases/{db_type}/{session_name}_{server_ip}/{timestamp}/{path.name}"

            try:
                with open(path, "rb") as f:
                    content = f.read()

                try:
                    contents = self._repo.get_contents(remote_path)
                    self._repo.update_file(remote_path, f"Update {path.name}", content, contents.sha)
                except GithubException:
                    self._repo.create_file(remote_path, f"Add {path.name}", content)

                self._log.info(f"GitHub upload OK: {remote_path}")
            except Exception as e:
                self._log.error(f"GitHub upload failed for {remote_path}: {e}")
                all_ok = False

        return all_ok

    def verify(self, destination_path: str) -> bool:
        if not self._authenticate():
            return False
        if not self._ensure_repo():
            return False
        try:
            self._repo.get_contents(destination_path)
            return True
        except GithubException:
            return False

    def list_backups(self, session_name: str = None, db_type: str = None) -> list:
        if not self._authenticate() or not self._ensure_repo():
            return []
        try:
            base = "databases"
            if db_type:
                base = f"{base}/{db_type}"
            if session_name:
                base = f"{base}/{session_name}"

            contents = self._repo.get_contents(base)
            result = []
            for c in contents:
                if c.type == "dir":
                    for sub in self._repo.get_contents(c.path):
                        result.append({
                            "path": sub.path,
                            "name": sub.name,
                            "type": sub.type,
                            "url": sub.html_url,
                        })
                else:
                    result.append({
                        "path": c.path,
                        "name": c.name,
                        "type": c.type,
                        "url": c.html_url,
                    })
            return result
        except GithubException:
            return []

    def get_config_widget(self):
        return None
