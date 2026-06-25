from abc import ABC, abstractmethod
from typing import Optional


class DatabaseConnector(ABC):
    name: str = ""
    display_name: str = ""
    default_port: int = 0

    @abstractmethod
    def detect(self) -> bool:
        pass

    @abstractmethod
    def connect(self, host: str, port: int, user: str, password: str) -> bool:
        pass

    @abstractmethod
    def list_databases(self) -> list[str]:
        pass

    @abstractmethod
    def dump(self, database: str, output_path: str, backup_type: str = "full",
             host: str = "localhost", port: Optional[int] = None,
             user: str = None, password: str = None) -> str:
        pass

    @abstractmethod
    def get_server_version(self) -> str:
        pass

    def get_default_port(self) -> int:
        return self.default_port
