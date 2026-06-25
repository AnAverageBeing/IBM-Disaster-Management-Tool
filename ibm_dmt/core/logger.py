import logging
import sys
from pathlib import Path
from datetime import datetime


class Logger:
    _instance = None
    _logger: logging.Logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup()
        return cls._instance

    def _setup(self):
        log_dir = Path.home() / ".config" / "ibm-dmt" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        self._logger = logging.getLogger("ibm_dmt")
        self._logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s UTC | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        formatter.converter = self._utc_converter

        fh = logging.FileHandler(log_dir / f"ibm_dmt_{datetime.utcnow().strftime('%Y%m%d')}.log")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        self._logger.addHandler(fh)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        self._logger.addHandler(ch)

    @staticmethod
    def _utc_converter(*args):
        return datetime.utcnow().timetuple()

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @classmethod
    def get_logger(cls) -> logging.Logger:
        return cls()._logger
