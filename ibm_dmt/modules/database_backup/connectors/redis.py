import subprocess
import socket
from typing import Optional
from ibm_dmt.modules.database_backup.connectors.base import DatabaseConnector
from ibm_dmt.core.logger import Logger


class RedisConnector(DatabaseConnector):
    name = "redis"
    display_name = "Redis"
    default_port = 6379

    def __init__(self):
        self._log = Logger.get_logger()
        self._connected = False
        self._host = "localhost"
        self._port = self.default_port
        self._password = None
        self._version = ""

    def detect(self) -> bool:
        try:
            result = subprocess.run(["redis-server", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self._version = result.stdout.strip()
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        try:
            with socket.create_connection(("localhost", self.default_port), timeout=2):
                self._version = "Redis detected on port 6379"
                return True
        except (OSError, socket.timeout):
            pass
        return False

    def connect(self, host: str, port: int, user: str, password: str) -> bool:
        try:
            import redis as redis_client
            r = redis_client.Redis(host=host, port=port, password=password or None,
                                   socket_connect_timeout=5, decode_responses=True)
            r.ping()
            info = r.info()
            self._version = info.get("redis_version", "")
            self._host = host
            self._port = port
            self._password = password
            self._connected = True
            r.close()
            return True
        except Exception as e:
            self._log.error(f"Redis connection failed: {e}")
            return False

    def list_databases(self) -> list[str]:
        if not self._connected:
            return []
        return ["redis://default"]

    def dump(self, database: str, output_path: str, backup_type: str = "full",
             host: str = "localhost", port: Optional[int] = None,
             user: str = None, password: str = None) -> str:
        import redis as redis_client
        r = redis_client.Redis(host=host, port=port or self.default_port,
                               password=password or None, decode_responses=True)
        r.save()
        r.close()

        dump_path = output_path
        subprocess.run(["cp", "/var/lib/redis/dump.rdb", dump_path],
                       check=True, capture_output=True)
        return dump_path

    def get_server_version(self) -> str:
        return self._version
