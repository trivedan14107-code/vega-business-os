"""Encryption boundary for OAuth tokens stored by the platform."""

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class TokenVaultError(ValueError):
    pass


class TokenVault:
    def __init__(self, encryption_key: str) -> None:
        try:
            self._cipher = Fernet(encryption_key.encode("ascii"))
        except (TypeError, ValueError) as exc:
            raise TokenVaultError("TOKEN_ENCRYPTION_KEY is invalid") from exc

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("ascii")

    def encrypt(self, token: dict[str, Any]) -> str:
        payload = json.dumps(token, separators=(",", ":")).encode("utf-8")
        return self._cipher.encrypt(payload).decode("ascii")

    def decrypt(self, encrypted_token: str) -> dict[str, Any]:
        try:
            payload = self._cipher.decrypt(encrypted_token.encode("ascii"))
        except InvalidToken as exc:
            raise TokenVaultError("Stored OAuth token could not be decrypted") from exc
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise TokenVaultError("Stored OAuth token has an invalid shape")
        return value
