"""IP rate limiting with a penalty box (Redis, shared by all workers/containers).

- Each client IP may send RATE_LIMIT_PER_MINUTE requests per 60 s window (window starts at its first request).
- The request that exceeds the limit puts the IP in a penalty box for RATE_LIMIT_BLOCK_SECONDS: every request
  gets 429 + Retry-After until the block expires; then the counter starts fresh.
- Exempt: health/readiness/metrics/docs. Fail-open if Redis is unreachable (logged), so a cache outage does
  not take the API down.
"""

from __future__ import annotations

from app.core import metrics
from app.core.logging import get_logger
from app.core.problems import PROBLEM_TYPES, problem_body, problem_response
from app.middleware.net import client_ip

log = get_logger("api.ratelimit")
WINDOW_SECONDS = 60


class RateLimitMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        app = scope["app"]
        s = app.state.settings
        if scope["path"].startswith(s.rate_limit_exempt):
            await self.app(scope, receive, send)
            return

        ip = client_ip(scope, s.trust_proxy_headers)
        redis = app.state.container.redis
        block_key, count_key = f"ratelimit:block:{ip}", f"ratelimit:count:{ip}"
        try:
            blocked_for = await redis.ttl(block_key)
            if blocked_for and blocked_for > 0:
                metrics.RATE_LIMIT_BLOCKS.labels("blocked").inc()
                await self._reject(scope, receive, send, blocked_for, s, "blocked")
                return
            async with redis.pipeline(transaction=True) as pipe:
                pipe.incr(count_key)
                pipe.expire(count_key, WINDOW_SECONDS, nx=True)
                pipe.ttl(count_key)
                count, _, window_left = await pipe.execute()
            if count > s.rate_limit_per_minute:
                async with redis.pipeline(transaction=True) as pipe:
                    pipe.set(block_key, 1, ex=s.rate_limit_block_seconds)
                    pipe.delete(count_key)
                    await pipe.execute()
                metrics.RATE_LIMIT_BLOCKS.labels("limit_exceeded").inc()
                log.warning("rate_limit_exceeded", client_ip=ip, limit=s.rate_limit_per_minute,
                            block_seconds=s.rate_limit_block_seconds)
                await self._reject(scope, receive, send, s.rate_limit_block_seconds, s, "exceeded")
                return
        except Exception as exc:  # noqa: BLE001 - fail open
            log.error("rate_limit_unavailable", error=f"{type(exc).__name__}: {exc}"[:200])
            await self.app(scope, receive, send)
            return

        remaining = max(s.rate_limit_per_minute - count, 0)
        reset = window_left if window_left and window_left > 0 else WINDOW_SECONDS
        extra = [(b"x-ratelimit-limit", str(s.rate_limit_per_minute).encode()),
                 (b"x-ratelimit-remaining", str(remaining).encode()),
                 (b"x-ratelimit-reset", str(reset).encode())]

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend(extra)
            await send(message)

        await self.app(scope, receive, send_with_headers)

    @staticmethod
    async def _reject(scope, receive, send, retry_after: int, s, reason: str) -> None:
        title, status = PROBLEM_TYPES["rate-limited"]
        detail = (f"Rate limit of {s.rate_limit_per_minute} requests/minute exceeded; this IP is blocked for "
                  f"{s.rate_limit_block_seconds} s." if reason == "exceeded" else
                  f"This IP is temporarily blocked for exceeding {s.rate_limit_per_minute} requests/minute. "
                  f"Retry after {retry_after} s.")
        body = problem_body(slug="rate-limited", title=title, status=status, detail=detail, instance=scope["path"],
                            request_id=scope.get("state", {}).get("request_id"), base_uri=s.problem_base_uri,
                            retry_after=retry_after)
        response = problem_response(body, headers={"Retry-After": str(retry_after),
                                                   "X-RateLimit-Limit": str(s.rate_limit_per_minute),
                                                   "X-RateLimit-Remaining": "0"})
        await response(scope, receive, send)
