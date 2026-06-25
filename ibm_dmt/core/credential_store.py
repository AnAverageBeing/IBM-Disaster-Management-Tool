import json
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class CredentialStore:
    _key: bytes = None
    _store_path: Path = None

    def __init__(self):
        store_dir = Path.home() / ".config" / "ibm-dmt"
        store_dir.mkdir(parents=True, exist_ok=True)
        self._store_path = store_dir / "credentials.enc"
        self._key_path = store_dir / ".key"

    def _derive_key(self, password: str = None) -> bytes:
        if password:
            salt = b"ibm_dmt_salt_2024"
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600000)
            return base64.urlsafe_b64encode(kdf.derive(password.encode()))
        if self._key_path.exists():
            return self._key_path.read_bytes()
        key = Fernet.generate_key()
        self._key_path.write_bytes(key)
        self._key_path.chmod(0o600)
        return key

    def unlock(self, password: str = None) -> None:
        self._key = self._derive_key(password)

    def lock(self) -> None:
        self._key = None

    @property
    def is_unlocked(self) -> bool:
        return self._key is not None

    def save(self, service: str, credentials: dict) -> None:
        if not self._key:
            self.unlock()
        cipher = Fernet(self._key)
        data = {}
        if self._store_path.exists():
            try:
                encrypted = self._store_path.read_bytes()
                decrypted = cipher.decrypt(encrypted)
                data = json.loads(decrypted)
            except Exception:
                data = {}
        data[service] = credentials
        encrypted = cipher.encrypt(json.dumps(data).encode())
        self._store_path.write_bytes(encrypted)

    def get(self, service: str) -> dict:
        if not self._key:
            self.unlock()
        if not self._store_path.exists():
            return {}
        cipher = Fernet(self._key)
        try:
            encrypted = self._store_path.read_bytes()
            decrypted = cipher.decrypt(encrypted)
            data = json.loads(decrypted)
            return data.get(service, {})
        except Exception:
            return {}

    def delete(self, service: str) -> None:
        if not self._key:
            self.unlock()
        if not self._store_path.exists():
            return
        cipher = Fernet(self._key)
        try:
            encrypted = self._store_path.read_bytes()
            decrypted = cipher.decrypt(encrypted)
            data = json.loads(decrypted)
            data.pop(service, None)
            encrypted = cipher.encrypt(json.dumps(data).encode())
            self._store_path.write_bytes(encrypted)
        except Exception:
            pass
