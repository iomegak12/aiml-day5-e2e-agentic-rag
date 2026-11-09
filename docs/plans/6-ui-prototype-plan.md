# Plan: Navigable UI prototype from the Stitch mockups

## Context
`docs/ui-mockups/stitch_netcore_assist_web_app/` holds the 8 Google Stitch screens I prompted for, plus `DESIGN.md`:
- Each screen has a `code.html` (Tailwind CDN, Inter + Material Symbols) and a `screen.png`.
- They are isolated: every link is `#`, the popovers are frozen open, and the tabs do nothing.
- Stitch also introduced issues:
  - a broken logo image (remote `lh3.googleusercontent.com` URL)
  - top-nav items with no backing API ("Topology & Telemetry", "Audit Logs")
  - an RBAC error: Bob (Employee) is shown KB-MTG-2006 as **Restricted** (it is `internal`)

Goal: a reviewable, clickable prototype that shows how the app behaves against the REST API. The Stitch originals stay untouched.

## Decisions (MCQs)
| Topic | Decision |
|---|---|
| Interactivity | Linked + light JS behaviours |
| Index | Screen gallery |
| Stitch issues | Fix them, and list every fix in index.html |
| Location | `docs/ui-mockups/prototype/` (originals untouched) |

## Output: `docs/ui-mockups/prototype/`
```
index.html                 gallery
01-sign-in.html            02-new-chat.html          03-live-run.html         04-answer-insights.html
05-request-history.html    06-request-detail.html    07-error-states.html     08-system-status.html
assets/prototype.js        shared behaviours + navigation map
assets/prototype.css       review bar, toasts, small fixes
assets/logo.svg            inline-able NetCore Assist logo
```
- Each screen is the Stitch `code.html` copied and transformed: links wired, fixes applied, assets included.
- A generator (`docs/ui-mockups/build_prototype.py`, BeautifulSoup is already a dependency) reproduces `prototype/` from the Stitch folder, so re-exporting from Stitch only needs a re-run.

## index.html (gallery)
- Header: the product name, "how to review", and a "Start the walkthrough →" link to `01-sign-in.html`.
- 8 cards. Each has the `screen.png` thumbnail (from the Stitch folder), title, purpose, the **API endpoints it consumes**, key interactions to try, and an "Open screen" link.
- A "Fixes applied to the Stitch output" list.
- The same visual language (Inter, white, soft pastel glow, rounded cards).

## Navigation map (all screens)
- **Shared shell (screens 2–8):**
  - "New chat" → 02.
  - History items → 04 (completed), 03 (running) or 06 (disconnected).
  - "System status" → 08, shown only for the admin.
  - Avatar → 01 (sign out).
  - Top nav becomes **Chat (02) | Requests (05)**; the unsupported items are removed.
- **01 Sign-in:** "Continue" or a demo-user card → 02. The chosen user (alice, bob, carol) is kept in `localStorage`; the shell then shows that name and role badge, and hides "System status" for non-admins.
- **02 New chat:** the mode dropdown and the Options popover start **closed** and toggle on click (with outside-click close). Send or an example chip → 03.
- **03 Live run:**
  - Simulates the SSE stream: step 2 spinner → done, log lines append, then "Judge evaluating…".
  - After about 6 s, a "Completed → View answer" banner leads to 04.
  - "Stop watching" → 06, as a simulated disconnect.
- **04 Answer + Insights:**
  - The tabs (Plan, Sources, Judge, Tool calls, Trace, Timing) switch panels. Missing panels (Plan, Trace) are added using the API's response shape.
  - The Copy buttons copy. "View request" → 06. Citation chips scroll to the matching source.
- **05 Request history:** the status filter pills filter rows client-side. Rows → 04, 03 or 06; "Resume" → 06; "Load more" shows a toast.
- **06 Request detail / Resume:** the replayed timeline items appear one by one, then the banner switches to "Live". "Open full insights" → 04.
- **07 Error states:**
  - The 429 countdown ticks down to 0, then re-enables send.
  - "Problem details" collapses and expands.
  - "Check result later" → 06, "Sign in again" → 01, "Retry" shows a toast.
- **08 System status:** "Refresh" updates "checked N s ago" and re-randomises latencies slightly. A non-admin opening it sees a "403-style admin only" notice.
- **Review bar** (fixed at the bottom, every screen):
  - "← Index"
  - screen number and title
  - Prev / Next
  - the user switcher (alice / bob / carol)

## Fixes applied (also listed in index.html)
1. **Logo:** the broken remote image becomes an inline SVG logo. The avatar becomes an initials avatar, so nothing loads from googleusercontent.
2. **Top nav:** items not backed by the API are removed; Chat and Requests are added.
3. **RBAC data:** KB-MTG-2006 → Internal for Bob. Data is checked against the API roles: guest = public, employee = public + internal, admin = all.
4. **Popovers and menus** that Stitch rendered open become closed by default and interactive.
5. Odd generated copy that doesn't match the backend (e.g. "Topology Vector Traversal" on the error screen) is reviewed and aligned with the real API fields (request_id, status, RFC 9457 problem).

## Verification
1. Run the generator → 8 screens + index + assets exist; the Stitch folder is unchanged (`git status`).
2. A link checker (Python) confirms every `href` in `prototype/` resolves to an existing file, apart from deliberate in-page anchors.
3. Check the JS syntax (`node --check`, if Node is available).
4. Serve the prototype with `python -m http.server -d docs/ui-mockups/prototype` and walk the main journeys:
   - sign-in → new chat → live run → answer
   - stop watching → resume
   - history filters
   - the 429 countdown
   - non-admin vs admin access to System status
5. Report anything I could not check visually (no browser automation here), so you can do the visual pass.
