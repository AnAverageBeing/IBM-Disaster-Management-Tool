import subprocess
import socket
from typing import Optional
from ibm_dmt.modules.database_backup.connectors.base import DatabaseConnector
from ibm_dmt.core.logger import Logger


class MariaDBConnector(DatabaseConnector):
    name = "mariadb"
    display_name = "MariaDB"
    default_port = 3306

    def __init__(self):
        self._log = Logger.get_logger()
        self._connected = False
        self._host = "localhost"
        self._port = self.default_port
        self._user = None
        self._password = None
        self._version = ""

    def detect(self) -> bool:
        try:
            result = subprocess.run(["mariadb", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and "MariaDB" in result.stdout:
                self._version = result.stdout.strip()
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        try:
            result = subprocess.run(["mysql", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and "MariaDB" in result.stdout:
                self._version = result.stdout.strip()
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False

    def connect(self, host: str, port: int, user: str, password: str) -> bool:
        try:
            import mysql.connector
            conn = mysql.connector.connect(host=host, port=port, user=user,
                                           password=password, connect_timeout=5)
            ver = conn.get_server_version()
            if isinstance(ver, tuple):
                ver = ".".join(str(v) for v in ver)
            self._version = f"MariaDB {ver}" if "maria" in conn._server_version.lower() else ver
            self._host = host
            self._port = port
            self._user = user
            self._password = password
            self._connected = True
            conn.close()
            return True
        except Exception as e:
            self._log.error(f"MariaDB connection failed: {e}")
            return False

    def list_databases(self) -> list[str]:
        if not self._connected:
            return []
        try:
            import mysql.connector
            conn = mysql.connector.connect(host=self._host, port=self._port,
                                           user=self._user, password=self._password)
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")
            dbs = [row[0] for row in cursor.fetchall()
                   if row[0] not in ("information_schema", "performance_schema", "sys", "mysql")]
            cursor.close()
            conn.close()
            return dbs
        except Exception as e:
            self._log.error(f"Failed to list MariaDB databases: {e}")
            return []

    def dump(self, database: str, output_path: str, backup_type: str = "full",
             host: str = "localhost", port: Optional[int] = None,
             user: str = None, password: str = None) -> str:
        cmd = ["mariadb-dump", "-h", host, "-P", str(port or self.default_port)]
        if user:
            cmd.extend(["-u", user])
        if password:
            cmd.extend([f"-p{password}"])

        if backup_type == "full":
            cmd.extend(["--all-databases"])
        elif backup_type == "incremental":
            cmd.extend(["--flush-logs", database])
        else:
            cmd.extend([database])

        with open(output_path, "w") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, check=True)
        return output_path

    def get_server_version(self) -> str:
        return self._version
