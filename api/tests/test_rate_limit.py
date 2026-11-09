from tests.conftest import Harness, headers

ASK = "/api/v1/agent/ask"


async def test_ip_is_blocked_after_exceeding_the_limit():
    h = Harness(rate_limit_per_minute=3, rate_limit_block_seconds=30)
    async with h.client(ip="10.1.1.1") as c:
        for n in range(3):
            r = await c.get("/api/v1/agent/requests", headers=headers())
            assert r.status_code == 200
            assert r.headers["x-ratelimit-limit"] == "3"
            assert r.headers["x-ratelimit-remaining"] == str(2 - n)
        r = await c.get("/api/v1/agent/requests", headers=headers())
        assert r.status_code == 429
        assert r.headers["retry-after"] == "30"
        body = r.json()
        assert r.headers["content-type"].startswith("application/problem+json")
        assert body["type"].endswith("/rate-limited") and body["retry_after"] == 30
        # still blocked (penalty box), even though the counter was reset
        r = await c.post(ASK, json={"question": "What is BFD?"}, headers=headers())
        assert r.status_code == 429 and 0 < int(r.headers["retry-after"]) <= 30
        # probes are exempt
        assert (await c.get("/health")).status_code == 200
    # other clients are not affected
    async with h.client(ip="10.2.2.2") as other:
        assert (await other.get("/api/v1/agent/requests", headers=headers())).status_code == 200


async def test_block_expires():
    h = Harness(rate_limit_per_minute=1, rate_limit_block_seconds=30)
    async with h.client(ip="10.3.3.3") as c:
        await c.get("/api/v1/agent/requests", headers=headers())
        assert (await c.get("/api/v1/agent/requests", headers=headers())).status_code == 429
        await h.redis.delete("ratelimit:block:10.3.3.3")  # simulate the 30 s passing
        assert (await c.get("/api/v1/agent/requests", headers=headers())).status_code == 200


async def test_rate_limited_requests_are_audited():
    h = Harness(rate_limit_per_minute=1)
    async with h.client(ip="10.4.4.4") as c:
        await c.get("/api/v1/agent/requests", headers=headers())
        r = await c.get("/api/v1/agent/requests", headers=headers())
    await h.container.audit.drain()
    assert any(e["status_code"] == 429 and e["id"] == r.headers["x-request-id"] for e in h.request_logs.entries)


async def test_fail_open_when_redis_is_down():
    h = Harness(rate_limit_per_minute=1)

    async def broken(*_a, **_k):
        raise ConnectionError("redis down")

    h.redis.ttl = broken
    async with h.client() as c:
        for _ in range(3):
            assert (await c.get("/health")).status_code == 200
            assert (await c.get("/api/v1/agent/requests", headers=headers())).status_code == 200
