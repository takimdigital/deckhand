---
name: vps-ops
description: "Deploy apps on a VPS with Coolify — free preview or paid."
version: 0.7.2
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [deploy, vps, coolify, hostinger, oracle, free-tier, preview, cloudflare, dns, ssl, ssh, operations, backups, rollback, migration]
    related_skills: [buildout, component-library]
---

# vps-ops — VPS deploy & management (Coolify)

Takes a project built by `buildout` and ships it to a real server: bootstrap the VPS, install
Coolify, point the domain, deploy, and then run the whole "user asks for a change → it ships" loop —
all from the harness, without the user ever touching the server.

## When to use

- The user wants to deploy/host/go live, mentions a VPS, Coolify, domain/DNS/SSL, or "put my app online".
- Any post-deploy request: check status, read logs, ship a change, roll back, backups, updates.
- The buildout skill finished in the project — deploy is the next phase.
- The user has no VPS/domain yet, or wants a $0 live preview → Track F: `references/11-oracle-free-tier.md` (+ `21` for the free domain).
- The user wants to leave the preview (or move any server → server) → `references/60-migrate-to-paid.md`.

## The promise (what the user does vs what you do)

First read the user's portable files — `~/.deckhand/profile.md` (accounts, providers, defaults) and `~/.deckhand/pending.md` (the ledger of human tasks; skill `deckhand-profile`). Never re-ask what the profile answers. **Surface open pending items in every report** (short, with ages) and **record new human tasks the moment they appear** — keys to paste, clicks, escrows, rotations.
The user provides ONLY: VPS + domain (+ optionally a provider API token). Everything else is your job.
Two one-time browser moments are unavoidable and are guided click-by-click in `references/00-user-checklist.md`:
1. Create the Coolify admin account + copy one API token.
2. (Private repos) approve the GitHub App install.

Never ask the user to open a terminal on the server or run server commands — you run everything
via `ssh`/API from the harness.

## Two deployment tracks — the user chooses, nothing is forced

**Track P — paid/direct (default when a VPS is already at hand).** The user provides a real VPS + real
domain → this runbook exactly as documented: `00 → 10 → 20 → 30 → 40/50`.

**Track F — free preview (offered, never forced).** The user has no VPS/domain yet, or wants to prove
the business live at $0 before paying: Oracle Cloud Always Free server + free `.pp.ua` domain (nic.ua)
+ Cloudflare DNS-only + Coolify's automatic Let's Encrypt — a real, live deployment on a disposable
host, with a clean exit (`60-migrate-to-paid.md`) when the business proves itself.

Ask ONCE, batched, at deploy time: *"Free preview first ($0) — or your own VPS + real domain now?"*
Smart defaults avoid the question: VPS+domain already handed over → Track P. Nothing provided yet and
cost / "test first" signals → recommend Track F, still as a choice. **One track per run** — never mix
the paid bootstrap (`10`) and the OCI bootstrap (`11`) in a single deployment.

> Track F status: researched + primary-source-verified 2026-09-18; first live run pending — items
> marked `[verify at live drill]` in refs 11/21/60 are open until exercised.

## Invariants (never violate)

- Secrets live ONLY in `~/.vps-ops/` (chmod 600) and in Coolify env vars. Never in repos, chat, or logs.
- Never disable SSH (port 22) — Coolify manages servers over SSH, including localhost.
- Validate before write: DNS changes go through `validate` first; firewall changes keep 22 open;
  GET-before-PUT snapshots anything you overwrite.
- Components must be free/permissive open source. Coolify itself is Apache-2.0 (user-approved).
- No "deployed" claim without BOTH: terminal deployment status (`coolify_api.py wait`) and a passing
  smoke check (`coolify_api.py smoke`).
- Never print token values; reference them as `$COOLIFY_TOKEN` / `$HOSTINGER_API_TOKEN`.
- Every invariant above applies to BOTH tracks. The free preview is a DISPOSABLE host: never present it as production-grade durability — say "preview" in reports; ref `60` is the exit path.
- Keep Coolify's dashboard OFF the public internet on EVERY track: loopback-bind its ports in Coolify's own compose (ref 10 Step 3b) + SSH tunnel — host firewall rules alone do NOT stop Docker-published ports (live-verified on Docker 29, 2026-09-19).

## Layout & routing table

| Need | Read |
|---|---|
| What to collect from the user; provider cheat sheets; business keys matrix | `references/00-user-checklist.md` |
| First-time setup (paid track): SSH key → firewall → Coolify install → admin/token → hardening → snapshot | `references/10-bootstrap-vps.md` |
| Free preview server (Oracle Always Free, Arm): signup/PAYG, instance, two firewalls, tunnel dashboard | `references/11-oracle-free-tier.md` |
| Which provider / how much? Prices + sizing for Oracle / Contabo / Hostinger / Hetzner | `references/12-provider-price-sheet.md` |
| Domain: A records (API or manual), propagation, instance domain, Let's Encrypt verify | `references/20-domain-dns-ssl.md` |
| Preview domain: free `.pp.ua` (nic.ua) or an owned domain at any registrar → Cloudflare DNS-only zone | `references/21-free-domain-cloudflare.md` |
| Deploy an app: repo → project/app → envs → Postgres → domain → first deploy → smoke | `references/30-deploy-app.md` |
| Already-deployed app, fresh session, zero context — the cold-start doc | the app repo's **`OPS.md`** first → then refs 40/50 (written at deploy time, ref 30 §9) |
| The change loop: edit → push → auto-deploy → wait → smoke → report; rollback | `references/40-change-pipeline.md` |
| Status, logs, metrics, backups, updates, incident playbook | `references/50-ops-monitoring.md` |
| Offsite backups — dual target (B2 + Tigris, both card-free; R2 optional), schedules, verification, restore reality · home copy (plain folder or a local RustFS S3) | `references/55-offsite-backups.md` |
| App uploads — S3-compatible storage (RustFS) via Coolify + its offsite copy | `references/56-app-object-storage.md` |
| Leave the preview → paid host: what moves, cutover, rollback | `references/60-migrate-to-paid.md` |
| Auth + login email: verdict, free email chain, deliverability DNS, failover router | `references/70-auth-and-email.md` |
| MCP integrations catalog (DNS/registrar, email — modular, extend per domain) | `references/80-mcp-integrations.md` |

## Tools of the trade

Universal path (works in ANY harness, stdlib only):

- `scripts/coolify_api.py` — `health | apps | app <uuid> | deploy <uuid> [--force] | deployments <uuid> | wait <uuid> [--timeout 900] | logs <uuid> [--lines 200] [--timestamps] | envs <uuid> | envset <uuid> KEY=VAL... | status | smoke <url> [--expect 200] [--contains TEXT]`
- `scripts/hostinger_api.py` — `vm list|get|metrics|restart` · `snapshot create|list` · `sshkey ensure --vm <id>` · `dns get|set-a` · `firewall ensure --vm <id>` · `actions <vm> [action_id]`

Run with `py scripts/coolify_api.py --help` on Windows, `python3 ...` elsewhere.
Exit codes: `0` ok · `3` deploy failed · `4` http/smoke error · `5` wait timeout · `6` unexpected.

Optional extras (never required): Coolify CLI (MIT, `coolify ...`) and MCP wiring — see
`references/10-bootstrap-vps.md`.

Oracle free-track asset: `assets/oci-cloud-init.yaml` — hand its contents to the user to paste into
the instance's Initialization script (ref `11-oracle-free-tier.md`); at first boot it installs the
root SSH key and opens 80/443 in the VM firewall.

## Session anchor

Every deployed project keeps `<project>/.vps-ops.json` (server/app/db UUIDs + domain + coolify_url —
NO secrets, plus `track: paid | free-preview` and the Oracle region on Track F). Read it first in any
later session; it re-enters the whole pipeline without context loss. Every deploy ALSO writes
`<project>/OPS.md` (ref 30 §9) — the human-readable cold-start handoff (live URL, access, secret
*locations*, the copy-paste everyday commands). Anchor = for the agent's tooling; `OPS.md` = for reading.

## Quickstart

0. Pick the track (ask once): VPS+domain already at hand → **P**; nothing yet / $0-first → **F**.
1. Checklist + collect → `references/00-user-checklist.md` (+ §3b for Track F)
2. **P:** bootstrap the VPS → `references/10-bootstrap-vps.md`
   **F:** free server → `references/11-oracle-free-tier.md`
3. Domain + SSL → `references/20-domain-dns-ssl.md` · **F:** `references/21-free-domain-cloudflare.md`
4. Deploy → `references/30-deploy-app.md`
5. First-run data + handoff → `references/30-deploy-app.md` §6b (migrations/seed/owner) and §9 (`OPS.md` — commit it with the app)
6. From then on → `references/40-change-pipeline.md` + `references/50-ops-monitoring.md`
7. Backups offsite (default, dual target) → `references/55-offsite-backups.md`; app stores uploads? → `references/56-app-object-storage.md`
8. App must send login email (verify/reset)? → `references/70-auth-and-email.md` (+ `templates/mail-router/`)
9. **F only, on request:** leave the preview → `references/60-migrate-to-paid.md`
