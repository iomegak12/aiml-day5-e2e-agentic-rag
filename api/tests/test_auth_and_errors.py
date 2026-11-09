from tests.conftest import headers

ASK = "/api/v1/agent/ask"


async def test_missing_api_key_is_401_problem(client):
    r = await client.post(ASK, json={"question": "What is BFD?"})
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/problem+json")
    assert "WWW-Authenticate" in r.headers
    body = r.json()
    assert body["type"].endswith("/unauthorized") and body["status"] == 401
    assert body["instance"] == ASK
    assert body["request_id"] == r.headers["x-request-id"]


async def test_invalid_api_key_is_401(client):
    r = await client.post(ASK, json={"question": "What is BFD?"}, headers={"X-API-Key": "nope"})
    assert r.status_code == 401


async def test_validation_error_lists_pointers(client):
    r = await client.post(ASK, json={"question": "", "unknown": 1}, headers=headers())
    assert r.status_code == 422
    body = r.json()
    assert body["type"].endswith("/validation-error")
    pointers = {e["pointer"] for e in body["errors"]}
    assert "/question" in pointers and "/unknown" in pointers


async def test_invalid_mode_is_422(client):
    r = await client.post(ASK, json={"question": "What is BFD?", "mode": "magic"}, headers=headers())
    assert r.status_code == 422


async def test_timeout_out_of_bounds_is_422(client):
    r = await client.post(ASK, json={"question": "What is BFD?", "timeout_seconds": 9999}, headers=headers())
    assert r.status_code == 422
    assert r.json()["errors"][0]["pointer"] == "/timeout_seconds"


async def test_unknown_route_is_404_problem(client):
    r = await client.get("/nope", headers=headers())
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["status"] == 404


async def test_method_not_allowed_is_problem(client):
    r = await client.get(ASK, headers=headers())
    assert r.status_code == 405
    assert r.json()["type"] == "about:blank"
