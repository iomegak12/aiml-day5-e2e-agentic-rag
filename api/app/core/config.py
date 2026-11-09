"""API settings (.env via pydantic-settings). Agent settings stay in scripts/agentic_rag/config.py."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import PROJECT_ROOT, __version__


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "NetCore Agentic RAG API"
    version: str = __version__
    api_host: str = "0.0.0.0"
    api_port: int = 8080

    # Authentication: "key1:alice,key2:bob,key3:carol" (API key -> demo user)
    api_keys: str = ""

    # Infrastructure
    database_url: str = "postgresql+asyncpg://netcore:netcore@localhost:5432/netcore_api"
    redis_url: str = "redis://localhost:6379"
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # Rate limiting (per client IP): N requests per 60 s window; on breach the IP is blocked for B seconds
    rate_limit_per_minute: int = 100
    rate_limit_block_seconds: int = 30
    rate_limit_exempt_paths: str = "/health,/ready,/metrics,/docs,/redoc,/openapi.json"
    trust_proxy_headers: bool = False  # use X-Forwarded-For only behind a trusted reverse proxy

    # Timeouts (seconds): per-request agent budget bounds; hard cap = budget + grace
    api_timeout_default: int = 120
    api_timeout_min: int = 10
    api_timeout_max: int = 300
    api_timeout_grace: int = 15
    agent_max_concurrency: int = 4  # worker threads running agent requests

    # SSE replay buffer (Redis Streams)
    event_buffer_ttl_seconds: int = 3600
    sse_ping_seconds: int = 15

    # Audit (Postgres)
    audit_exclude_paths: str = "/health,/ready,/metrics,/docs,/redoc,/openapi.json,/favicon.ico"
    audit_max_body_bytes: int = 65536
    db_retry_attempts: int = 3

    # Logging (JSON)
    log_level: str = "INFO"
    log_file: str = "logs/api.log"
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5

    problem_base_uri: str = Field(default="https://netcore.example/problems/",
                                  description="Base URI for RFC 9457 problem types")

    @field_validator("api_timeout_default")
    @classmethod
    def _positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("must be > 0")
        return v

    @property
    def key_map(self) -> dict[str, str]:
        """API key -> user id."""
        pairs = (item.strip().rsplit(":", 1) for item in self.api_keys.split(",") if ":" in item)
        return {key.strip(): user.strip() for key, user in pairs if key.strip()}

    @property
    def rate_limit_exempt(self) -> tuple[str, ...]:
        return tuple(p.strip() for p in self.rate_limit_exempt_paths.split(",") if p.strip())

    @property
    def audit_exclude(self) -> tuple[str, ...]:
        return tuple(p.strip() for p in self.audit_exclude_paths.split(",") if p.strip())


@lru_cache(maxsize=1)
def get_api_settings() -> ApiSettings:
    return ApiSettings()
