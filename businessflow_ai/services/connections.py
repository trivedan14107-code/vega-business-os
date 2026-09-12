"""Persistent OAuth connections and internal capability discovery."""

import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from businessflow_ai.models import ConnectedApplication, ConnectionStatus, OAuthProvider
from businessflow_ai.services.token_vault import TokenVault

SCOPE_CAPABILITIES = {
    OAuthProvider.GOOGLE_WORKSPACE: {
        "openid": {"workspace.profile.read"},
        "email": {"workspace.profile.read"},
        "profile": {"workspace.profile.read"},
        "https://www.googleapis.com/auth/userinfo.email": {"workspace.profile.read"},
        "https://www.googleapis.com/auth/userinfo.profile": {"workspace.profile.read"},
        "https://www.googleapis.com/auth/calendar.readonly": {"calendar.read"},
        "https://www.googleapis.com/auth/calendar.events": {
            "calendar.read",
            "calendar.create",
            "google_meet.create",
        },
        "https://www.googleapis.com/auth/spreadsheets": {
            "sheets.read",
            "sheets.append",
        },
        "https://www.googleapis.com/auth/gmail.send": {"gmail.send"},
    },
    OAuthProvider.SLACK: {
        "channels:read": {"slack.channels.read"},
        "groups:read": {"slack.channels.read"},
        "chat:write": {"slack.send"},
    },
}


def capabilities_for_scopes(
    provider: OAuthProvider, scopes: list[str]
) -> list[str]:
    capabilities: set[str] = set()
    scope_map = SCOPE_CAPABILITIES[provider]
    for scope in scopes:
        capabilities.update(scope_map.get(scope, set()))
    return sorted(capabilities)


class OAuthStateError(ValueError):
    pass


class ConnectionStore:
    def __init__(self, database_path: str | Path, token_vault: TokenVault) -> None:
        self.database_path = str(database_path)
        self.token_vault = token_vault
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS oauth_states (
                    state TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    code_verifier TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_connections (
                    company_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    encrypted_token TEXT NOT NULL,
                    scopes TEXT NOT NULL,
                    account_email TEXT,
                    status TEXT NOT NULL,
                    connected_at TEXT NOT NULL,
                    PRIMARY KEY(company_id, provider)
                );
                """
            )

    def create_oauth_state(
        self, company_id: str, provider: OAuthProvider, code_verifier: str
    ) -> str:
        state = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO oauth_states VALUES (?, ?, ?, ?, ?)",
                (state, company_id, provider.value, code_verifier, expires_at.isoformat()),
            )
        return state

    def consume_oauth_state(
        self, state: str, provider: OAuthProvider
    ) -> tuple[str, str]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM oauth_states WHERE state = ? AND provider = ?",
                (state, provider.value),
            ).fetchone()
            connection.execute("DELETE FROM oauth_states WHERE state = ?", (state,))

        if row is None:
            raise OAuthStateError("OAuth state is invalid or already used")
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(UTC):
            raise OAuthStateError("OAuth state has expired")
        return row["company_id"], row["code_verifier"]

    def save_connection(
        self,
        company_id: str,
        provider: OAuthProvider,
        token: dict[str, Any],
        scopes: list[str],
        account_email: str | None,
    ) -> ConnectedApplication:
        connected_at = datetime.now(UTC)
        encrypted = self.token_vault.encrypt(token)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO oauth_connections
                (company_id, provider, encrypted_token, scopes, account_email, status, connected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    provider.value,
                    encrypted,
                    " ".join(scopes),
                    account_email,
                    ConnectionStatus.CONNECTED.value,
                    connected_at.isoformat(),
                ),
            )
        return self.get_connection(company_id, provider)

    def get_connection(
        self, company_id: str, provider: OAuthProvider
    ) -> ConnectedApplication:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM oauth_connections WHERE company_id = ? AND provider = ?",
                (company_id, provider.value),
            ).fetchone()
        if row is None:
            raise KeyError(f"{provider.value} is not connected")
        scopes = row["scopes"].split()
        return ConnectedApplication(
            company_id=company_id,
            provider=provider,
            status=ConnectionStatus(row["status"]),
            scopes=scopes,
            capabilities=capabilities_for_scopes(provider, scopes),
            connected_at=datetime.fromisoformat(row["connected_at"]),
            account_email=row["account_email"],
        )

    def get_token(self, company_id: str, provider: OAuthProvider) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT encrypted_token FROM oauth_connections "
                "WHERE company_id = ? AND provider = ?",
                (company_id, provider.value),
            ).fetchone()
        if row is None:
            raise KeyError(f"{provider.value} is not connected")
        return self.token_vault.decrypt(row["encrypted_token"])

    def update_token(
        self, company_id: str, provider: OAuthProvider, token: dict[str, Any]
    ) -> None:
        """Replace an encrypted OAuth token without changing connection metadata."""
        encrypted = self.token_vault.encrypt(token)
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE oauth_connections SET encrypted_token = ? "
                "WHERE company_id = ? AND provider = ?",
                (encrypted, company_id, provider.value),
            )
        if cursor.rowcount != 1:
            raise KeyError(f"{provider.value} is not connected")

    def list_connections(self, company_id: str) -> list[ConnectedApplication]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT provider FROM oauth_connections WHERE company_id = ? ORDER BY provider",
                (company_id,),
            ).fetchall()
        return [
            self.get_connection(company_id, OAuthProvider(row["provider"])) for row in rows
        ]

    def available_capabilities(self, company_id: str) -> set[str]:
        available: set[str] = set()
        for connection in self.list_connections(company_id):
            if connection.status != ConnectionStatus.CONNECTED:
                continue
            capabilities = set(connection.capabilities)
            if connection.provider == OAuthProvider.SLACK:
                token = self.get_token(company_id, OAuthProvider.SLACK)
                if not token.get("default_channel_id"):
                    capabilities.discard("slack.send")
            available.update(capabilities)
        return available
