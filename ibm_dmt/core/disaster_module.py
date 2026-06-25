from abc import ABC, abstractmethod
from typing import Optional
from PyQt6.QtWidgets import QWidget


class DisasterModule(ABC):
    name: str = ""
    description: str = ""
    icon: str = ""
    version: str = "1.0.0"

    @abstractmethod
    def get_widget(self) -> QWidget:
        pass

    def on_activate(self) -> None:
        pass

    def on_deactivate(self) -> None:
        pass

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "version": self.version,
        }
