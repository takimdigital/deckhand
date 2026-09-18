<p align="center">
  <img src="assets/logo.svg" width="108" alt="Expert Build Pack — AI agent skills for building and deploying SaaS">
</p>

<h1 align="center">Expert Build Pack</h1>

<p align="center">
  <b>From an idea to a live, production-ready SaaS — by chatting with your AI agent.<br>
  No agency, no DevOps, no hosting bills until it earns.</b>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Tests: 36 passing" src="https://img.shields.io/badge/tests-36%20passing-brightgreen.svg">
  <img alt="Version: 0.2.2" src="https://img.shields.io/badge/version-0.2.2-blueviolet.svg">
  <img alt="Works with Claude Code, Codex, Cursor, Hermes" src="https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Codex%20%7C%20Cursor%20%7C%20Hermes-black.svg">
</p>

---

Three small skill folders you drop into your AI coding agent (Claude Code, OpenAI Codex, Cursor, Hermes Agent…). From then on, your agent doesn't just *write code* — it **takes the whole thing live**: sets up a server (free tier, or one you already have), attaches your domain with HTTPS, deploys the app, puts a real database behind it, seeds first data, **smoke-tests everything, and hands you the URL**. If a change breaks something, it catches it and rolls back.

> You: *"Build me a quiz site for dog owners and put it online."*
> Agent: reads these skills, builds it, ships it, and replies with a live link + the evidence logs.

**Who it's for:** solo founders, indie hackers, and non-developers using AI agents — anyone who wants a real product on the internet without hiring anyone.

## 🚀 Zero → live, in three steps

1. **Say what you want.** "An invoicing tool for freelancers", "a quiz site", "my bakery's booking page."
2. **Your agent builds it.** From a living pool of vetted, MIT-licensed, human-designed components — with **one locked design system** (colour, type, radius, motion), so the result looks designed, not AI-generated.
3. **Your agent ships it.** Server, domain, HTTPS padlock, database, backups — proven with real deploy logs and health checks, never "should work".

After day one it's the everyday loop: *"add dark mode"* → change → deploy → verify. *"something's broken"* → read the logs → fix it or roll back.

## 💡 Why it feels too easy

- **It finishes the job.** Most AI tools stop at "here's the code". This pack is built for the last mile — the part where projects usually die (servers, DNS, SSL, databases, backups, rollbacks).
- **Start at $0 — for real.** Don't want to pay for hosting until the business earns? The built-in **free-preview track** goes live on a genuinely free Oracle Cloud server + a free domain behind Cloudflare + automatic HTTPS, with click-by-click guidance for every browser step that only you can do. When it makes money, the migration runbook moves you to a paid host in ~5–15 minutes of downtime (rollback included). Paying is an offer, never a gate.
- **Cheap to run.** It was engineered to burn **a fraction of the tokens** of "generate everything from scratch" workflows — [here's why](#-why-it-uses-so-few-tokens).
- **Evidence, not vibes.** Every step ends with a check the agent actually ran: HTTP 200s, container health, database queries, restore drills.
- **Yours, forever.** MIT-only and self-hosted on your own server. No subscription, no lock-in, nothing proprietary bundled.

## 🪙 Why it uses so few tokens

Most AI workflows burn tokens re-inventing things. This pack is engineered the other way:

- **Procedures live in compact playbooks, not in the model's head.** The agent *reads* a deployment runbook once — with real API shapes and known pitfalls — instead of re-deriving the whole process from scratch. Re-deriving is what costs a fortune.
- **Scripts do the labour.** Registry sync, design-token picking, deploy API calls, health checks — deterministic Python scripts handle the boring parts, so you're not paying tokens for boilerplate.
- **Assemble, don't generate.** Design and code come from a living pool of already-excellent MIT components, not raw model output. Skipping "generate a UI from nothing" removes the single most expensive part of an AI build.
- **Gates, not retry spirals.** Execution loops with verification: run → check → move on, or stop and fix the real error. No long "advice essays", no blind retrying.

## 🗣️ Things you can just say

```text
Build me an invoicing SaaS for freelancers.
Deploy it to my VPS with the domain billing.example.com.
Deploy it to the free Oracle server first — I'll pay for hosting once it makes money.
Add dark mode and ship it.
Something broke in production — check the logs and roll back.
```

The agent drives the whole pipeline and reports back with deploy and health-check evidence — never a to-do list for you.

## 🗺️ The two tracks, both shipped

**Track P — your own VPS + domain (paid).** Bootstrap any Ubuntu VPS (SSH keys, firewall, Coolify, hardened dashboard on a tunnel) → DNS + SSL via Cloudflare → deploy (Nixpacks or Dockerfile; public repos and private repos via deploy keys) → first-run data (migrations, seed, production owner) → ongoing pipeline: change → push → deploy → smoke test, rollback, env vars, logs, backups + restore drills. Proven end-to-end on a live deployment.

**Track F — go live at $0 first (free preview).** The full chain, guided click-by-click where a browser is unavoidable and agent-driven everywhere else: **[free `.pp.ua` domain] → [Cloudflare DNS-only] → [Oracle Cloud Always Free (Arm) VPS] → [Coolify + Let's Encrypt]** — shipped with an `oci-cloud-init.yaml` first-boot asset, an "out of host capacity" ladder, a signup-failure ladder with vetted alternatives, and an honest reclamation-risk note. Researched and primary-source-verified; first live run pending. The migration runbook moves you to a paid host when you're ready.

**Choosing a host? No fresh research needed.** The provider price sheet carries current prices + sizing rules for Oracle, Contabo, Hostinger and Hetzner (USD/CAD, monthly and prepaid terms). Already own a domain? Ref 21 points it at Cloudflare too — DNS/SSL setup is identical at any registrar.

## ✅ Proven on a live server (not "should work")

Deployed and validated end to end against a real Coolify instance:

- [x] **Deploy** — container image app · public Git repo · private repo via deploy key
- [x] **Change pipeline** — edit → commit → push → deploy → health smoke test
- [x] **Broken deploy caught** by the smoke test → **rollback** (full-tag) → `git revert` fix-forward
- [x] **Postgres** — provisioned via API → the app executes a real query over the internal network
- [x] **Backups** — schedule → dump → **restore drill** (`pg_restore` into a scratch database, verified)
- [x] **Build packs** — Nixpacks and Dockerfile · **ops** — logs, deployments, env vars, docker cleanup
- [x] **36 unit tests** green (standard library only)
- [x] **Paid track validated live** — a real Next.js + Postgres SaaS deployed end-to-end on a rented VPS: Coolify → Cloudflare DNS-only → Let's Encrypt, with migrations, seed data and a production-owner flow — every error it surfaced is now folded back into the runbooks.

## ⚡ The skills

| Skill | What it does |
| --- | --- |
| [`expert-build-pack`](skills/expert-build-pack) | **Idea → codebase.** Expert references, execution-first build loops, verified MIT boilerplates, coherent-random design assembly from the live shadcn registry pool (MIT-only), design tokens locked once and applied everywhere. |
| [`component-library`](skills/component-library) | **Build → reuse.** Save any component you build; the next project starts from what you already made. |
| [`vps-ops`](skills/vps-ops) | **Codebase → live business.** Two tracks: **paid** (your VPS + domain) or **free preview** ($0 on Oracle Cloud Always Free + a free `.pp.ua` domain). Bootstraps Coolify, wires domain/SSL, deploys with Nixpacks or Dockerfile, then runs the everyday pipeline: deploy, monitor, env changes, database + backups, rollback — plus a migration runbook to move from the free preview to a paid host. |

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

Then just start a conversation — the examples above work verbatim.

## 📖 Plain-words glossary (no jargon required)

- **Agent** — your AI assistant (Claude Code, Codex, Cursor, Hermes…), the thing you chat with.
- **VPS** — a small rented computer in a data centre that runs your product. ~$0–6/month depending on power.
- **Domain / DNS** — your web address (like `mybakery.com`) and the system that points it at your server.
- **HTTPS / SSL** — the padlock in the browser. The pack gets you one automatically, free.
- **Deploy** — putting your app onto that rented computer so the world can reach it.
- **Rollback** — instantly returning to the last version that worked when something breaks.
- **Coolify** — the free, open-source control panel the agent installs to run your apps, databases and backups. Think "self-hosted Vercel".
- **Token** — the unit AI models are paid in. Fewer tokens = cheaper usage.
- **SKILL.md** — how agent skills are packaged: plain-text instructions an agent reads before doing a task.

## 🔒 Principles

- **MIT only.** Every component and registry is license-checked (SPDX) before use. No pro tier, no paywalled components, nothing proprietary bundled.
- **Living pool, never hardcoded.** The component catalog is discovered fresh from the shadcn registry index — it grows as the ecosystem grows.
- **Coherent-random design.** Design tokens (colour, type, radius, motion) are locked once per project, then applied to every component — random picks that still look designed.
- **Agent-first ops.** The agent manages the server over its API: deploy, env, backups, rollback, logs. You never SSH in.
- **Token-cheap by design.** Registry metadata is compacted before the model ever sees it; scripts do the deterministic work.
- **Execution over advice.** The skills drive work in loops with verification gates, not advice essays.

## 📁 Repository layout

```text
skills/
├── expert-build-pack/     # idea → codebase (references, buildout engine, design assembly)
│   ├── references/        # expert playbooks, formats, lifecycle, eval, buildout
│   ├── scripts/           # registry sync + deterministic design picker
│   └── tests/             # stdlib unit tests
├── component-library/     # save / load reusable components
└── vps-ops/               # Coolify deploy & ops — paid VPS or free preview (Oracle + .pp.ua)
    ├── references/        # bootstrap, domain/SSL, free preview, deploy, change pipeline, ops, migration
    ├── assets/            # oci-cloud-init.yaml (Oracle first-boot)
    ├── scripts/           # Coolify API + Hostinger API clients
    └── tests/
```

## ❓ FAQ

**Do I need to know how to code?**
No. You chat; the agent works. You'll answer at most a couple of simple questions (like "free preview first, or your own server?") and do the few things only you can do — like creating an account, or clicking "connect domain" when a browser is unavoidable — each explained click by click.

**Does this only work with Claude Code?**
No. The skills are plain folders with a `SKILL.md`. Claude Code, OpenAI Codex, Cursor, Hermes Agent — anything that reads skill folders.

**What does it actually cost?**
The pack is free and yours forever. Hosting: $0 to start on the free-preview track; later, a small VPS is typically ~$5–6/month (the price sheet compares providers for you).

**What do I need for the deploy part?**
A VPS and a domain — or nothing but an Oracle Cloud account if you start on the free-preview track. `vps-ops` bootstraps Coolify on the server and drives everything from there. Hostinger's API is baked in; any provider works over SSH.

**Will my design look AI-generated?**
That is what the Buildout Engine exists to avoid: it reuses already-excellent open-source components instead of generating slop, with tokens locked once so everything stays coherent.

**Is anything paid required?**
No. MIT-licensed components only; Coolify (Apache-2.0) runs on your own server — including the entire $0 preview stack.

**Is my project locked into this system?**
No. It's your code on your server, built from open-source parts. Stop using the pack any time — everything keeps running.

## 📄 License

[MIT](LICENSE)
