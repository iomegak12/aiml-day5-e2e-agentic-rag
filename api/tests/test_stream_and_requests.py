from tests.conftest import headers, parse_sse

STREAM = "/api/v1/agent/ask/stream"
REQUESTS = "/api/v1/agent/requests"


async def _stream(client, user="bob", **body):
    r = await client.post(STREAM, json={"question": "How do I fix BFD flaps?", **body}, headers=headers(user))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    return r.headers["x-request-id"], parse_sse(r.text)


async def test_stream_emits_events_in_order(client):
    run_id, events = await _stream(client)
    types = [e["event"] for e in events]
    assert types[0] == "accepted" and types[-2:] == ["result", "done"]
    assert {"plan", "step", "tool_call", "judge", "trace"} <= set(types)
    assert types.index("plan") < types.index("judge") < types.index("result")
    assert events[0]["data"]["request_id"] == run_id
    assert events[0]["data"]["events_url"] == f"{REQUESTS}/{run_id}/events"
    assert events[-2]["data"]["executed_plan"]
    assert all(e.get("id") for e in events)


async def test_stream_without_trace(client):
    _, events = await _stream(client, include_trace=False)
    types = {e["event"] for e in events}
    assert "trace" not in types and "tool_call" not in types and "plan" in types


async def test_stream_auth_is_checked_before_starting(harness, client):
    r = await client.post(STREAM, json={"question": "What is BFD?"})
    assert r.status_code == 401 and harness.runner.calls == []


async def test_get_request_by_id(client):
    run_id, _ = await _stream(client)
    r = await client.get(f"{REQUESTS}/{run_id}", headers=headers("bob"))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed" and body["endpoint"] == "stream"
    assert body["result"]["request_id"] == run_id
    assert body["links"]["events"] == f"{REQUESTS}/{run_id}/events"


async def test_other_users_get_404_admin_sees_all(client):
    run_id, _ = await _stream(client, user="bob")
    assert (await client.get(f"{REQUESTS}/{run_id}", headers=headers("alice"))).status_code == 404
    assert (await client.get(f"{REQUESTS}/{run_id}", headers=headers("carol"))).status_code == 200


async def test_unknown_and_malformed_ids_are_404(client):
    assert (await client.get(f"{REQUESTS}/00000000-0000-0000-0000-000000000000", headers=headers())).status_code == 404
    assert (await client.get(f"{REQUESTS}/not-a-uuid", headers=headers())).status_code == 404


async def test_list_is_scoped_and_paginated(client):
    ids = [(await _stream(client, user="bob"))[0] for _ in range(3)]
    await _stream(client, user="alice")
    page1 = (await client.get(REQUESTS, params={"limit": 2}, headers=headers("bob"))).json()
    assert [i["request_id"] for i in page1["items"]] == ids[::-1][:2]
    assert page1["next_cursor"]
    page2 = (await client.get(REQUESTS, params={"limit": 2, "cursor": page1["next_cursor"]},
                              headers=headers("bob"))).json()
    assert [i["request_id"] for i in page2["items"]] == [ids[0]] and page2["next_cursor"] is None
    admin = (await client.get(REQUESTS, params={"limit": 100}, headers=headers("carol"))).json()
    assert len(admin["items"]) == 4
    filtered = (await client.get(REQUESTS, params={"status": "timeout"}, headers=headers("bob"))).json()
    assert filtered["items"] == []


async def test_invalid_cursor_is_422(client):
    r = await client.get(REQUESTS, params={"cursor": "garbage"}, headers=headers())
    assert r.status_code == 422


async def test_resume_replays_only_missed_events(client):
    run_id, events = await _stream(client)
    after = events[2]["id"]
    r = await client.get(f"{REQUESTS}/{run_id}/events", headers={**headers(), "Last-Event-ID": after})
    replay = parse_sse(r.text)
    assert [e["id"] for e in replay] == [e["id"] for e in events[3:]]
    assert replay[-1]["event"] == "done"


async def test_resume_without_last_event_id_replays_everything(client):
    run_id, events = await _stream(client)
    r = await client.get(f"{REQUESTS}/{run_id}/events", headers=headers())
    assert [e["event"] for e in parse_sse(r.text)] == [e["event"] for e in events]


async def test_resume_after_buffer_expired_uses_stored_result(harness, client):
    run_id, _ = await _stream(client)
    await harness.redis.delete(f"agent:events:{run_id}")
    r = await client.get(f"{REQUESTS}/{run_id}/events", headers=headers())
    replay = parse_sse(r.text)
    assert [e["event"] for e in replay] == ["result", "done"]
    assert replay[0]["data"]["request_id"] == run_id


async def test_resume_rejects_bad_last_event_id(client):
    run_id, _ = await _stream(client)
    r = await client.get(f"{REQUESTS}/{run_id}/events", headers={**headers(), "Last-Event-ID": "abc"})
    assert r.status_code == 422


async def test_resume_of_someone_elses_run_is_404(client):
    run_id, _ = await _stream(client, user="bob")
    r = await client.get(f"{REQUESTS}/{run_id}/events", headers=headers("alice"))
    assert r.status_code == 404
