"""Models exposed by the OAuth connection layer."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OAuthProvider(StrEnum):
    GOOGLE_WORKSPACE = "google_workspace"
    SLACK = "slack"


class ConnectionStatus(StrEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ConnectedApplication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: str
    provider: OAuthProvider
    status: ConnectionStatus
    scopes: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    connected_at: datetime
    account_email: str | None = None
