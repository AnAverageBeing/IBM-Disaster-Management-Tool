import subprocess
from typing import Optional
from ibm_dmt.modules.database_backup.connectors.base import DatabaseConnector
from ibm_dmt.core.logger import Logger


class OracleConnector(DatabaseConnector):
    name = "oracle"
    display_name = "Oracle Database"
    default_port = 1521

    def __init__(self):
        self._log = Logger.get_logger()
        self._connected = False
        self._host = "localhost"
        self._port = self.default_port
        self._user = None
        self._password = None
        self._service_name = ""
        self._version = ""

    def detect(self) -> bool:
        try:
            result = subprocess.run(["sqlplus", "-V"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self._version = result.stderr.strip() if result.stderr else "Oracle detected"
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        try:
            import cx_Oracle
            self._version = "Oracle client library detected"
            return True
        except ImportError:
            pass
        return False

    def connect(self, host: str, port: int, user: str, password: str) -> bool:
        try:
            import cx_Oracle
            dsn = cx_Oracle.makedsn(host, port, service_name=self._service_name or "XE")
            conn = cx_Oracle.connect(user=user, password=password, dsn=dsn)
            self._version = conn.version
            self._host = host
            self._port = port
            self._user = user
            self._password = password
            self._connected = True
            conn.close()
            return True
        except Exception as e:
            self._log.error(f"Oracle connection failed: {e}")
            return False

    def list_databases(self) -> list[str]:
        if not self._connected:
            return []
        try:
            import cx_Oracle
            dsn = cx_Oracle.makedsn(self._host, self._port, service_name=self._service_name or "XE")
            conn = cx_Oracle.connect(user=self._user, password=self._password, dsn=dsn)
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM all_users ORDER BY username")
            dbs = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return dbs
        except Exception as e:
            self._log.error(f"Failed to list Oracle databases: {e}")
            return []

    def dump(self, database: str, output_path: str, backup_type: str = "full",
             host: str = "localhost", port: Optional[int] = None,
             user: str = None, password: str = None) -> str:
        dump_file = output_path.replace(".sql", ".dmp")
        log_file = output_path.replace(".sql", ".log")

        cmd = ["expdp", f"{user}/{password}@{host}:{port or self.default_port}/{self._service_name or 'XE'}",
               f"directory={database}", f"dumpfile={dump_file}", f"logfile={log_file}"]

        if backup_type == "full":
            cmd.append("full=Y")
        else:
            cmd.append(f"schemas={database}")

        subprocess.run(cmd, check=True, capture_output=True)
        return dump_file

    def get_server_version(self) -> str:
        return self._version
