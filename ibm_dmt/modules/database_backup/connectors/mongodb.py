import subprocess
import socket
from typing import Optional
from ibm_dmt.modules.database_backup.connectors.base import DatabaseConnector
from ibm_dmt.core.logger import Logger


class MongoDBConnector(DatabaseConnector):
    name = "mongodb"
    display_name = "MongoDB"
    default_port = 27017

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
            result = subprocess.run(["mongod", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self._version = result.stdout.split("\n")[0]
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        try:
            with socket.create_connection(("localhost", self.default_port), timeout=2):
                self._version = "MongoDB detected on port 27017"
                return True
        except (OSError, socket.timeout):
            pass
        return False

    def connect(self, host: str, port: int, user: str, password: str) -> bool:
        try:
            import pymongo
            uri = f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin"
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
            client.server_info()
            self._version = client.server_info().get("version", "")
            self._host = host
            self._port = port
            self._user = user
            self._password = password
            self._connected = True
            client.close()
            return True
        except Exception as e:
            self._log.error(f"MongoDB connection failed: {e}")
            return False

    def list_databases(self) -> list[str]:
        if not self._connected:
            return []
        try:
            import pymongo
            uri = f"mongodb://{self._user}:{self._password}@{self._host}:{self._port}/?authSource=admin"
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
            dbs = client.list_database_names()
            exclude = {"admin", "local", "config"}
            client.close()
            return [db for db in dbs if db not in exclude]
        except Exception as e:
            self._log.error(f"Failed to list MongoDB databases: {e}")
            return []

    def dump(self, database: str, output_path: str, backup_type: str = "full",
             host: str = "localhost", port: Optional[int] = None,
             user: str = None, password: str = None) -> str:
        cmd = ["mongodump", "--host", host, "--port", str(port or self.default_port)]
        if user:
            cmd.extend(["--username", user])
        if password:
            cmd.extend(["--password", password])
        if database != "all":
            cmd.extend(["--db", database])
        cmd.extend(["--out", output_path])
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def get_server_version(self) -> str:
        return self._version
