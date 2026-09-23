# Pool details — the measured digest of a template

The registry row says *what* a template is (licence, stack, stars, boot). The **detail file** says
what it is like to work with: real routes, real features, the env names it demands at build time,
the deploy story, the rebrand surface, and the traps that will cost an hour.

Three places hold it, each for a different reader:

| Where | What | Who reads it |
|---|---|---|
| `templates.db` → `details` column | the full JSON blob, queryable via `features`/`locales`/`swap_burden` | scripts (`score`, matching) |
| `data/details/<slug>.json` | the same JSON, one file per template, shipped | an agent, on demand |
| `data/templates.json` → `details_digest` | a compact digest (`features`, `locales`, `swap_burden`, routes count, deploy summary, pitfall kinds, health) | an agent scanning the whole pool cheaply |

The bulk export deliberately does **not** carry the blobs: 8 templates × ~25 KB would flood the
context of every agent that opens the pool. Read one `data/details/<slug>.json` when you actually
need it — that is the whole point of the split.

## Adding details (once per template, then never again)

Fan out **one subagent per repo** (`delegate_task`, up to 10 in one call). Each writes exactly one
file; nothing else is written, nothing is cloned. Give every subagent:

1. the repo slug and the output path `…/cache/scratch/pool-details/<slug>.json`;
2. `references/pool-details-contract.md` — the field-by-field schema, read first;
3. the four hard rules: remote-only (GitHub API), env vars **by name only**, evidence per fact,
   honest `null` over a guess.

Subagents cannot touch the registry (that would race), so the import is a single deterministic step
you run yourself once they are done.

## Importing

```bash
py scripts/templates_db.py import-details <dir-or-file> [--store data/details] [--json]
```

What the gate refuses (each with the reason on stderr, exit 1):

- `repo` or `slug` missing — the file is not addressable;
- a **credential-shaped value** anywhere in the text (`sk_live_…`, `ghp_…`, `AKIA…`, a private-key
  header …). Env vars travel by name; a value in the pool is a leak that ships to every user;
- a repo that is **not in the registry** — measure the repo first
  (`py scripts/template_intake.py --repo <owner/name>`);
- a file whose slug matches a row that measures a **different repo** (cross-attachment) — that would
  silently describe the wrong template.

It accepts and stores: `details` (blob), `details_at`, `details_file`, and the promoted columns
`features`, `locales`, `swap_burden` (normalised to `none|light|medium|heavy`).
Warnings (missing section, no `evidence`, no `unmeasured`) are printed but do not block — treat them
as the subagent's honesty report.

Then re-export so the pool the agent reads matches the truth:

```bash
py scripts/templates_db.py export
```

## Blocking a template (structured, or nothing)

A detail file may carry `"blocking": []` — the only channel for a claim that stops a template from
ever being used. Two kinds exist: `injected-payload` (shipped code carries an obfuscated/injected
blob) and `install-impossible` (a dependency that does not exist, a build that cannot install).
Each entry quotes its own `evidence` — the 404, the character count, the command that showed it.

Rules learned the hard way:

- **Only `blocking[]` blocks.** The first importer derived flags by regexing `pitfalls` prose and
  gave two healthy templates a blocker — `no bun lockfile` (while an npm lockfile exists) and a
  passing mention of `npm ci`. A false flag costs a good candidate; a regex over free text is not
  a measurement.
- Importing sets `risk_flags[].kind` with `"source": "pool-details"`; a later intake run merges and
  keeps them (intake owns the repo facts, the detail file owns its derived blockers).
- A blocked row can never be ranked: it lands in the `blocked:` list with the reason, and the owner
  is told why — never silently dropped.
- The pool owner re-verifies a `blocking` claim before it ships (open the file, run the command).
- Unknown kinds and missing evidence are warnings at import, so the contract can grow without
  breaking older files.

## Budgets

- One subagent per repo; ≤10 per batch (harness limit). ~5 minutes each, ~30 GitHub API calls.
- Detail file ≤ ~40 KB. If it grows past that, the schema is being abused: it is a digest, not a
  dossier, and the bulk export pays for it.
- Never clone to measure: `gh api` + `raw.githubusercontent.com` answer everything in the contract.

## Using it later (this is why it exists)

- **match**: the digest carries measured `features` and `locales`, so a "French + Arabic, RTL, wants
  invoicing" ask can be ranked on what the code does instead of on keywords in a README.
- **clone**: `deploy.build_cmd` / `start_cmd` / `migrations_cmd`, `env.required_at_build` (a build
  that needs a vendor key is a swap input, not a broken template), `pitfalls` (native modules,
  postinstall hooks, tracked `.env` files), `monorepo.workspaces`.
- **swap**: `vendor[]` names what to remove and what to put in its place, with the file it was seen in.
- **rebrand**: `rebrand_surface[]` + `hardcoded_demo_content[]` — the files that carry someone else's
  name, logo or copy.
- **verify / deploy**: `deploy.docker`, `standalone_output`, `dockerfile_port`, `tests.*`, and
  `verdict.weak_for` (what you will have to build yourself before the site is honest).
