"""MCP server settings (root .env via pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from netcore_mcp import PROJECT_ROOT


class McpSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    mcp_host: str = "0.0.0.0"
    mcp_port: int = 9090
    database_url: str = "postgresql+asyncpg://netcore:netcore@localhost:5432/netcore_api"

    # Jira Cloud (Basic auth = account email + API token)
    atlassian_site_url: str = ""
    atlassian_email: str = ""
    atlassian_api_token: str = ""
    jira_project_key: str = "KAN"
    jira_issue_type: str = "Incident"
    jira_resolve_transition: str = "Resolved"  # transition (or target status) name used by resolve_ticket
    jira_timeout_seconds: float = 15.0
    jira_sync_interval_seconds: int = 60  # background retry of tickets whose Jira sync is pending; 0 = off

    log_level: str = "INFO"

    @field_validator("atlassian_site_url")
    @classmethod
    def _strip_slash(cls, v: str) -> str:
        return v.strip().rstrip("/")

    @property
    def jira_enabled(self) -> bool:
        return bool(self.atlassian_site_url and self.atlassian_email and self.atlassian_api_token)


@lru_cache(maxsize=1)
def get_settings() -> McpSettings:
    return McpSettings()
