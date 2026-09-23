# 20 — Clone (the only step that touches the owner's disk)

Nothing is cloned until the owner picks a match. Intake and matching read GitHub remotely.
Projects live on **disk D**. Never install to C: (it is nearly full on this host).

## Command

```
py scripts/factory_clone.py --template <name> --slug <slug> --root D:/ [--ref <commit|tag>] [--install]
```

- `--template` reads the registry row (license gate runs: no verified MIT/Apache → refuse, exit 4).
- `--ref` pins the upstream commit. **Pin it in the record even when you don't pass it** —
  the scorecard stores the resolved commit, so a project can always be explained later.
- Refuses an existing non-empty folder (exit 5). No merging into someone's work.

## What lands on disk

```
D:/<slug>/
  <the template as-is>          # no rewriting at clone time — ever
  .factory/match.json           # template, repo, upstream commit, license, stack, cloned_at
  .factory/swap-map.json        # vendor -> target drafts from intake (status pending)
  .factory/brand.json           # empty; filled at 40-rebrand
  .factory/scorecard.md         # the record a buyer/dev can read
  PENDING.md                    # the mandatory facts only
```

Fresh git history: upstream `.git` is dropped, `git init` + one commit
(`chore: clone <template> via buildout factory (upstream <sha>)`). The owner's repo starts at
commit 1; upstream history is not theirs to carry.

## Order: clone → **swap** → build

Many templates validate their env at build time (zod/env schemas) and refuse to build without the
vendor's keys — measured case: `ixartz/Next-js-Boilerplate` requires `CLERK_SECRET_KEY` with
`z.string().min(1)`, so `npm run build` cannot pass before the auth swap. A build failure whose
output names `CLERK_…`, `STRIPE_…`, `SENTRY_…`, `RESEND_…`, `DATABASE_URL`, … is a **swap input,
not a pool rejection**: `template_intake.py --deep` records it as a `vendor-keys-required` flag and
the scorer keeps the candidate rankable.

## Boot (measure, never assert)

```
cd D:/<slug> && <pm> install     # pnpm store is already D:/pnpm-store
<pm> run build
<pm> run start  (or dev)         # scratch port, e.g. 7390
```

Record in `templates.db` (`boot_install_ok`, `boot_build_ok`, `boot_start_ok`, `boot_ms`, `boot_port`).
Evidence rules:
- HTTP 200 is not proof of freshness — capture a build id, asset hash or served CSS token and
  show it came from **this** build;
- install failure → the row is `rejected` with the reason; report it to the owner in one line.

## Env scaffold

Copy `.env.example` → `.env` and fill only what boot needs (DB URL, auth secret, SMTP).
Every value the owner must supply later goes to `PENDING.md`, never into a fake default.
`.env` is gitignored by the template; verify that before the first commit.

## Done when

- folder exists on D:, one commit, `.factory/*` complete;
- install + build + start observed with a pasteable log line;
- `PENDING.md` lists only facts only the owner can give (domain, email, legal, photos, payment, date).
