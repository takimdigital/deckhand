# vps-ops

Companion skill to `expert-build-pack`: deploy & manage the built project on the user's own VPS with Coolify.

- **Bootstrap** — SSH key, provider firewall, Coolify install, admin/token handoff, hardening, golden snapshot.
- **Ship** — repo → Coolify app + Postgres + envs + domain → first deploy → smoke.
- **Operate** — change pipeline (push → auto-deploy → wait → smoke → report), rollback, logs, metrics, backups, updates.
- Universal: pure-stdlib Python scripts; works from Hermes / Claude Code / Codex / any harness.
- The user provides only a VPS + domain; the two one-time browser approvals are guided click-by-click.

## Install

Copy this folder into the harness's skills dir, or use the combined zip (`expert-build-pack.zip`,
contains `expert-build-pack/` + `component-library/` + `vps-ops/`).
Known skill dirs: `~/.claude/skills/`, `~/.agents/skills/`, `~/.codex/skills/`, Hermes profile skills dir.

## Layout

```
SKILL.md
README.md
references/   00-user-checklist · 10-bootstrap-vps · 20-domain-dns-ssl · 30-deploy-app · 40-change-pipeline · 50-ops-monitoring
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
23 tests, no network needed.

## License notes

MIT. Coolify = Apache-2.0 (the user's chosen platform); Coolify CLI = MIT; Hostinger MCP server = MIT.
