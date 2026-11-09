# Plan: NetCore Assist Web UI (`web/`), v0.8.0

## Context
The approved prototype (`docs/ui-mockups/prototype/`, 8 screens) now becomes a working web app on top of the existing FastAPI backend (`api/`, v0.7.0).
- Stack: React 18, Vite and pure JavaScript.
- Code: modular, in `web/`.
- Routing: the browser reaches the API only through Nginx, on the same origin.
- Packaging: container files and a compose service.
- Docs: README and the other root docs are updated.

## Decisions (MCQ rounds)
| Topic | Decision |
|---|---|
| Screens | All 8. Screen 07 ("error states") becomes reusable components, not a page. |
| Styling | Tailwind CSS v4 (`@tailwindcss/vite`), with the prototype tokens in `@theme` |
| Libraries | React Router 7, TanStack Query v5 and `@microsoft/fetch-event-source` |
| Nginx | One web container that serves the build and proxies to `api:8080` |
| Key storage | `sessionStorage`, protected by a strict CSP |
| Quality | Vitest, React Testing Library and jsdom, plus ESLint 9 (flat config) and Prettier |
| Toolchain | npm with Node 22 LTS (`node:22-alpine` build stage) |
| API port | 8080 stays published to the host |
| Sign-in | API key field only, no demo cards and no secrets in the bundle |
| `/metrics` | Not proxied. System status uses `/health` and `/ready` only. |
| Web port | Host **80** (overridable with `WEB_PORT`), mapped to 8080 inside the container |
| Version | **0.8.0**: project, `web/package.json`, `localhost/netcore-rag-web:0.8.0` |
| Nginx image | `nginxinc/nginx-unprivileged:alpine` (non-root) |
| Structure | Feature-based folders |
| Dev | The Vite dev server proxies `/api`, `/health` and `/ready` to `localhost:8080` |
| Extras | ⌘K new chat, dark mode toggle, copy answer and citation jump. **Export JSON is not included.** |
| Proxy trust | `TRUST_PROXY_HEADERS=true` on api. Spoofing via direct 8080 is a documented trade-off. |
| Fonts | Self-hosted with `@fontsource` (Inter, JetBrains Mono, Material Symbols) |
| Make/compose | `web-*` targets, and the web service is part of `stack-up` |
| Headers | Strict CSP plus the standard security headers, gzip and cache rules |
| Identity | New **`GET /api/v1/me`** endpoint in the API |

> ⚠ Port 80 with rootless Podman: unprivileged processes cannot bind ports below 1024 by default. Fix with `sysctl net.ipv4.ip_unprivileged_port_start=80` in the Podman machine, or set `WEB_PORT=3000`. This goes in TROUBLESHOOTING.

## 1. Backend addition (small)
- `api/app/controllers/me.py`: `GET /api/v1/me`, which depends on `get_current_user` (`api/app/core/security.py:29`).
  - Returns `{id, name, role, allowed_levels}`, built from `agentic_rag.config.User`.
  - Rate-limited like the other routes.
- `api/app/schemas/`: add a `MeResponse` model.
- `api/app/main.py:61`: add `include_router(me.router)`.
- `api/tests/test_me.py`: covers 200 for each role and 401 for a missing or bad key.

## 2. `web/` layout
```
web/
  package.json  vite.config.js  vitest.setup.js  eslint.config.js  .prettierrc
  index.html  Containerfile  .dockerignore  nginx/default.conf  nginx/security-headers.conf
  src/
    main.jsx  App.jsx  router.jsx            # routes, lazy-loaded features
    styles/index.css                         # @import tailwindcss; @theme tokens; dark variant
    api/      client.js  sse.js  endpoints.js  queryClient.js  ApiError.js
    features/
      auth/      SignInPage  AuthProvider  useAuth  RequireAuth  RequireAdmin
      chat/      NewChatPage  Composer  ModePill  OptionsPopover
      run/       LiveRunPage  useAskStream (reducer)  PlanSteps  EventLog
                 AnswerPage  insights/{Plan,Sources,Judge,ToolCalls,Trace,Timing}Tab  CitationChip
      requests/  HistoryPage  HistoryFilters  RequestDetailPage  useRequests  useRunEvents
      status/    SystemStatusPage
    components/  AppShell  Sidebar  TopBar  UserCard  StatusBadge  Tabs  Popover  Toast
                 ThemeToggle  errors/{ProblemPanel,RateLimitBanner,TimeoutCard,UnavailableCard}
    hooks/       useHotkey  useTheme  useCountdown
    lib/         storage.js  format.js  problem.js
```

**`api/client.js`**
- `fetch` wrapper that adds `X-API-Key` from `sessionStorage`.
- Parses `application/problem+json` into an `ApiError`, which keeps `status`, `type` slug, `retryAfter` and `request_id`.
- On a 401 it clears the key and redirects to `/sign-in`.

**`api/sse.js`** wraps `fetchEventSource` for `POST /ask/stream` and `GET /requests/{id}/events`.
- Sends `Last-Event-ID` (tracks the last `id`) on resume.
- Uses `openWhenHidden: true` and supports abort.

**`useAskStream`** is a reducer over the SSE events:
- `accepted` → `plan` → `step` → `tool_call`/`trace` → `judge` → `result`/`error` → `done`
- It is reused by the live run and request detail screens; replay drives it from the `/events` stream.

**Routes**

| Path | Screen |
|---|---|
| `/sign-in` | 01 |
| `/` | 02 New chat |
| `/runs/:id/live` | 03 |
| `/runs/:id` | 04 Answer and insights |
| `/requests` | 05 |
| `/requests/:id` | 06 |
| `/status` | 08, admin only |

- Sidebar history links follow the same status rules as the prototype.
- "Stop watching" aborts the stream; the server keeps running the job, and the user is sent to the detail screen.

**Errors (from screen 07)**
- 429: banner with a `Retry-After` countdown, and the composer is disabled meanwhile.
- 504 and 503: cards.
- Every error: a collapsible `ProblemPanel`.
- 422: field errors mapped onto the composer.

**Styling**
- Tokens are taken from the prototype's `tailwind.config` and from `DESIGN.md`: colours, spacing, radii, type scale, status palette and the ambient gradient.
- Dark mode: `@custom-variant dark` uses the class strategy and sets dark values for the same tokens.
  - First load follows `prefers-color-scheme`; the user's choice is saved in `localStorage`.
- Prototype markup is reused where possible; `docs/ui-mockups/prototype/*.html` is the visual reference.

## 3. Nginx and containers
**`nginx/default.conf`** listens on 8080.
- Static files from `/usr/share/nginx/html`, with an SPA fallback (`try_files $uri /index.html`).
- `location /api/`, `= /health` and `= /ready` go to `proxy_pass http://api:8080`. All three use `proxy_http_version 1.1` and set:
  - `X-Forwarded-For $remote_addr`, `X-Real-IP` and `X-Forwarded-Proto`
  - `proxy_buffering off` (needed for SSE)
  - `proxy_read_timeout 330s` (300 s max agent timeout plus grace)
- Not proxied: `/metrics`, `/docs`.

**Caching and compression**
- `index.html`: `no-cache`.
- `/assets/*`: 1 year, `immutable`.
- gzip on.

**`security-headers.conf`**
- `Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy` with camera, microphone and geolocation disabled

**`web/Containerfile`**, multi-stage:
- Stage `build`: `node:22-alpine`, then `npm ci`, `npm run build`.
- Stage `runtime`: `nginxinc/nginx-unprivileged:1.29-alpine` (exact tag pinned at implementation time).
  - Copies `dist/` and the conf files.
  - `EXPOSE 8080`.
  - `HEALTHCHECK` calls `wget -qO- localhost:8080/healthz`, a static 200 location in Nginx.

**`compose.yaml`**
- New service `web`:
  - container `netcore-web`, image `localhost/netcore-rag-web:0.8.0`
  - `build: {context: ./web, dockerfile: Containerfile}`
  - ports `${WEB_PORT:-80}:8080`
  - `depends_on: api: condition: service_healthy`
  - healthcheck, `restart: unless-stopped`
- api service: add `TRUST_PROXY_HEADERS=true`.

**Other files**
- `.dockerignore` (root): add `web/` so it stays out of the API build context.
- `.env.example`: add `WEB_PORT=80`.
- Version bump to 0.8.0: the API image tag (`localhost/netcore-rag-api:0.8.0`) and the API version string.

**Makefile**
- `WEB_IMAGE` variable.
- New targets: `web-install`, `web-dev`, `web-lint`, `web-test`, `web-build` (npm), `web-image`, `web-up`, `web-down`, `web-logs`.
- `stack-up` and `stack-down` now include web.
- Follows the existing ENGINE docker/podman detection (`Makefile:18-31`).

## 4. Docs
| File | Change |
|---|---|
| README | New "Web UI" section: architecture (browser → Nginx → API), run steps, screen list, make targets. Also add the layout entry, `/me` in the route table and the compose port table. |
| CHANGELOG | 0.8.0 entry: Added (web UI, `/me`, web image), Changed (TRUST_PROXY_HEADERS, version), Security (CSP, non-root nginx). |
| CONTRIBUTING | Front-end setup (Node 22, `make web-*`), lint, test, folder conventions. |
| TROUBLESHOOTING | New rows: port 80 on rootless Podman, SSE buffering through a proxy, blank page from a CSP violation, 401 loop after a key change, Vite proxy connection refused. |
| CODE_OF_CONDUCT | Scope line now covers the web UI. Otherwise unchanged. |
| SECURITY | Key held in sessionStorage plus the CSP rationale, `TRUST_PROXY_HEADERS` spoofing trade-off, `/metrics` not exposed, non-root Nginx. |

## 5. Verification
1. `make api-test`: existing tests plus `test_me.py` pass.
2. `make web-lint web-test`: Vitest covers the client (problem parsing, 401 redirect), the `useAskStream` reducer (event fixtures), the sign-in flow, the 429 countdown and the admin route guard.
3. `make web-build` produces `dist/`. Then `make stack-up` should leave web healthy, and `http://localhost/` should load.
4. Manual run through Nginx:
   - Sign in as bob: the user card shows employee, and there is no Status link.
   - Ask in plan mode: the live run streams step by step, which proves Nginx is not buffering. The answer, all six insights tabs and the citation jump work.
   - History filters and the detail replay work, including resume with `Last-Event-ID`.
   - Sign in as carol: the Status page shows `/ready` checks.
   - Dark mode toggle and ⌘K both work.
5. Rate limit and headers:
   - Burst 101 requests: the 429 banner counts down, and the API log shows the real client IP rather than the Nginx IP.
   - `curl -I http://localhost/` shows the CSP and security headers.
   - `curl http://localhost/metrics` serves the SPA instead of metrics, so they are not exposed.
6. No commit unless asked.
