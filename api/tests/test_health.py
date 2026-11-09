async def test_health_is_public_and_versioned(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.headers["x-request-id"]


async def test_ready_when_all_dependencies_up(client):
    r = await client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert set(body["checks"]) == {"chroma", "redis", "postgres"}


async def test_ready_returns_problem_when_a_dependency_is_down(harness, client):
    harness.checks["postgres"] = False
    r = await client.get("/ready")
    assert r.status_code == 503
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["type"].endswith("/not-ready")
    assert body["checks"]["postgres"]["status"] == "down"
    assert "postgres" in body["detail"]


async def test_metrics_exposes_prometheus_text(client):
    await client.get("/health")
    r = await client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in r.text
    assert "agent_runs_total" in r.text


async def test_openapi_and_swagger_available(client):
    spec = (await client.get("/openapi.json")).json()
    assert "/api/v1/agent/ask" in spec["paths"]
    assert "/api/v1/agent/requests/{request_id}/events" in spec["paths"]
    assert "X-API-Key" in str(spec["components"]["securitySchemes"])
    assert (await client.get("/docs")).status_code == 200


async def test_no_cors_headers(client):
    r = await client.options("/api/v1/agent/ask", headers={"Origin": "https://evil.example",
                                                           "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers
