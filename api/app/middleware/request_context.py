"""Outermost middleware (pure ASGI, stream-safe):

- assigns X-Request-ID (server-generated UUID; a client-sent X-Request-ID is kept as correlation_id)
- binds request context to structlog (request_id, method, path, client_ip, user_id)
- JSON access log + Prometheus HTTP metrics
- captures request/response bodies (capped; SSE bodies are not buffered) and writes the audit row to Postgres
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import structlog

from app.core import metrics
from app.core.logging import get_logger
from app.middleware.net import client_ip

log = get_logger("api.access")


def _decode_body(raw: bytes, content_type: str) -> Any:
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    if "json" in content_type:
        try:
            return json.loads(text)
        except ValueError:
            return text
    return text


class RequestContextMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        app = scope["app"]
        settings, audit = app.state.settings, app.state.container.audit
        request_id = str(uuid.uuid4())
        headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope.get("headers", [])}
        ip = client_ip(scope, settings.trust_proxy_headers)
        path, method = scope["path"], scope["method"]
        scope.setdefault("state", {})["request_id"] = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, method=method, path=path, client_ip=ip)

        cap = settings.audit_max_body_bytes
        audited = not path.startswith(settings.audit_exclude)
        req_chunks: list[bytes] = []
        res_chunks: list[bytes] = []
        state: dict[str, Any] = {"status": 500, "headers": {}, "truncated": False, "req_size": 0, "res_size": 0}

        async def receive_wrapper():
            message = await receive()
            if audited and message["type"] == "http.request":
                body = message.get("body", b"")
                if state["req_size"] < cap:
                    req_chunks.append(body[: cap - state["req_size"]])
                state["req_size"] += len(body)
            return message

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                state["status"] = message["status"]
                message.setdefault("headers", [])
                message["headers"].append((b"x-request-id", request_id.encode()))
                state["headers"] = {k.decode("latin-1"): v.decode("latin-1") for k, v in message["headers"]}
            elif message["type"] == "http.response.body" and audited:
                if "text/event-stream" not in state["headers"].get("content-type", ""):
                    body = message.get("body", b"")
                    if state["res_size"] < cap:
                        res_chunks.append(body[: cap - state["res_size"]])
                    state["res_size"] += len(body)
            await send(message)

        started = time.perf_counter()
        metrics.HTTP_IN_PROGRESS.inc()
        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        finally:
            metrics.HTTP_IN_PROGRESS.dec()
            latency = time.perf_counter() - started
            route_obj = scope.get("route")
            route = getattr(route_obj, "path", None) or ("unmatched" if state["status"] == 404 else path)
            metrics.HTTP_REQUESTS.labels(method, route, str(state["status"])).inc()
            metrics.HTTP_LATENCY.labels(method, route).observe(latency)
            user_id = scope.get("state", {}).get("user_id")
            log.info("http_request", status=state["status"], latency_ms=round(latency * 1000, 1), route=route,
                     user_id=user_id, user_agent=headers.get("user-agent"))
            if audited:
                content_type = state["headers"].get("content-type", "")
                if "text/event-stream" in content_type:
                    response_body: Any = {"stream": "text/event-stream",
                                          "note": "events: Redis Stream agent:events:<run_id>; result: agent_runs"}
                else:
                    response_body = _decode_body(b"".join(res_chunks), content_type)
                from app.services.redaction import sanitize_headers
                audit.spawn(audit.log_request({
                    "id": request_id, "method": method, "path": path, "route": route,
                    "query_string": scope.get("query_string", b"").decode("latin-1") or None,
                    "client_ip": ip, "user_agent": headers.get("user-agent"), "user_id": user_id,
                    "status_code": state["status"], "latency_ms": round(latency * 1000, 1),
                    "request_headers": sanitize_headers(headers),
                    "request_body": _decode_body(b"".join(req_chunks), headers.get("content-type", "")),
                    "response_headers": sanitize_headers(state["headers"]),
                    "response_body": response_body,
                    "body_truncated": state["req_size"] > cap or state["res_size"] > cap,
                    "correlation_id": headers.get("x-request-id") or headers.get("x-correlation-id"),
                }))
            structlog.contextvars.clear_contextvars()
