import os
import io
import zipfile
from pathlib import Path
from typing import Optional
import requests
from ibm_dmt.modules.database_backup.destinations.base import BackupDestination
from ibm_dmt.core.logger import Logger


class DiscordDestination(BackupDestination):
    name = "discord"
    MAX_SIZE = 24_999_999  # 25MB Discord limit minus overhead

    def __init__(self, webhook_url: str = None):
        self._log = Logger.get_logger()
        self.webhook_url = webhook_url or ""

    def upload(self, file_paths: list[str], session_name: str,
               server_ip: str, timestamp: str, metadata: dict) -> bool:
        if not self.webhook_url:
            self._log.error("Discord webhook URL not configured")
            return False

        all_success = True
        for fp in file_paths:
            success = self._upload_file(fp, metadata)
            if not success:
                all_success = False

        return all_success

    def _upload_file(self, file_path: str, metadata: dict) -> bool:
        path = Path(file_path)
        file_size = path.stat().st_size

        if file_size <= self.MAX_SIZE:
            return self._send_file(path)

        return self._split_and_send(path)

    def _send_file(self, path: Path) -> bool:
        try:
            with open(path, "rb") as f:
                response = requests.post(
                    self.webhook_url,
                    files={"file": (path.name, f)},
                    timeout=120,
                )
            if response.status_code in (200, 204):
                self._log.info(f"Discord upload OK: {path.name}")
                return True
            self._log.error(f"Discord upload failed ({response.status_code}): {path.name}")
            return False
        except Exception as e:
            self._log.error(f"Discord upload error: {e}")
            return False

    def _split_and_send(self, path: Path) -> bool:
        all_ok = True
        part_num = 0
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(path, arcname=path.name)
        data = buf.getvalue()

        parts = [data[i:i + self.MAX_SIZE] for i in range(0, len(data), self.MAX_SIZE)]

        for i, part_data in enumerate(parts):
            part_name = f"{path.name}.part{i+1:03d}"
            try:
                response = requests.post(
                    self.webhook_url,
                    files={"file": (part_name, io.BytesIO(part_data))},
                    timeout=120,
                )
                if response.status_code not in (200, 204):
                    self._log.error(f"Discord part {i+1} failed: {response.status_code}")
                    all_ok = False
                else:
                    self._log.info(f"Discord part {i+1}/{len(parts)} OK: {part_name}")
            except Exception as e:
                self._log.error(f"Discord part {i+1} error: {e}")
                all_ok = False

        return all_ok

    def verify(self, destination_path: str) -> bool:
        return bool(self.webhook_url)

    def get_config_widget(self):
        return None
