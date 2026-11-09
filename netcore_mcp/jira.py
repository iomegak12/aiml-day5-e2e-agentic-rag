"""Jira Cloud REST v3 client (httpx async, Basic auth = account email + API token)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from netcore_mcp.config import McpSettings
from netcore_mcp.schemas import JIRA_PRIORITY

RETRY_STATUSES = {429, 502, 503, 504}


class JiraError(Exception):
    """Any Jira failure; the message is safe to store on the ticket (no credentials)."""


@dataclass(frozen=True)
class JiraIssue:
    id: str
    key: str
    url: str


def _paragraph(text: str, bold: bool = False) -> dict:
    node: dict[str, Any] = {"type": "text", "text": text}
    if bold:
        node["marks"] = [{"type": "strong"}]
    return {"type": "paragraph", "content": [node]}


def adf(*paragraphs: str, header: str | None = None) -> dict:
    """Plain text -> Atlassian Document Format (one paragraph per non-empty line)."""
    content = [_paragraph(header, bold=True)] if header else []
    for block in paragraphs:
        content += [_paragraph(line) for line in block.splitlines() if line.strip()]
    return {"type": "doc", "version": 1, "content": content or [_paragraph("-")]}


def _label(value: str) -> str:
    return "-".join(value.lower().split())  # Jira labels cannot contain spaces


def issue_fields(ticket: Any, settings: McpSettings) -> dict:
    """The Jira create payload for a ticket: summary, ADF description with a header, priority and labels."""
    header = (f"{ticket.ticket_id} | Registered by: {ticket.registered_by} | Severity: {ticket.severity} | "
              f"Product: {ticket.product_family} | Region: {ticket.region}")
    return {
        "project": {"key": settings.jira_project_key},
        "issuetype": {"name": settings.jira_issue_type},
        "summary": f"[{ticket.ticket_id}] {ticket.title}"[:255],
        "description": adf(ticket.description, header=header),
        "priority": {"name": JIRA_PRIORITY[ticket.severity]},
        "labels": ["netcore-assist", _label(ticket.product_family), _label(ticket.region),
                   f"user-{_label(ticket.registered_by)}"],
    }


class JiraClient:
    def __init__(self, settings: McpSettings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self._http = httpx.AsyncClient(
            base_url=settings.atlassian_site_url or "http://jira.invalid",
            auth=(settings.atlassian_email, settings.atlassian_api_token),
            headers={"Accept": "application/json"},
            timeout=settings.jira_timeout_seconds,
            transport=transport,
        )

    @property
    def enabled(self) -> bool:
        return self.settings.jira_enabled

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """One retry on network errors and 429/5xx; raises JiraError with a short, credential-free message."""
        if not self.enabled:
            raise JiraError("Jira is not configured (ATLASSIAN_SITE_URL / ATLASSIAN_EMAIL / ATLASSIAN_API_TOKEN)")
        for attempt in (1, 2):
            try:
                response = await self._http.request(method, path, **kwargs)
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise JiraError(f"Jira unreachable: {type(exc).__name__}") from exc
            else:
                if response.status_code not in RETRY_STATUSES or attempt == 2:
                    break
            await asyncio.sleep(1.0)
        if response.is_error:
            raise JiraError(f"Jira {method} {path} -> HTTP {response.status_code}: {_error_text(response)}")
        return response

    async def create_issue(self, ticket: Any) -> JiraIssue:
        data = (await self._request("POST", "/rest/api/3/issue",
                                    json={"fields": issue_fields(ticket, self.settings)})).json()
        key = data["key"]
        return JiraIssue(id=str(data["id"]), key=key, url=f"{self.settings.atlassian_site_url}/browse/{key}")

    async def add_comment(self, key: str, text: str, header: str | None = None) -> str:
        data = (await self._request("POST", f"/rest/api/3/issue/{key}/comment",
                                    json={"body": adf(text, header=header)})).json()
        return str(data["id"])

    async def resolve(self, key: str) -> str:
        """Move the issue with the transition named JIRA_RESOLVE_TRANSITION (or one leading to that status)."""
        wanted = self.settings.jira_resolve_transition.lower()
        transitions = (await self._request("GET", f"/rest/api/3/issue/{key}/transitions")).json()["transitions"]
        match = next((t for t in transitions if t["name"].lower() == wanted
                      or t.get("to", {}).get("name", "").lower() == wanted), None)
        if match is None:
            names = ", ".join(t["name"] for t in transitions) or "none"
            raise JiraError(f"No '{self.settings.jira_resolve_transition}' transition for {key} (available: {names})")
        await self._request("POST", f"/rest/api/3/issue/{key}/transitions", json={"transition": {"id": match["id"]}})
        return match.get("to", {}).get("name") or match["name"]


def _error_text(response: httpx.Response) -> str:
    try:
        body = response.json()
        parts = list(body.get("errorMessages", [])) + [f"{k}: {v}" for k, v in body.get("errors", {}).items()]
        return "; ".join(parts)[:300] or response.reason_phrase
    except ValueError:
        return response.text[:200] or response.reason_phrase
