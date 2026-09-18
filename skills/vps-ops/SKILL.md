---
name: vps-ops
description: "Deploy and manage apps on a VPS with Coolify."
version: 0.1.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [deploy, vps, coolify, hostinger, dns, ssl, ssh, operations, backups, rollback]
    related_skills: [expert-build-pack, component-library]
---

# vps-ops — VPS deploy & management (Coolify)

Takes a project built by `expert-build-pack` and ships it to a real server: bootstrap the VPS, install
Coolify, point the domain, deploy, and then run the whole "user asks for a change → it ships" loop —
all from the harness, without the user ever touching the server.

## When to use

- The user wants to deploy/host/go live, mentions a VPS, Coolify, domain/DNS/SSL, or "put my app online".
- Any post-deploy request: check status, read logs, ship a change, roll back, backups, updates.
- The buildout skill (`expert-build-pack`) finished in the project — deploy is the next phase.

## The promise (what the user does vs what you do)

The user provides ONLY: VPS + domain (+ optionally a provider API token). Everything else is your job.
Two one-time browser moments are unavoidable and are guided click-by-click in `references/00-user-checklist.md`:
1. Create the Coolify admin account + copy one API token.
2. (Private repos) approve the GitHub App install.

Never ask the user to open a terminal on the server or run server commands — you run everything
via `ssh`/API from the harness.

## Invariants (never violate)

- Secrets live ONLY in `~/.vps-ops/` (chmod 600) and in Coolify env vars. Never in repos, chat, or logs.
- Never disable SSH (port 22) — Coolify manages servers over SSH, including localhost.
- Validate before write: DNS changes go through `validate` first; firewall changes keep 22 open;
  GET-before-PUT snapshots anything you overwrite.
- Components must be free/permissive open source. Coolify itself is Apache-2.0 (user-approved).
- No "deployed" claim without BOTH: terminal deployment status (`coolify_api.py wait`) and a passing
  smoke check (`coolify_api.py smoke`).
- Never print token values; reference them as `$COOLIFY_TOKEN` / `$HOSTINGER_API_TOKEN`.

## Layout & routing table

| Need | Read |
|---|---|
| What to collect from the user; provider cheat sheets; business keys matrix | `references/00-user-checklist.md` |
| First-time setup: SSH key → firewall → Coolify install → admin/token → hardening → snapshot | `references/10-bootstrap-vps.md` |
| Domain: A records (API or manual), propagation, instance domain, Let's Encrypt verify | `references/20-domain-dns-ssl.md` |
| Deploy an app: repo → project/app → envs → Postgres → domain → first deploy → smoke | `references/30-deploy-app.md` |
| The change loop: edit → push → auto-deploy → wait → smoke → report; rollback | `references/40-change-pipeline.md` |
| Status, logs, metrics, backups, updates, incident playbook | `references/50-ops-monitoring.md` |

## Tools of the trade

Universal path (works in ANY harness, stdlib only):

- `scripts/coolify_api.py` — `health | apps | app <uuid> | deploy <uuid> [--force] | deployments <uuid> | wait <uuid> [--timeout 900] | logs <uuid> [--lines 200] [--timestamps] | envs <uuid> | envset <uuid> KEY=VAL... | status | smoke <url> [--expect 200] [--contains TEXT]`
- `scripts/hostinger_api.py` — `vm list|get|metrics|restart` · `snapshot create|list` · `sshkey ensure --vm <id>` · `dns get|set-a` · `firewall ensure --vm <id>` · `actions <vm> [action_id]`

Run with `py scripts/coolify_api.py --help` on Windows, `python3 ...` elsewhere.
Exit codes: `0` ok · `3` deploy failed · `4` http/smoke error · `5` wait timeout · `6` unexpected.

Optional extras (never required): Coolify CLI (MIT, `coolify ...`) and MCP wiring — see
`references/10-bootstrap-vps.md`.

## Session anchor

Every deployed project keeps `<project>/.vps-ops.json` (server/app/db UUIDs + domain + coolify_url —
NO secrets). Read it first in any later session; it re-enters the whole pipeline without context loss.

## Quickstart

1. Checklist + collect → `references/00-user-checklist.md`
2. Bootstrap the VPS → `references/10-bootstrap-vps.md`
3. Domain + SSL → `references/20-domain-dns-ssl.md`
4. Deploy → `references/30-deploy-app.md`
5. From then on → `references/40-change-pipeline.md` + `references/50-ops-monitoring.md`
