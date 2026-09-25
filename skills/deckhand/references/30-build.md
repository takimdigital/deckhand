# 30 — BUILD (four ways in, one running app)

**Objective:** a project folder with its own history that runs locally and implements the plan.
**Output:** `dh dev start` answers; `dh phase done build` green. **Gate G2:** the owner opens the URL and says go.

## Entry by path
| path | command | notes |
|---|---|---|
| pool / mine | `dh clone <template> --to <projects_root>/<slug>` | shallow clone at the measured commit, fresh history, `NOTICE`, `.env` from the example with LOCAL secrets generated (never vendor keys), deps installed |
| existing | `dh adopt <folder\|git-url>` | history kept; stack detected; nothing rewritten |
| scratch | `dh scaffold --to <dir>` then `dh compose --sections hero,features,pricing,faq,cta,footer --copy .deckhand/copy.json` | create-next-app + UI base (tokens, `cn`, Button); compose assembles licensed blocks filled with the plan's copy — no code generation |

### copy.json (scratch path) — the only input the model writes: words, never code
```json
{ "hero":     { "eyebrow": "…", "heading": "…", "text": ["…"], "actions": [{ "label": "…", "href": "/order" }],
                "image": { "src": "/hero.jpg", "alt": "…" } },
  "features": { "heading": "…", "text": ["subtitle"], "items": [{ "title": "…", "text": "…" }] },
  "pricing":  { "heading": "…", "items": [{ "title": "…", "price": "€9", "text": "…", "bullets": ["…"],
                "action": { "label": "…", "href": "…" } }] },
  "faq":      { "heading": "…", "items": [{ "title": "question", "text": "answer" }] },
  "footer":   { "text": ["…"], "columns": [{ "title": "…", "links": [{ "label": "…", "href": "/x" }] }],
                "social": ["https://instagram.com/…"] } }
```
Every owner word comes from the plan (never invented); missing facts → `PENDING.md`. Footer columns default
to the sitemap's `nav` (page titles as labels). A section that must keep the design's form says
`"form": true`, and its WP must then wire it with success and error states. Compose scores up to 8 designs per
section (owner words carried, demo left, design family) and reports `dropped` / `demo_copy`: rewrite those
words, never delete the report.

## Swap rented services (pool/existing bases)
`dh swap scan` → `.deckhand/swap-map.json`. Replace ONE vendor at a time, keeping the base's call-site
interfaces (an adapter module), then `dh swap check` (vendor SDK absent + target present). Targets:
clerk/auth0/next-auth → **better-auth** · neon/planetscale/supabase-db → **postgres container** · resend/
sendgrid → **SMTP + failover router** (`templates/ops/mail-router`) · S3/uploadthing/blob → **RustFS/MinIO
(S3 API)** · sentry → logs or GlitchTip · posthog/plausible → **Umami** or none · algolia → **Meilisearch** ·
pusher → **SSE/socket.io** · stripe/paddle/lemonsqueezy → **KEEP** (a processor, not a lock-in).
Swap BEFORE the first build when the base validates env at build time. A swap bigger than a day is a scope
decision for the owner, never a silent half-swap. Smoke the swapped path (sign-up → session → protected page;
migrate → write → read), not the home page.

## Implementing the plan
- Solo: build WP by WP in `.deckhand/work/index.json` order (WP-00 shell first).
- Parallel: one sub-agent per lane (`agent` field) with its WP brief; coordination only via
  `dh bb post|read`. Merge order: WP-00, then features; `dh plan lint` + route smoke after each merge.
- Every page from the plan exists; every action reaches its declared target; every call shows its success
  and error state. Forms validate server-side. Seed data is realistic but marked as sample.
- Run commands through `dh run -- …` (known failures print their fix immediately).

## Run it
`dh dev start` (detached; `.deckhand/dev.log`; waits until it answers) → give the owner the URL and a
3-line test script (what to click, what should happen). `dh phase done build` → **G2**.

## Traps
Read `dh learn preflight build` output — it is printed by `dh next` and is the current list.
