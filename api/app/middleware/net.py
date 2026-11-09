"""Client IP of an ASGI request."""

from __future__ import annotations


def client_ip(scope: dict, trust_proxy: bool = False) -> str:
    if trust_proxy:  # only behind a reverse proxy you control; otherwise the header is spoofable
        for name, value in scope.get("headers", []):
            if name == b"x-forwarded-for":
                return value.decode("latin-1").split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "unknown"
