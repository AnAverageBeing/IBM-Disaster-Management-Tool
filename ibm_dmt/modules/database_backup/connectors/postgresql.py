import subprocess
import socket
from typing import Optional
from ibm_dmt.modules.database_backup.connectors.base import DatabaseConnector
from ibm_dmt.core.logger import Logger


class PostgreSQLConnector(DatabaseConnector):
    name = "postgresql"
    display_name = "PostgreSQL"
    default_port = 5432

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
            result = subprocess.run(["psql", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self._version = result.stdout.strip()
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        try:
            with socket.create_connection(("localhost", self.default_port), timeout=2):
                self._version = "PostgreSQL detected on port 5432"
                return True
        except (OSError, socket.timeout):
            pass
        return False

    def connect(self, host: str, port: int, user: str, password: str) -> bool:
        try:
            import psycopg2
            conn = psycopg2.connect(host=host, port=port, user=user,
                                    password=password, connect_timeout=5)
            self._version = f"{conn.server_version}"
            self._host = host
            self._port = port
            self._user = user
            self._password = password
            self._connected = True
            conn.close()
            return True
        except Exception as e:
            self._log.error(f"PostgreSQL connection failed: {e}")
            return False

    def list_databases(self) -> list[str]:
        if not self._connected:
            return []
        try:
            import psycopg2
            conn = psycopg2.connect(host=self._host, port=self._port,
                                    user=self._user, password=self._password)
            cursor = conn.cursor()
            cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
            dbs = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return dbs
        except Exception as e:
            self._log.error(f"Failed to list PostgreSQL databases: {e}")
            return []

    def dump(self, database: str, output_path: str, backup_type: str = "full",
             host: str = "localhost", port: Optional[int] = None,
             user: str = None, password: str = None) -> str:
        env = {}
        if password:
            env["PGPASSWORD"] = password

        cmd = ["pg_dump", "-h", host, "-p", str(port or self.default_port)]
        if user:
            cmd.extend(["-U", user])

        if backup_type == "full":
            cmd.append("--all-databases")
        elif backup_type == "incremental":
            cmd.extend(["--format=custom", database])
        else:
            cmd.extend(["--format=custom", database])

        with open(output_path, "w") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env, check=True)
        return output_path

    def get_server_version(self) -> str:
        return self._version
