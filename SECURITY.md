# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.7.x | Yes |
| < 0.7 | No |

## Reporting a Vulnerability

Please **do not** open a public issue. Email **jd.ramkumar@gmail.com** with:

- a description of the issue and its impact
- steps to reproduce it
- any suggested fix

You will receive an acknowledgement within 5 business days.

## Handling Secrets

- Keep API keys only in `.env`. It is git-ignored, and `.env.example` holds placeholders only.
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
- **CORS:** not enabled. Browsers on other origins can't call the API.
- **Audit and PII:**
  - Every request (except probes) is stored in Postgres.
  - E-mail addresses and card numbers in bodies are redacted before storage, and `X-API-Key` / `Authorization` / `Cookie` headers are masked.
  - The live SSE buffer in Redis holds what the client received, for `EVENT_BUFFER_TTL_SECONDS` (1 h).
- **Errors:** RFC 9457 problem details. Stack traces are never returned; quote the `request_id` instead.
- **Container:** non-root user (uid 10001), slim base, no build tools, and no `.env` in the image (configuration comes from the environment at run time).
