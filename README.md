<p align="center">
  <img src="assets/logo.svg" width="108" alt="Expert Build Pack">
</p>

<h1 align="center">Expert Build Pack</h1>

<p align="center">
  <b>Agent skills that take a product from idea to a live, self-hosted SaaS.<br>
  Build it, deploy it, change it, roll it back — from the chat.</b>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Tests: 36 passing" src="https://img.shields.io/badge/tests-36%20passing-brightgreen.svg">
  <img alt="Version: 0.2.1" src="https://img.shields.io/badge/version-0.2.1-blueviolet.svg">
  <img alt="Works with Claude Code, Codex, Cursor, Hermes" src="https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Codex%20%7C%20Cursor%20%7C%20Hermes-black.svg">
</p>

---

Three skill folders. Drop them into your AI coding agent and it can:

- **build** a real product from an idea — expert playbooks, execution-first loops, verified MIT boilerplates, and a coherent design assembled from a living pool of MIT component registries;
- **store** every component you build and reuse it in the next project;
- **deploy** to your own VPS — Coolify bootstrapped, domain + SSL attached, apps built and served;
- **operate** afterwards — change → push → deploy → smoke test → rollback, plus logs, metrics, backups and restore drills, entirely via API.

## ⚡ The skills

| Skill | What it does |
| --- | --- |
| [`expert-build-pack`](skills/expert-build-pack) | **Idea → codebase.** Expert references, execution-first build loops, verified MIT boilerplates, coherent-random design assembly from the live shadcn registry pool (MIT-only), design tokens locked once and applied everywhere. |
| [`component-library`](skills/component-library) | **Build → reuse.** Save any component you build; the next project starts from what you already made. |
| [`vps-ops`](skills/vps-ops) | **Codebase → live business.** Bootstraps Coolify on a fresh VPS, wires domain/SSL, deploys with Nixpacks or Dockerfile, then runs the everyday pipeline: deploy, monitor, env changes, database + backups, rollback. |

## 🚀 Install

No build step, no dependencies — plain `SKILL.md` folders plus stdlib Python:

```bash
git clone https://github.com/takimdigital/expert-build-pack.git
cd expert-build-pack
```

| Harness | Copy the skill folders into |
| --- | --- |
| Claude Code | `~/.claude/skills/` |
| OpenAI Codex | `~/.codex/skills/` |
| Generic agents (AGENTS.md) | `~/.agents/skills/` |
| Hermes Agent | your Hermes profile `skills/` directory |

```bash
# example: Claude Code
cp -r skills/* ~/.claude/skills/
```

Then just talk to your agent:

```text
Build me an invoicing SaaS for freelancers.
Deploy it to my VPS with the domain billing.example.com.
Add dark mode and ship it.
Something broke in production — check the logs and roll back.
```

The agent reads the skills, drives the whole pipeline, and reports back with real deploy and health-check evidence — not instructions for you to follow.

## ✅ Proven on a live server (not "should work")

Deployed and validated end to end against a real Coolify instance:

- [x] **Deploy** — container image app · public Git repo · private repo via deploy key
- [x] **Change pipeline** — edit → commit → push → deploy → health smoke test
- [x] **Broken deploy caught** by the smoke test → **rollback** (full-tag) → `git revert` fix-forward
- [x] **Postgres** — provisioned via API → the app executes a real query over the internal network
- [x] **Backups** — schedule → dump → **restore drill** (`pg_restore` into a scratch database, verified)
- [x] **Build packs** — Nixpacks and Dockerfile · **ops** — logs, deployments, env vars, docker cleanup
- [x] **36 unit tests** green (standard library only)

Every bug these drills found is fixed and pinned in the reference runbooks — they carry live-verified API shapes, not guesses.

## 🔒 Principles

- **MIT only.** Every component and registry is license-checked (SPDX) before use. No pro tier, no paywalled components, nothing proprietary bundled.
- **Living pool, never hardcoded.** The component catalog is discovered fresh from the shadcn registry index — it grows as the ecosystem grows.
- **Coherent-random design.** Design tokens (color, type, radius, motion) are locked once per project, then applied to every component — random picks that still look designed.
- **Agent-first ops.** The agent manages the server over its API: deploy, env, backups, rollback, logs. You never SSH in.
- **Token-cheap by design.** Registry metadata is compacted before the model ever sees it.
- **Execution over advice.** The skills drive work in loops with verification gates, not advice essays.

## 📁 Repository layout

```text
skills/
├── expert-build-pack/     # idea → codebase (references, buildout engine, design assembly)
│   ├── references/        # expert playbooks, formats, lifecycle, eval, buildout
│   ├── scripts/           # registry sync + deterministic design picker
│   └── tests/             # stdlib unit tests
├── component-library/     # save / load reusable components
└── vps-ops/               # Coolify + Hostinger deploy & ops
    ├── references/        # bootstrap, domain/SSL, deploy, change pipeline, ops
    ├── scripts/           # Coolify API + Hostinger API clients
    └── tests/
```

## ❓ FAQ

**Does this only work with Claude Code?**
No. The skills are plain folders with a `SKILL.md`. Claude Code, OpenAI Codex, Cursor, Hermes Agent — anything that reads skill folders.

**What do I need for the deploy part?**
A VPS and a domain. `vps-ops` bootstraps Coolify on it and drives everything from there. Hostinger's API is baked in; any provider works over SSH.

**Will my design look AI-generated?**
That is what the Buildout Engine exists to avoid: it reuses already-excellent open-source components instead of generating slop, with tokens locked once so everything stays coherent.

**Is anything paid required?**
No. MIT-licensed components only; Coolify (Apache-2.0) runs on your own server.

## 📄 License

[MIT](LICENSE)
