# Phase 7 – Web UI (React + Vite + Nginx) and the all-in-one make target

Your prompts (lightly cleaned), the MCQ clarifications with every option ([x] = your choice), and a one-line outcome.

## Prompt 1

> We now have a requirement to build the web UI for the scenario above.
>
> We have already prepared a prototype from the UI mockups we designed with Google Stitch. As per the business requirement, we now need to build the working web application with the following specifications:
>
> - React 18
> - Vite
> - Pure JavaScript, no TypeScript
> - Nginx-based API access, instead of the web UI calling the services directly
> - Modularise the code
> - Keep the implementation in a `web\` folder at the workspace root
> - Update README, CHANGELOG, CONTRIBUTING, TROUBLESHOOTING, CODE_OF_CONDUCT and SECURITY
> - Update compose and prepare container files for building images for this web UI
>
> Do you understand my web application requirements? Let's have a debate of MCQ-based Q&As so we are both aligned. I prefer the Q&A so that none of the important features are missed.
>
> NOTES:
> - Do NOT assume anything on your own; clarify with me.
> - Do NOT generate any code until the plan is reviewed and approved.
> - Do NOT give long, detailed responses unless I ask; brief is fine.
>
> Let's go.

### Clarifications

#### Round 1

**Which prototype screens should the web app implement? (The prototype has 8: sign-in, new chat, live run, answer and insights, request history, request detail and replay, error states, and system status, which is admin only.)** _(Screens)_

- [x] **All 8 (Recommended)** – Matches the approved prototype exactly. System status is admin-only and calls /health and /ready.
- [ ] All except System status – Skips the admin ops screen, so /health and /ready don't need to be exposed to the UI.
- [ ] Core flow only – Sign-in, chat, live run, answer and history. Replay and status come later.

**How should the app be styled?** _(Styling)_

- [x] **Tailwind CSS v4 (Recommended)** – Build-time Tailwind with the prototype's tokens moved into @theme. Closest to the Stitch/prototype markup, so screens port 1:1.
- [ ] CSS Modules + CSS variables – No framework. Tokens are :root variables and each component has its own .module.css. More hand-written CSS.
- [ ] Component library (MUI/Mantine) – Ready-made widgets, but matching the prototype's look takes heavy theming.

**Which client libraries should handle routing, server data and SSE?** _(Libraries)_

- [x] **Router + Query + fetch-SSE (Recommended)** – React Router 7 for routes, TanStack Query for history/detail caching, and @microsoft/fetch-event-source for the POST stream with the X-API-Key header.
- [ ] Router + plain fetch hooks – Fewer dependencies: custom useFetch hooks plus a hand-written SSE parser. More code to maintain.
- [ ] Router + Query + hand-written SSE – Same as the first option, but the SSE reader is our own ~60-line fetch stream parser instead of a library.

**How should Nginx be set up in front of the API?** _(Nginx)_

- [x] **Single web container (Recommended)** – One Nginx image serves the Vite build and proxies /api, /health and /ready to api:8080 on the same origin. No CORS needed.
- [ ] Separate gateway + static web – A dedicated Nginx gateway container routes to both a static web container and the API. More moving parts, closer to a production edge setup.
- [ ] Nginx + Vite dev proxy – Nginx proxies in containers, and the Vite dev server proxies /api for local npm run dev (this can be combined with either option).

#### Round 2

**Where should the browser keep the user's X-API-Key after sign-in?** _(Key storage)_

- [x] **sessionStorage (Recommended)** – Survives a page refresh and is cleared when the tab closes. Good balance for a demo app; still readable by any XSS, so a strict CSP goes with it.
- [ ] localStorage – Persists across browser restarts, so it is the most convenient. It also has the largest exposure window.
- [ ] Memory only – Safest, but every refresh forces a new sign-in.
- [ ] Nginx session cookie (BFF) – Nginx/auth layer holds the key and the browser only gets an HttpOnly cookie. This is industry best practice but needs an extra auth service, which is overkill here.

**What testing and code-quality tooling should web/ have?** _(Testing)_

- [x] **Vitest + RTL + ESLint/Prettier (Recommended)** – Unit and component tests with mocked fetch/SSE, plus lint and format. A standard Vite setup.
- [ ] Above + Playwright E2E – Adds browser end-to-end tests against the running stack. Strongest coverage, heavier to set up.
- [ ] ESLint/Prettier only – No automated tests; verify manually.

**Which package manager and Node version should web/ use?** _(Node/PM)_

- [x] **npm + Node 22 LTS (Recommended)** – Zero extra install, with package-lock.json. The build stage uses node:22-alpine.
- [ ] pnpm + Node 22 LTS – Faster, with a strict dependency tree. Needs corepack/pnpm installed.
- [ ] npm + Node 24 – Newer runtime. Fine for build-only use.

**Once Nginx fronts the API in compose, should api:8080 still be published to the host?** _(API port)_

- [x] **Keep published (Recommended)** – make agent-api-test, scripts and /docs keep working directly. The web UI still goes only through Nginx.
- [ ] Internal only – Only Nginx is exposed, which matches a production gateway. Test scripts would need to point at the Nginx port instead.

#### Round 3

**The prototype's sign-in screen has Alice, Bob and Carol cards. How should they work in the real app?** _(Demo users)_

- [x] **Key field only (Recommended)** – Remove the cards; users paste their key. No secrets in the bundle, which is industry practice.
- [ ] Cards prefill from build env – Demo keys are baked in via VITE_DEMO_KEYS for a one-click classroom demo. Anyone can read them in the JS bundle.
- [ ] Cards as hints only – Cards show the name, role and access levels for teaching purposes, but the key must still be typed.

**The System status screen shows Prometheus /metrics. How should Nginx handle /metrics?** _(Metrics)_

- [x] **Don't proxy /metrics (Recommended)** – The status screen uses only /health and /ready. /metrics is unauthenticated, so it stays off the public origin.
- [ ] Proxy, private-network IPs only – Nginx allows RFC1918/localhost only. The status screen parses a few counters.
- [ ] Proxy openly – Simplest, but exposes internal metrics to anyone who can reach the UI.

**Which host port should the web (Nginx) container publish?** _(Web port)_

- [ ] 3000 (Recommended) – WEB_PORT=3000 in .env. A common front-end port with no clash with 8000, 8080, 6379 or 5432.
- [ ] 8088 – Sits next to the API's 8080.
- [x] **80** – Plain http://localhost. It may need admin rights or clash on some machines.

**What version number should this release use?** _(Version)_

- [x] **0.8.0 for both (Recommended)** – Bump the project to 0.8.0, and use 0.8.0 for web/package.json and the image tag localhost/netcore-rag-web:0.8.0. Keeps the CHANGELOG consistent.
- [ ] Web 0.1.0, API stays 0.7.0 – The web app is versioned on its own and the API is untouched.

#### Round 4

**Which Nginx base image should the web container use?** _(Nginx image)_

- [x] **nginx-unprivileged:alpine (Recommended)** – Runs as non-root and listens on 8080 inside the container, mapped to host 80. Matches the API's non-root practice and is safer.
- [ ] nginx:alpine – The official image. The master process runs as root and listens on 80 directly. Simpler, weaker hardening.

**How should the web/ code be organised into modules?** _(Structure)_

- [x] **Feature-based (Recommended)** – src/features/{auth,chat,run,requests,status}, plus shared src/api, src/components, src/hooks and src/lib. Scales well and is the current React practice.
- [ ] Type-based – src/pages, src/components, src/hooks and src/services. Familiar, but files for one feature get scattered.

**Should npm run dev in web/ proxy /api to the local API at localhost:8080 through Vite?** _(Dev proxy)_

- [x] **Yes, mirror the Nginx routes (Recommended)** – The same relative paths work in dev and in the container, with hot reload against a running API.
- [ ] No, containers only – Always test through the Nginx container; there is no fast hot-reload loop.

**Which prototype extras should be included?** _(Extras, multi-select)_

- [x] **⌘K new-chat shortcut** – Keyboard shortcut that focuses or opens a new chat.
- [ ] Export run JSON – Download a run's detail as a .json file from the detail screen.
- [x] **Copy answer / citations jump** – A copy button, and citation chips that scroll to their sources.
- [x] **Dark mode toggle** – The prototype is light-only, so this would mean extra design work.

#### Round 5

**Behind Nginx, every user would share the Nginx IP for rate limiting unless the API trusts X-Forwarded-For. But port 8080 also stays published, so a direct caller could spoof that header. What should we do?** _(Proxy trust)_

- [x] **TRUST_PROXY_HEADERS=true (Recommended)** – Set this on the api service in compose. Nginx overwrites X-Forwarded-For with $remote_addr. Direct-8080 spoofing is accepted as a demo trade-off and documented in SECURITY.md.
- [ ] Keep false – No spoofing risk, but all web users share one 100/min bucket.

**How should fonts and icons (Inter, JetBrains Mono, Material Symbols) be loaded?** _(Fonts)_

- [x] **Self-host via @fontsource (Recommended)** – Bundled by Vite. Works offline in class, allows a strict CSP (no third-party origins) and no Google tracking.
- [ ] Google Fonts CDN – Same as the prototype and gives a smaller bundle, but the CSP must allow fonts.googleapis.com and fonts.gstatic.com.

**How should the web app fit into the Makefile and compose?** _(Make/Compose)_

- [x] **web-\* targets + in stack-up (Recommended)** – Add web-install, dev, test, lint, build, image, up, down and logs targets. The compose web service depends on api being healthy, so make stack-up brings the full UI up.
- [ ] web-\* targets, separate profile – The web service sits under compose profile "web" and starts only on request.

**Which security headers should Nginx send?** _(Headers)_

- [x] **Strict CSP + standard set (Recommended)** – CSP default-src 'self', X-Content-Type-Options, Referrer-Policy, frame-ancestors none and Permissions-Policy. Also gzip, long caching for hashed assets, and no-cache for index.html.
- [ ] Standard set, no CSP – Easier to get working; weaker XSS defence for a key kept in sessionStorage.

#### Round 6

**The API has no /me endpoint, but the shell needs the user's name and role for the user card and the admin-only System status link. How should the UI get them?** _(Identity)_

- [x] **Add GET /api/v1/me to API (Recommended)** – A small backend addition that returns {id, name, role, allowed_levels}. Sign-in validates the key and loads the profile in one call. Includes a pytest and a README route-table update.
- [ ] No backend change – Validate the key with GET /requests?limit=1 and leave the role unknown until the first run's accepted event. The admin link would appear late or unreliably.

**Prototype screen 07 is an "error states" showcase. How should it appear in the real app?** _(Error states)_

- [x] **Reusable components (Recommended)** – Problem panel, 429 countdown banner, 401 redirect to sign-in, and 504/503 cards, shown wherever those errors actually happen. No standalone page.
- [ ] Components + /dev/errors page – Same components, plus a demo route that renders them all for teaching.

**Outcome:** Built `web/` ("NetCore Assist", v0.8.0): all 8 screens with live SSE runs, resume via `Last-Event-ID`, insights tabs, history, admin status; Nginx gateway image with strict CSP; `GET /api/v1/me`; `web-*` make targets; 27 Vitest tests, 53 API tests; all six docs updated.

---

## Prompt 2

> Can you add a make target to start all containers, including the prerequisites, API and web, with the appropriate dependencies (Chroma, Redis and Postgres), along with populate, access levels and DB migration?

### Clarifications

#### Round 1

**`make populate` re-reads every article and calls OpenAI each time, for table/code descriptions and embeddings, even when Chroma already holds the data. What should the new all-in-one target do about populate?** _(Populate)_

- [x] **Skip if already populated (Recommended)** – Run populate only when a Chroma database is empty, checked by chunk count. Re-runs are fast and free. Force a refresh with POPULATE=1.
- [ ] Always populate – Every run re-embeds both domains. Always fresh, but slower and costs OpenAI credits every time (your account just ran out).

**What should the new target be called?** _(Name)_

- [x] **make up-all (Recommended)** – New target. The existing bootstrap (infrastructure plus local API) and stack-up (containers only) stay unchanged.
- [ ] make demo-up – Same behaviour, but a classroom-oriented name.
- [ ] Extend make bootstrap – Change the existing bootstrap target to also build and start the api and web containers.

**The API container already runs `alembic upgrade head` when it starts. Should the target also run `make db-migrate` from the host, before the API starts?** _(Migrations)_

- [x] **Yes, migrate explicitly (Recommended)** – Postgres starts, then db-migrate runs, then the API starts. A migration error shows up clearly before the API starts. It is harmless if the container repeats it (idempotent).
- [ ] No, rely on the container – One less step. Migration failures only appear in the API container logs and health status.

**Outcome:** Added `make up-all` (chroma → redis → postgres → images → populate only empty domains → access levels → migration → api → web, each waiting for healthy) and `--if-empty` in `populate_vector_dbs.py`; the force flag is `REPOPULATE=1` because `POPULATE` already names the script.
