# Changelog

## [2.0.0] — 2026-09-25 — Deckhand v2 (full rework)

One skill (`skills/deckhand`), one control plane (`dh`), one try-on engine. The five v1 skills
(buildout, vps-ops, component-library, session-autopsy, deckhand-profile) are merged; their proven parts
were ported, not rewritten (the Coolify/Hostinger/backup clients and their 40 tests, the ops runbooks,
the measured template pool).

### Why v1 try-on never worked — and what replaced it
| v1 defect (measured) | v2 |
|---|---|
| every click needed the LLM in a polling loop (`wait --follow` + `handle` per pick) — harness-dependent, token-costly, stalls when the agent is busy | the helper does every write itself; the agent is not in the click loop (0 model calls per swap) |
| whole sections were refused ("blocks are never swapped in v1") — the one thing owners wanted | sections are the main case: hero, features, pricing, cta, faq, testimonials, footer, logos, stats, team, contact, login/signup |
| only the item's FIRST file was staged; registry dependencies ignored → broken imports | every file fetched; imports followed recursively; the site's own ui primitives reused |
| a swap flipped a file-wide import (every `<Button>` in the file changed) | element-precise wrapper at the clicked JSX node |
| the owner's words were lost (demo copy shown) | content transplant: headings, text, prices, CTAs+links, images, inputs, `.map()` list data, card-by-card |
| colours were the registry's | palette classes → the site's tokens; missing tokens derived from the site's own colours |
| the Tailark source was the paywalled `tailark.com/r` (401) → 8 free heroes | the MIT OSS source (GitHub) → 300 free blocks; catalog 738 items |
| the parser was the project's `typescript` → TypeScript 7 (no JS API) broke it | vendored `@babel/parser` (MIT) |
| Turbopack rule `as: '*.tsx'` renamed modules → every `'use client'` import broke | no `as`; verified on Next 16.3.6 |
| proxy-less overlay depended on patching the root layout | reverse proxy injects the overlay (any framework); Host/Origin rewritten to `localhost` so Next's dev guard allows HMR |
| demo stock photos / fake "trusted by" logos / "Get a Demo" buttons shipped | replaced by a placeholder / hidden / removed on keep; `dh verify` blocks what remains |

### Added
- `dh` control plane (stdlib Python): phase state machine with gates, `dh next` (one instruction + one
  reference + the relevant lessons), brief, profile + vault + capability doctor, pool query/add (remote
  measuring), plan init/lint/render/split (interaction-graph lint: dead ends, unreachable pages, forms
  without success/error, un-owned APIs, protected pages without login), blackboard for parallel agents,
  clone/adopt/scaffold/compose, swap scan/check, dev runner, rebrand scan/apply/check, verify (12 rows),
  deploy target/ship/smoke over the Coolify client, handoff, ops bots (watchdog, link audit + app-bot
  specs), learn (dh run, from-failure, preflight, promote) with 20 seed lessons, harvest.
- Try-on engine (zero-dependency Node): AST stamp loader (Next Turbopack/webpack, Vite), proxy + overlay,
  catalog ranking (personal library first, base-safe, diverse), fetch with GitHub-source follower +
  cache + fixture replay, materialize, theme normalization, transplant, keep/bake/prune, byte-exact
  discard, save to library, headless CLI, `compose` (a page from blocks + copy).
- Multi-harness installer (`install.sh`, `install.ps1`), `AGENTS.md`, offline CI.
- Compose/try-on content fidelity: CTA-vs-link pairing, copyright line → `© <year> <brand>`, compound
  component roles (`AccordionTrigger`…), lead/body paragraph split, twin card rows as one list, two-tone
  headings, footer/navbar menus from the plan (`lib/sitelinks.mjs`), social rows filtered to the owner's
  networks, design forms hidden unless wired, one `<h1>` per page, design-family coherence, and a
  demo-copy ledger (`.deckhand/demo-copy.json`) that `dh rebrand check` enforces.
- `dh verify` proves routes on the production build it just made (served on a free port, stopped after).
- Kokonut UI items fall back to the project's GitHub mirror when kokonutui.com is unreachable.
- No-domain preview: `dh deploy smoke` warns on plain http / generated `sslip.io` URLs; HANDOFF.md is
  labelled PREVIEW with the no-logins-over-http rule.

### Verified
- Chromium end-to-end on a real Next 16.3.6 app: pick → 3 hero variants with the owner's copy (4/4) →
  cycle → keep (baked, pruned, licence recorded) → save to library; CTA try → discard byte-exact.
- Scratch compose of a 6-section landing page from live Tailark OSS blocks (~6 s): 34/34 owner words
  placed, footer menu from the plan, typecheck clean; `dh rebrand check` blocked the one leftover demo
  sentence and passed after it was rewritten.
- `next build` after keep: type-check passes; 0 stamped files in the production output.
- Suites: 26 node (try-on) · 20 unittest (dh) · 40 pytest (ops clients) — green on Ubuntu and Windows CI.

v1 history: see the git log of `main` up to 6832e0f.
