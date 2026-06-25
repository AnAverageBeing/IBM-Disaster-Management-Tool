import sqlite3
import subprocess
from pathlib import Path
from typing import Optional
from ibm_dmt.modules.database_backup.connectors.base import DatabaseConnector
from ibm_dmt.core.logger import Logger


class SQLiteConnector(DatabaseConnector):
    name = "sqlite"
    display_name = "SQLite"
    default_port = 0

    def __init__(self):
        self._log = Logger.get_logger()
        self._connected = False
        self._databases: list[str] = []
        self._version = ""

    def detect(self) -> bool:
        try:
            result = subprocess.run(["sqlite3", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self._version = result.stdout.strip()
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        import sqlite3
        self._version = sqlite3.sqlite_version
        return True

    def connect(self, host: str, port: int, user: str, password: str) -> bool:
        self._connected = True
        return True

    def list_databases(self) -> list[str]:
        common_paths = [
            "/var/www/html/*.db", "/var/lib/*.db", "/opt/*.db",
            "/home/*/*.db", "/tmp/*.db", "*.sqlite", "*.sqlite3",
        ]
        import glob
        dbs = set()
        for pattern in common_paths:
            for path in glob.glob(pattern):
                dbs.add(path)
        for path in glob.glob("**/*.db", recursive=True):
            dbs.add(path)
        for path in glob.glob("**/*.sqlite", recursive=True):
            dbs.add(path)
        for path in glob.glob("**/*.sqlite3", recursive=True):
            dbs.add(path)

        valid = []
        for db in dbs:
            try:
                conn = sqlite3.connect(db)
                conn.cursor().execute("SELECT 1")
                conn.close()
                valid.append(db)
            except Exception:
                pass
        self._databases = valid
        return valid

    def dump(self, database: str, output_path: str, backup_type: str = "full",
             host: str = "localhost", port: Optional[int] = None,
             user: str = None, password: str = None) -> str:
        conn = sqlite3.connect(database)
        with open(output_path, "w") as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")
        conn.close()
        return output_path

    def get_server_version(self) -> str:
        return self._version
