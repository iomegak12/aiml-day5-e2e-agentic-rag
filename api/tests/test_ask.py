import asyncio

from tests.conftest import headers

ASK = "/api/v1/agent/ask"


async def test_ask_returns_full_details(harness, client):
    r = await client.post(ASK, json={"question": "How do I fix BFD flaps?"}, headers=headers("bob"))
    assert r.status_code == 200
    body = r.json()
    assert body["request_id"] == r.headers["x-request-id"]
    assert body["status"] == "completed" and body["agent_status"] == "answered"
    assert body["user"] == {"id": "bob", "name": "Bob", "role": "employee", "allowed_levels": ["public", "internal"]}
    # plan details: two versions (initial + one re-plan) with rationales
    assert [v["version"] for v in body["plan"]["versions"]] == [1, 2]
    assert body["plan"]["replans"] == 1
    assert body["plan"]["versions"][0]["rationale"] == "single lookup"
    # executed plan with outcomes
    assert [s["status"] for s in body["executed_plan"]] == ["no_results", "done"]
    assert body["sources"][0]["kb_id"] == "KB-NET-1005"
    assert body["judge"]["passed"] is True and body["judge"]["attempts"][0]["action"] == "accept"
    assert body["tool_calls"][0]["origin"] == "planner"
    assert body["trace"][0]["step"] == "Request"
    assert body["cache"]["hit"] is False
    assert body["timings"]["agent_s"] == 4.2 and body["timings"]["total_s"] >= 0


async def test_ask_passes_identity_and_options_to_the_agent(harness, client):
    await client.post(ASK, json={"question": "What is SLA class gold?", "mode": "react", "timeout_seconds": 20,
                                 "bypass_cache": True}, headers=headers("carol"))
    call = harness.runner.calls[-1]
    assert call == {"question": "What is SLA class gold?", "user_id": "carol", "mode": "react",
                    "timeout_seconds": 20, "bypass_cache": True}


async def test_include_trace_false_drops_trace_and_tool_calls(client):
    r = await client.post(ASK, json={"question": "What is BFD?", "include_trace": False}, headers=headers())
    body = r.json()
    assert body["trace"] == [] and body["tool_calls"] == []
    assert body["executed_plan"]  # plan details stay


async def test_react_mode_has_no_plan(client):
    body = (await client.post(ASK, json={"question": "What is BFD?", "mode": "react"}, headers=headers())).json()
    assert body["plan"] is None and body["executed_plan"] == []
    assert body["tool_calls"][0]["origin"] == "agent"


async def test_agent_error_is_503_problem_and_stored(harness, client):
    harness.runner.status = "error"
    r = await client.post(ASK, json={"question": "What is BFD?"}, headers=headers())
    assert r.status_code == 503
    body = r.json()
    assert body["type"].endswith("/agent-failed")
    run = harness.runs.rows[r.headers["x-request-id"]]
    assert run["status"] == "failed" and run["result"]["agent_status"] == "error"


async def test_agent_exception_is_503(harness, client):
    harness.runner.raises = RuntimeError("boom")
    r = await client.post(ASK, json={"question": "What is BFD?"}, headers=headers())
    assert r.status_code == 503


async def test_hard_timeout_is_504_with_result_url(harness, client):
    harness.runner.delay = 3.0
    r = await client.post(ASK, json={"question": "What is BFD?", "timeout_seconds": 1}, headers=headers())
    assert r.status_code == 504
    body = r.json()
    assert body["type"].endswith("/agent-timeout")
    assert body["result_url"] == f"/api/v1/agent/requests/{r.headers['x-request-id']}"
    assert harness.runs.rows[r.headers["x-request-id"]]["status"] == "timeout"


async def test_run_and_request_are_audited_with_pii_redacted(harness, client):
    r = await client.post(ASK, json={"question": "Mail the fix to jane.doe@acme.com please"}, headers=headers())
    await harness.container.audit.drain()
    run = harness.runs.rows[r.headers["x-request-id"]]
    assert "jane.doe@acme.com" not in run["question"] and "[REDACTED_EMAIL]" in run["question"]
    entry = next(e for e in harness.request_logs.entries if e["id"] == r.headers["x-request-id"])
    assert entry["request_headers"]["x-api-key"] == "[REDACTED]"
    assert "[REDACTED_EMAIL]" in entry["request_body"]["question"]
    assert entry["user_id"] == "bob" and entry["status_code"] == 200
    assert entry["response_body"]["request_id"] == r.headers["x-request-id"]


async def test_probes_are_not_audited(harness, client):
    await client.get("/health")
    await harness.container.audit.drain()
    assert harness.request_logs.entries == []


async def test_client_disconnect_keeps_run_and_flags_it(harness):
    """The run keeps going after the client leaves; its final status says so and the result is stored."""
    import threading

    from agentic_rag.config import DEMO_USERS
    from app.schemas.agent import AskRequest

    harness.runner.gate = threading.Event()
    service = harness.container.agent_service
    handle = await service.start(run_id="00000000-0000-0000-0000-000000000001", user=DEMO_USERS["bob"],
                                 request=AskRequest(question="What is BFD?"), client_ip="1.2.3.4", endpoint="stream")
    await asyncio.sleep(0.05)
    await service.client_left(handle.run_id)
    harness.runner.gate.set()
    outcome = await handle.task
    run = harness.runs.rows[handle.run_id]
    assert outcome.status == "client_disconnected"
    assert run["status"] == "client_disconnected" and run["client_disconnected"] is True
    assert run["result"]["answer"]
