"""Application configuration, driven entirely by environment variables.

Secrets live in `.env` (gitignored); `.env.example` documents the keys.
"""
from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "dev-insecure-change-me"
_DEFAULT_CORS_ORIGINS = "http://localhost:5173"

# Origins that are never valid for a production frontend; used to catch a
# CORS config that was left at its dev default.
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "[::1]")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"

    # Postgres (async SQLAlchemy / asyncpg)
    database_url: str = "postgresql+asyncpg://cars:cars@db:5432/cars"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # S3 / MinIO
    s3_endpoint: str = "http://minio:9000"  # in-cluster (server-side uploads)
    s3_public_endpoint: str = "http://localhost:9000"  # browser-reachable URL base
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "cars"

    # CORS — comma-separated list of allowed origins
    cors_origins: str = _DEFAULT_CORS_ORIGINS

    # Lead anti-spam: max submissions per IP within the window (seconds)
    leads_rate_limit: int = 5
    leads_rate_window: int = 60
    # Only trust X-Forwarded-For when behind a proxy that overwrites it;
    # otherwise clients can spoof the header to bypass the rate limit.
    trust_proxy: bool = False

    # Telegram notifications for new leads (optional — no-op if unset)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Auth / JWT
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 30
    # Login anti-bruteforce: attempts per IP within the window (seconds)
    login_rate_limit: int = 10
    login_rate_window: int = 60
    # Registration anti-spam: accounts per IP within the window (seconds).
    # Also blunts email enumeration via the 409 "already exists" response.
    register_rate_limit: int = 5
    register_rate_window: int = 60

    # Admin panel (SQLAdmin, issue #18). On startup the app ensures an admin
    # account with these credentials exists (created or promoted). Leave the
    # password empty to skip bootstrapping. The session cookie is signed with
    # the JWT secret.
    admin_email: str = ""
    admin_password: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @staticmethod
    def _is_local_origin(origin: str) -> bool:
        # Match by host, so http://localhost:5173 and https://127.0.0.1 both count.
        host = urlsplit(origin).hostname or origin
        return host in _LOCAL_HOSTS

    @model_validator(mode="after")
    def _require_secrets_outside_dev(self) -> "Settings":
        if self.app_env == "dev":
            return self

        # Refuse to boot with the public default JWT secret in a real env —
        # otherwise anyone could forge tokens for any user.
        if self.jwt_secret == _DEFAULT_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET must be set to a non-default value when APP_ENV != dev"
            )

        # A CORS list left at the localhost default means the production
        # frontend (on the real domains) can't call the API — fail fast with a
        # clear message instead of shipping a silently broken deploy.
        origins = self.cors_origins_list
        if not origins or all(self._is_local_origin(o) for o in origins):
            raise ValueError(
                "CORS_ORIGINS must include the production frontend origin(s) "
                "when APP_ENV != dev (currently only localhost)"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
