from abc import ABC, abstractmethod
from typing import Optional


class BackupDestination(ABC):
    name: str = ""

    @abstractmethod
    def upload(self, file_paths: list[str], session_name: str,
               server_ip: str, timestamp: str, metadata: dict) -> bool:
        pass

    @abstractmethod
    def verify(self, destination_path: str) -> bool:
        pass

    @abstractmethod
    def get_config_widget(self):
        pass
