"""Unit tests for the services without HTTP: redaction, audit retries, mapping."""

from datetime import datetime, timezone

from app.services.audit_service import AuditService
from app.services.mapping import plan_details, to_ask_response
from app.services.redaction import redact, redact_text, sanitize_headers
from tests.conftest import FakeRuns, make_result


def test_redact_text_masks_email_and_card():
    text = redact_text("mail a.b@acme.com, card 4111 1111 1111 1111 ok")
    assert "a.b@acme.com" not in text and "4111" not in text
    assert "[REDACTED_EMAIL]" in text and "[REDACTED_CREDIT_CARD]" in text


def test_redact_is_recursive_and_keeps_types():
    data = {"q": "x@y.com", "n": 3, "items": ["z@w.org", {"deep": "a@b.co"}], "none": None}
    out = redact(data)
    assert out["n"] == 3 and out["none"] is None
    assert "@" not in str(out)


def test_sanitize_headers():
    out = sanitize_headers({"X-API-Key": "secret", "Authorization": "Bearer t", "Accept": "json"})
    assert out == {"X-API-Key": "[REDACTED]", "Authorization": "[REDACTED]", "Accept": "json"}


class FlakyLogs:
    def __init__(self, failures: int) -> None:
        self.failures, self.calls, self.entries = failures, 0, []

    async def add(self, entry):
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectionError("db down")
        self.entries.append(entry)


async def test_audit_retries_then_succeeds():
    logs = FlakyLogs(failures=2)
    audit = AuditService(logs, FakeRuns(), attempts=3, max_wait=0.01)
    assert await audit.log_request({"id": "1", "request_body": {"q": "me@x.com"}}) is True
    assert logs.calls == 3
    assert logs.entries[0]["request_body"]["q"] == "[REDACTED_EMAIL]"


async def test_audit_failure_never_raises():
    logs = FlakyLogs(failures=99)
    audit = AuditService(logs, FakeRuns(), attempts=3, max_wait=0.01)
    assert await audit.log_request({"id": "1"}) is False
    assert logs.calls == 3


def test_plan_details_groups_versions():
    result = make_result("q", "bob")
    details = plan_details(result.plan, result.plan_rationales)
    assert [v["version"] for v in details["versions"]] == [1, 2]
    assert details["replans"] == 1
    assert "status" not in details["versions"][0]["steps"][0]  # plan = intent; outcomes are in executed_plan


def test_plan_details_none_for_react():
    assert plan_details([], {}) is None


def test_to_ask_response_maps_cache_hit():
    result = make_result("q", "alice", status="cache_hit")
    result.cache_similarity, result.cached_question = 0.95, "similar q"
    now = datetime.now(timezone.utc)
    response = to_ask_response(run_id="r1", run_status="completed", result=result, include_trace=True,
                               started_at=now, finished_at=now, total_s=1.0, queued_s=0.0)
    assert response.cache.hit is True and response.cache.similarity == 0.95
    assert response.user.role == "guest"
