# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.10.x | Yes |
| < 0.10 | No |

## Reporting a Vulnerability

Please **do not** open a public issue. Email **jd.ramkumar@gmail.com** with:

- a description of the issue and its impact
- steps to reproduce it
- any suggested fix

You will receive an acknowledgement within 5 business days.

## Handling Secrets

- Keep API keys only in `.env`. It is git-ignored, and `.env.example` holds placeholders only.
- The same applies to `ATLASSIAN_API_TOKEN`: it acts with the full rights of the Atlassian account that owns it. Revoke it at id.atlassian.com (Security > API tokens) if it leaks.
- If you commit a key by accident, **rotate it immediately** in the OpenAI dashboard. Removing it from git history is not enough.
- The generated KB content is synthetic and fictional, so it contains no real customer or product data.

## REST API

- **Authentication:** every agent endpoint needs `X-API-Key`.
  - Keys map to demo users in `API_KEYS` (`.env`) and are compared in constant time.
  - Rotate them by editing `.env` and restarting.
  - These are demo credentials: put a real identity provider (OIDC/JWT) or an API gateway in front of the API in production.
- **Authorisation:** RBAC comes from the user's role.
  - Users can only read their own requests; the admin can read all.
  - Anyone else gets `404`, so request ids don't leak.
- **Rate limiting:** per client IP (Redis); the request that exceeds the limit blocks the IP for 30 s.
  - The limiter fails open if Redis is down, so availability wins over strictness.
  - Only set `TRUST_PROXY_HEADERS=true` behind a reverse proxy you control; otherwise `X-Forwarded-For` can be spoofed.
  - `compose.yaml` sets it to `true` for the `api` container, because the web gateway (Nginx) overwrites `X-Forwarded-For` with the real client address. **Trade-off:** port 8080 is still published to the host for scripts and `/docs`, so a caller that hits it directly could spoof the header. In production, do not publish the API port (only the gateway is reachable), or use a gateway that strips the header.
- **CORS:** not enabled. Browsers on other origins can't call the API; the web UI is served from the same origin as the API (Nginx gateway).
- **Audit and PII:**
  - Every request (except probes) is stored in Postgres.
  - E-mail addresses and card numbers in bodies are redacted before storage, and `X-API-Key` / `Authorization` / `Cookie` headers are masked.
  - The live SSE buffer in Redis holds what the client received, for `EVENT_BUFFER_TTL_SECONDS` (1 h).
- **Errors:** RFC 9457 problem details. Stack traces are never returned; quote the `request_id` instead.
- **Container:** non-root user (uid 10001), slim base, no build tools, and no `.env` in the image (configuration comes from the environment at run time).

## Web UI

- **Same origin:** the browser talks only to the Nginx gateway; `/api/*`, `/health` and `/ready` are proxied to the API. `/metrics` (unauthenticated) and `/docs` are **not** exposed through the gateway.
- **API key storage:** the key is kept in `sessionStorage` (per tab, cleared when the tab closes) and sent as `X-API-Key`. Any `401` clears it and returns to sign-in. No key or secret is ever built into the JavaScript bundle (`VITE_*` variables are public by design, so none are used).
  - `sessionStorage` is readable by script on the page, so XSS is the main risk. It is reduced by a strict CSP and by rendering model output with react-markdown with raw HTML disabled. A production deployment should prefer a backend-for-frontend with an `HttpOnly` session cookie and a real identity provider (OIDC).
- **Headers** (`web/nginx/security-headers.conf`):
  - `Content-Security-Policy: default-src 'self'`: scripts, styles, fonts and API calls only from the same origin, with `frame-ancestors 'none'` and `object-src 'none'`.
  - `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, `Permissions-Policy`, `Cross-Origin-Opener-Policy: same-origin`.
  - Fonts are self-hosted, and the build never inlines assets as `data:` URIs.
- **Gateway:** `nginxinc/nginx-unprivileged` (non-root, port 8080 in the container), `server_tokens off`, request bodies capped at 64 KB, and `X-Forwarded-For` overwritten (not appended).
- **TLS:** the demo serves plain HTTP on localhost. Terminate TLS (and add `Strict-Transport-Security`) in front of the gateway for any shared deployment.

## MCP Server (IT tickets)

- **No authentication (demo scope):** the server trusts the `X-User-Id` header, so anyone who can reach port 9090 can act as any demo user, including the admin. Keep it on localhost or a private network: in compose only the agent (`api` container) needs it. Before any shared deployment, add authentication (for example OAuth 2.1 / bearer tokens, which FastMCP supports) and derive the user from the token, not from a header.
- **RBAC is enforced on the server**, not only in the agent: search, resolve and sync are admin-only, and another user's ticket reads as "not found". The agent adds its own guards (writes only on explicit request, never from a re-plan, never twice per request).
- **Jira:** the token is read from `.env` and never logged; stored Jira errors contain no credentials. Issues are created by the token owner, and the requester is recorded in the description header and a `user-<id>` label. The mirror is one-way: changes made in Jira do not flow back to Postgres.
- **Data:** ticket text is user-supplied and shown to the LLM as context, so treat it as untrusted input (it is quoted as data in the CONTEXT, and the output guardrails still apply).

## Publishing and AWS deployment

- **Docker Hub:** `DOCKERHUB_TOKEN` must be a personal access token (scope: read & write), never your password. It is passed to `docker login` on stdin and never printed. The pushed repositories are **public**: images contain code but no secrets (`.env` is excluded by `.dockerignore`).
- **AWS keys** (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) are only read by Terraform on your machine. `iac/prepare.py` removes every `AWS_*` and `DOCKERHUB_*` line from the `.env` it uploads, so neither reaches the instance. Prefer an IAM user limited to EC2 in one region, and rotate the keys if they leak.
- **The server's `.env`** (`/opt/netcore/.env`, mode 0600) holds the OpenAI key, `API_KEYS` and the Jira token. It is copied over SSH; only its hash goes into the Terraform state.
- **SSH:** a new ED25519 key pair is generated per deployment. The private key is in `iac/.keys/` and in the local Terraform state; both are git-ignored, so keep them private. Port 22 is open only to the public IP detected at plan time (set `ssh_cidr` to change it). Password login is disabled by the Ubuntu AMI.
- **Exposure:** only port 80 (Nginx gateway, strict CSP) is public. The API (8080) and the **unauthenticated MCP server** (9090) are bound to 127.0.0.1 and reached through an SSH tunnel; Chroma, Redis and Postgres have no host ports. IMDSv2 is required and the root volume is encrypted.
- **TLS:** the demo serves plain HTTP. Put a TLS-terminating load balancer or a reverse proxy with a certificate in front before using it with real users.

