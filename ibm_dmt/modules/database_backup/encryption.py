import os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from ibm_dmt.core.logger import Logger


class Encryptor:
    def __init__(self):
        self._log = Logger.get_logger()

    def encrypt_file(self, input_path: str, key: bytes = None, output_path: str = None) -> str:
        if key is None:
            key = AESGCM.generate_key(bit_length=256)

        if output_path is None:
            output_path = f"{input_path}.enc"

        aesgcm = AESGCM(key)
        nonce = os.urandom(12)

        with open(input_path, "rb") as f:
            plaintext = f.read()

        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        with open(output_path, "wb") as f:
            f.write(nonce + ciphertext)

        key_path = f"{output_path}.key"
        with open(key_path, "wb") as f:
            f.write(key)

        self._log.info(f"Encrypted {input_path} -> {output_path}")
        return output_path

    def decrypt_file(self, input_path: str, key: bytes = None,
                     key_path: str = None, output_path: str = None) -> str:
        if key is None and key_path:
            with open(key_path, "rb") as f:
                key = f.read()

        if key is None:
            raise ValueError("Encryption key required for decryption")

        if output_path is None:
            output_path = input_path.replace(".enc", "")

        with open(input_path, "rb") as f:
            data = f.read()

        nonce = data[:12]
        ciphertext = data[12:]

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        with open(output_path, "wb") as f:
            f.write(plaintext)

        return output_path
