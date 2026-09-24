# 20 — Clone (the only step that touches the owner's disk)

Nothing is cloned until the owner picks a match. Intake and matching read GitHub remotely.
Projects land in the **projects root** (default `D:/<slug>` on this host; `--root` overrides —
on a non-Windows host pass the root explicitly, the script refuses a Windows-style path there).

## Command

```
py scripts/factory_clone.py --template <name> --slug <slug> --root D:/ [--ref <branch|tag|sha>] [--install]
```

- `--template` reads the registry row (license gate runs: no verified MIT/Apache → refuse, exit 4).
- `--repo owner/name` bypasses the registry — the licence is then **measured live** (GitHub API) and
  a local-path fixture must carry its own LICENSE file. Never assume; the gate is measured either way.
- `--ref` pins the upstream code: a branch or tag goes straight in; a **commit sha** is fetched and
  checked out detached (plain `git clone --branch <sha>` fails). **Record the resolved commit even
  when you don't pass `--ref`** — the scorecard stores it, so a project can always be explained later.
- Refuses an existing non-empty folder (exit 5). No merging into someone's work.

## What lands on disk

```
D:/<slug>/
  <the template as-is>          # no rewriting at clone time — ever
  .factory/match.json           # template, repo, upstream commit, license, stack, cloned_at
  .factory/swap-map.json        # vendor -> target entries: registry row + a scan of THIS clone
  .factory/brand.json           # empty; filled at 40-rebrand
  .factory/scorecard.md         # the record a buyer/dev can read
  PENDING.md                    # the mandatory facts only
```

The swap map is **measured from the clone**, not only from the registry row: intake sees dep names,
the local scan also reads `package.json`, `.env.example` and the README, so a vendor that appears
only in code or docs still lands in the map (marked `source: local-scan`). If the map comes out
empty, the clone says so and `swap_check` refuses it (exit 3) — an empty map is not a pass.

Fresh git history: upstream `.git` is dropped, `git init` + one commit
(`chore: clone <template> via buildout factory (upstream <sha>)`), cut **before** the install so no
`node_modules`/`.next` can enter commit 1. The owner's repo starts at commit 1; upstream history is
not theirs to carry.

## Order: clone → **swap** → build

Many templates validate their env at build time (zod/env schemas) and refuse to build without the
vendor's keys — measured case: `ixartz/Next-js-Boilerplate` requires `CLERK_SECRET_KEY` with
`z.string().min(1)`, so `npm run build` cannot pass before the auth swap. A build failure whose
output names `CLERK_…`, `STRIPE_…`, `SENTRY_…`, `RESEND_…`, `DATABASE_URL`, … is a **swap input,
not a pool rejection**: `template_intake.py --deep` records it as a `vendor-keys-required` flag and
the scorer keeps the candidate rankable.

## Boot (measure, never assert)

**Read the template's own scripts before assuming a port.** Measured case (`salmanshahriar/Next-Elite`):
`"start": "next start -p 6767"` — the port is hardcoded in the script, so `PORT=… npm run start`
serves on 6767 anyway. Read `scripts` in `package.json`, then curl *that* port.
`output: "standalone"` prints a warning that `next start` is not the right runner — the deploy
target is `node .next/standalone/server.js` (or the template's Dockerfile); record it for ref 50.

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

## Phased mode — end the run here (gate G2, second half)

A clone is the fast, quiet part: install, build, start, prove it answers — then **hand it over**. The
message is a local URL and one line on what the owner is looking at ("this is the base, in its own
skin — your design and brand land in the next phase"). Then stop. No rebrand, no extra features, no
deploy in the same turn: that is G3/G4, and the owner tests first.

Running it locally, the parts that bite:

- **Start the server as a background process**, then poll a health check until it answers — a
  foreground `npm run dev` is refused/blocked by the harness, and a browser pointed at a
  not-yet-listening port just proves the port is closed.
- **Read the port from the project**, never assume 3000; a second app (or the previous phase's server)
  is often still holding it — `EADDRINUSE … 127.0.0.1:5770` is a stale process, not a bug. Kill it
  before rebinding (on Windows from git-bash: `taskkill //F //PID <pid>` — double slashes; single
  slashes get mangled into paths).
- **Prove the page served is the build you made** (chunk hashes / BUILD_ID), not a cached one.

## Env scaffold

Copy `.env.example` → `.env` and fill only what boot needs (DB URL, auth secret, SMTP).
Every value the owner must supply later goes to `PENDING.md`, never into a fake default.
`.env` is gitignored by the template; verify that before the first commit (the clone step adds the
ignore rule itself when the template forgot one).

**Secrets the app needs only locally are generated, not faked.** Measured case: the pilot boots
green and still prints `[auth] Missing BETTER_AUTH_SECRET` — sessions are insecure without it. A
*project* secret (`BETTER_AUTH_SECRET`, `NEXTAUTH_SECRET`, `APP_KEY`, 32+ chars) is not a vendor
credential: generate one (`py -c "import secrets;print(secrets.token_hex(32))"`), put it in `.env`,
and add a `PENDING.md` line to rotate it for production. Never generate a *vendor* key
(Clerk/Stripe/…): those are what the swap phase removes.

## Done when

- folder exists in the projects root, one commit (cut before any install), `.factory/*` complete;
- `swap-map.json` has entries, or the run warned EMPTY and `template_intake.py` is the next step;
- install + build + start observed with a pasteable log line. **For a template whose build names
  vendor keys, this evidence is produced after the swap** (ref 30) — the contract with SKILL.md's
  phase table: phase 2 proves the clone landed, phase 3 proves it swaps AND builds;
- `PENDING.md` lists only facts only the owner can give (domain, email, legal, photos, payment, date).
