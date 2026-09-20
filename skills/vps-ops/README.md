# vps-ops

Companion skill to `buildout`: deploy & manage the built project on the user's own VPS with
Coolify — or prove it live at $0 first on the free-preview track.

- **Two tracks, the user's choice** — *paid* (their VPS + domain) or *free preview*
  (Oracle Cloud Always Free + `.pp.ua` + Cloudflare; exit path = the migration ref).
- **Bootstrap** — SSH key, provider firewall, Coolify install, admin/token handoff, hardening, golden snapshot.
- **Ship** — repo → Coolify app + Postgres + envs + domain → first deploy → smoke.
- **Auth + email** — login email that actually arrives: the free failover chain (Resend → Mailgun →
  Brevo) behind a drop-in router, deliverability DNS, and a modular MCP catalog (refs 70/80).
- **Backups offsite, always** — dual cloud targets (B2 + Tigris, both card-free; R2 optional), 3-copy
  retention, verified restore drills (live-proven end-to-end), optional home copy (plain folder **or a
  local RustFS S3 with a console UI**) with a scheduled watchdog; RustFS S3 storage for app uploads (refs 55/56).
- **Operate** — change pipeline (push → auto-deploy → wait → smoke → report), rollback, logs, metrics, backups, updates.
- **Move** — free → paid cutover with a verified integrity gate and a rollback matrix.
- **Handoff** — every deploy writes the app's `OPS.md` (ref 30 §9): access, secret *locations*, and the
  copy-paste commands for the everyday loop — a cold-start door for any future session.
- Universal: pure-stdlib Python scripts; works from Hermes / Claude Code / Codex / any harness.
- The user provides a VPS + domain (Track P) or just an Oracle account (Track F); every browser
  moment is guided click-by-click.

## Install

Copy this folder into the harness's skills dir, or use the combined zip (`deckhand.zip`,
contains `buildout/` + `component-library/` + `vps-ops/`).
Known skill dirs: `~/.claude/skills/`, `~/.agents/skills/`, `~/.codex/skills/`, Hermes profile skills dir.

## Layout

```
SKILL.md
README.md
CHANGELOG.md
references/   00-user-checklist · 10-bootstrap-vps · 11-oracle-free-tier · 20-domain-dns-ssl ·
              21-free-domain-cloudflare · 30-deploy-app · 40-change-pipeline · 50-ops-monitoring ·
              55-offsite-backups · 56-app-object-storage · 60-migrate-to-paid · 70-auth-and-email ·
              80-mcp-integrations
assets/       oci-cloud-init.yaml    (Oracle first-boot: root key + VM firewall)
templates/    OPS-handoff-template.md · mail-router/ (send.ts · schema.sql · .env.example · README) ·
              vps-backup/ (coolify-backup.sh · local-pull.sh · run-pull.cmd · fix-clock.cmd · rustfs-local.compose.yml · README)
scripts/      coolify_api.py · hostinger_api.py      (stdlib only)
tests/        test_coolify_api.py · test_hostinger_api.py
```

## Requirements

Python 3 (3.12+, stdlib), `ssh` + `ssh-keygen` (OpenSSH), `curl`, `git`.
Optional: `gh` (repo creation), `coolify` CLI (MIT).

## Tests

```
py -m unittest discover -s tests -v        # or python3 -m unittest ...
```
30 tests, no network needed.

## License notes

MIT. Coolify = Apache-2.0 (the user's chosen platform); Coolify CLI = MIT; Hostinger MCP server = MIT.
