import json
import os
from pathlib import Path
from typing import Any


class Config:
    _data: dict = {}
    _path: Path = None

    def __init__(self):
        config_dir = Path.home() / ".config" / "ibm-dmt"
        config_dir.mkdir(parents=True, exist_ok=True)
        self._path = config_dir / "config.json"
        self._sessions_dir = config_dir / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self.load()

    @property
    def sessions_dir(self) -> Path:
        return self._sessions_dir

    def load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        target = self._data
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save()

    def remove(self, key: str) -> None:
        keys = key.split(".")
        target = self._data
        for k in keys[:-1]:
            if k not in target:
                return
            target = target[k]
        target.pop(keys[-1], None)
        self.save()
