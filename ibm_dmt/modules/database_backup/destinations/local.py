import shutil
from pathlib import Path
from ibm_dmt.modules.database_backup.destinations.base import BackupDestination
from ibm_dmt.core.logger import Logger


class LocalDestination(BackupDestination):
    name = "local"

    def __init__(self, base_path: str = None):
        self._log = Logger.get_logger()
        self.base_path = base_path or str(Path.home() / "backups")

    def upload(self, file_paths: list[str], session_name: str,
               server_ip: str, timestamp: str, metadata: dict) -> bool:
        dest_dir = Path(self.base_path) / "databases" / metadata.get("db_type", "unknown") / \
                   f"{session_name}_{server_ip}" / timestamp
        dest_dir.mkdir(parents=True, exist_ok=True)

        for fp in file_paths:
            src = Path(fp)
            dst = dest_dir / src.name
            shutil.copy2(src, dst)
            self._log.info(f"Copied {src.name} -> {dst}")

        return True

    def verify(self, destination_path: str) -> bool:
        return Path(destination_path).exists()

    def get_config_widget(self):
        return None
