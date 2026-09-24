# 10 — Match (the registry decides, not the model)

The match is a **script run**. The registry row carries only measured facts.
The assistant's opinion is one sentence; the ranking is reproducible.

## Candidate state

| state | meaning | may be ranked? |
|---|---|---|
| `unverified` + no `stack` | seeded, never measured | **no** — run `template_intake.py` first |
| `unverified` + measured | remote facts present, boot unmeasured | yes (boot bonus absent) |
| `verified` | remote facts + boot scorecard | yes (+5) |
| `rejected` | license/archived/boot failure | never |

Grow the pool: `py scripts/template_intake.py --seed data/templates.seed.json`
(remote only — cloning happens at 20-clone, after the owner picks).

## Score (deterministic, `templates_db.py score`)

| signal | points |
|---|---|
| shape match | +40 |
| feature overlap (accounts, payments, i18n, jobs, admin, tests, database) | +10 each, cap +30 |
| RTL asked **and** template has i18n + RTL | +10 (i18n only: +4) |
| canonical stack (next + postgres + better-auth/none/custom) | +15 |
| boot measured green (start) | +10 (build only: +5) |
| status `verified` | +5 |
| community proof — stars | +5 if ≥1000 · +2 if ≥200 · **−10 if <10 (unproven)** |
| each vendor dep needing a swap | −2, cap −10 |
| stale upstream (>365d) | −20 |
| no tests detected | −5 |

**Blockers (never ranked):** license not MIT/Apache-2.0 · archived · `boot_build_ok = 0` ·
status `rejected`. Boot failure is a pool rejection, not a warning: a template that does not
build is not a template.

**Shape is a heuristic** (`shape_source: heuristic:…` — description + topics + README + tree).
When the owner's classification differs, record it: re-`import` the row with `shape` +
`shape_source: "manual"`. Never edit the DB by hand and never leave `shape` at `unknown` for a
repo you intend to use.

## Deep details (measured, not promised)

A row may carry a detail file (`data/details/<slug>.json`; a compact digest rides the export). It is
the only place that says what the **code** does, so it outranks every heuristic above:

- `features[]` / `locales[]` — measured, so they answer a "French + Arabic, wants invoicing" ask
  on what exists rather than on README keywords;
- `swap_burden` (none|light|medium|heavy) + `vendor[]`, each with the file it was seen in — the real
  price of a non-canonical pick;
- `env.required_at_build[]` — a build that demands a vendor key is a **swap input**, not a broken
  template: it explains some `boot_build_ok = 0` rows and the fix order is swap, then build;
- `pitfalls[]` — native modules, postinstall hooks, tracked `.env` files: read before cloning;
- `blocking[]` — if a detail file declares `injected-payload` or `install-impossible`, the row is a
  **hard blocker** (never cloned, never ranked, reason shown to the owner). It is structured and
  evidence-quoted on purpose: no regex over prose may block a healthy template;
- `verdict.weak_for` — what the owner will have to build themselves. Put it in the top-3 out loud.

No details = not measured, not a blocker. Add them with `references/pool-details.md` (one subagent
per repo, remote only, then one import command).

## Output the owner sees

Top 3, each with:
- name, stars, last push, license, stack in one line;
- **why it ranked** — the script's reasons (it prints up to 12). The **swap cost** line and the
  **`not in stack:`** line are mandatory in what the owner reads; if you trim, trim the others.
- **what it will not do** (the `not in stack:` line — the honest gap);
- swap cost (how many proprietary services must be replaced, and with what).

Then the owner picks. If nothing ranks **> 0**: stop. That is a pool gap, not a build order —
record it (`pool_gap` note with the shape/features asked) and either measure more repos or
tell the owner the pool can't serve this business yet. **Do not fall back to generating an app.**

## Phased mode — this is gate G2 (first half)

Present the top 3, then **stop and wait**. The owner's pick is the gate; do not clone, do not
"prepare while they decide", do not start the next phase in the same turn. One message, one question:
*"which one do I use as the base?"* Their answer starts `20-clone.md`.

## Shape taxonomy

| shape | what it means | example businesses |
|---|---|---|
| saas | accounts + plans; software is the product | invoicing tool, scheduling tool |
| marketplace | two sides, listings + requests | travel marketplace, gig platform |
| booking | time slots, appointments | clinic, salon, tutor |
| catalogue | products/menu, browse + order/enquire | restaurant, shop |
| leadgen | presence + lead capture (**Lane B, not this pool**) | plumber, law firm |
| internal | owner's own team tool | CRM, ops dashboard |

## Stack policy (why canonical matters)

Canonical = **Next.js + PostgreSQL + Better Auth (+ Docker)**. Each non-canonical template (Wasp,
Remix, FastAPI, Clerk, Auth.js) costs a **fresh swap map** that cannot be reused — that is the real
price difference, not the star count. Prefer canonical; allow non-canonical with the cost stated.

## Lane B (declare it, don't fake it)

Presence/lead-gen businesses are out of scope until a marketing-template set exists in the pool.
The design-generation machinery that used to fake this was removed in 0.8.0 on purpose.
