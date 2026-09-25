# 20 — PLAN (the page map is an interaction graph)

**Objective:** a plan any agent can build without guessing: every page, every section, every clickable
thing and exactly where it leads, every form's success AND failure, every feature's owner.
**Output:** `.deckhand/sitemap.json` lint-clean, `.deckhand/PLAN.md`, work packages. **Gate G1.**

## Schema (`dh plan init` writes a lint-clean example to adapt)
- `pages[]`: `id, route, title, auth (public|user|admin), purpose, sections[], actions[], modals[],
  features[], data (bool), states[] (empty|loading|error for data pages), terminal (bool), entry (bool),
  chrome (false = no global nav)`.
- `sections[]`: `id, slot (hero|features|pricing|faq|cta|testimonials|logo-cloud|stats|team|contact|footer|…),
  actions[]` — the slot vocabulary is shared with try-on and compose.
- `actions[]`: `id, label, to` + for calls `then` (what the user sees on success) and `error` (on failure).
  Target grammar: `route:/path` · `anchor:#section` · `modal:<id>` · `api:METHOD /path` · `external:https://…`
  · `state:<page>.<state>` · `mailto:` · `tel:` · `download:<file>`.
- `nav.header[] / nav.footer[]`: targets; they count as outgoing edges for every page with chrome.
- `features[]`: `id, title, pages[], api[], entities[], emails[], done` (the acceptance sentence).
- `forms[]`: `id, page, fields[], submit, success, error`. `entities[]`: `id, fields[]`.

## Lint (errors block the phase)
E1 id/route unique and valid · E2 every target resolves · E3 every page reachable from `/` (or `entry:true`)
· E4 no dead end (non-terminal page with no way forward) · E5 calls/forms declare `then`+`error` /
`success`+`error` · E6 every API is owned by a feature · E7 features ↔ pages consistent · E8 protected pages
have a login page whose success lands somewhere · E9 anchors exist · E10 modals declared · E11 no unlabeled
action. Warnings: W1 empty page, W3 data page without empty/loading/error, W4 feature without `done`.

## Procedure
1. From brief + research: pick the pages the conversion plays require; map each play to a section/feature.
2. `path=pool|mine`: `dh pool query` → take the top base; its routes seed the map (keep what the base already
   does well; note `weak_for` gaps as features to build). Nothing fits (`gap`) → propose `scratch`.
3. Write `sitemap.json`; loop `dh plan lint` to 0 errors; then `dh plan render` (PLAN.md + mermaid).
4. `dh plan split --agents N` (N = parallel builders available, usually 2–4): WP-00 shell + one WP per feature.
5. `dh phase done plan` → present PLAN.md + chosen base (name, why, gaps, swap cost) → ONE question:
   "approve, or what changes?" Two revision rounds max; beyond that it is a `later` item, not a blocker.

## Copy
Write `.deckhand/copy.json` now if `path=scratch` (it feeds `dh compose`): per section slot
`{heading, text[], actions[{label, href}], items[{title, text, price, bullets[], action}]}`, owner's
language(s), claims only from the brief/research — anything unconfirmed goes to PENDING.
