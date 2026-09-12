"""Environment-backed application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables or `.env.local`."""

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "Vega"
    database_url: str = "sqlite:///businessflow.db"
    groq_api_key: SecretStr | None = None
    groq_fast_model: str = "openai/gpt-oss-20b"
    groq_reasoning_model: str = "openai/gpt-oss-120b"
    app_base_url: str = "http://localhost:8000"
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    token_encryption_key: SecretStr | None = None
    session_secret: SecretStr | None = None
    default_company_id: str = "demo-company"
    owner_email: str | None = None
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    business_timezone: str = "Asia/Kolkata"
    default_meeting_duration_minutes: int = 45
    whatsapp_verify_token: SecretStr | None = None
    slack_client_id: str | None = None
    slack_client_secret: SecretStr | None = None
    slack_redirect_uri: str | None = None
    slack_default_channel_id: str | None = None

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance for the process."""

    return Settings()
