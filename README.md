<p align="center">
  <img src="assets/logo.svg" width="108" alt="Deckhand — agent skills that turn a $5 server and a $10 domain into a live business">
</p>

<h1 align="center">Deckhand</h1>

<p align="center">
  <b>Bring a $5 server and a $10 domain.<br>
  Your agent turns them into a live business — you go find the clients.</b>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <a href="https://github.com/takimdigital/deckhand-skill/actions/workflows/ci.yml"><img alt="CI status" src="https://img.shields.io/github/actions/workflow/status/takimdigital/deckhand-skill/ci.yml?branch=main&label=CI"></a>
  <img alt="Version: 0.19.0" src="https://img.shields.io/badge/version-0.19.0-blueviolet.svg">
  <img alt="Works with Claude Code, Codex, Cursor, Hermes" src="https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Codex%20%7C%20Cursor%20%7C%20Hermes-black.svg">
</p>

---

Five small skill folders you drop into your AI coding agent (Claude Code, OpenAI Codex, Cursor, Hermes Agent…). From then on, your agent doesn't just *write code* — it **takes the whole thing live**: sets up a server (a $5 one, or the free tier), attaches your domain with HTTPS, deploys the app, puts a real database behind it, seeds first data, **smoke-tests everything, and hands you the URL**. If a change breaks something, it catches it and rolls back.

Think of it as a deckhand: **you keep the helm, it works the ropes.** Your job is the business — finding clients.

> You: *"Build me a quiz site for dog owners and put it online."*
> Agent: reads these skills, builds it, ships it, and replies with a live link + the evidence logs.

**Who it's for:** solo founders, indie hackers, and non-developers using AI agents — anyone who ever froze at the words "server", "DNS" or "deploy". Nobody should miss out on a business because the setup felt overwhelming.

## 🚀 Zero → live, in three steps

1. **Say what you want.** "An invoicing tool for freelancers", "a quiz site", "my bakery's booking page."
2. **Your agent builds it.** It measures a pool of real, open-source, MIT/Apache-licensed applications through GitHub's API, ranks them against what you asked for, clones the closest match and swaps the template's paid services for self-hosted ones. Code human maintainers wrote on purpose — not a model improvising.
3. **Your agent ships it.** Server, domain, HTTPS padlock, database, backups — proven with real deploy logs and health checks, never "should work".

After day one it's the everyday loop: *"add dark mode"* → change → deploy → verify. *"something's broken"* → read the logs → fix it or roll back.

## 💡 Why it feels too easy

- **The whole door costs about the price of a lunch.** A real online business = **~$5/month for a server + ~$10/year for a domain**. That's it. What stops most people isn't money — it's the pile of unfamiliar tech (servers, DNS, SSL, deploys, databases). That pile is exactly what Deckhand absorbs: you bring two things — a server and a domain — and go find clients.
- **It finishes the job.** Most AI tools stop at "here's the code". Deckhand is built for the last mile — the part where projects usually die (servers, DNS, SSL, databases, backups, rollbacks).
- **Start at $0 — for real.** Don't want to pay anything until the business earns? The built-in **free-preview track** goes live on a genuinely free Oracle Cloud server + a free domain behind Cloudflare + automatic HTTPS, with click-by-click guidance for every browser step that only you can do. When it makes money, the migration runbook moves you to a paid host in ~5–15 minutes of downtime (rollback included). Paying is an offer, never a gate.
- **Cheap to run.** It was engineered to burn **a fraction of the tokens** of "generate everything from scratch" workflows — [here's why](#-why-it-uses-so-few-tokens).
- **Evidence, not vibes.** Every step ends with a check the agent actually ran: HTTP 200s, container health, database queries, restore drills.
- **Yours, forever.** MIT-only and self-hosted on your own server. No subscription, no lock-in, nothing proprietary bundled.

## ☕ The uncomfortable math

**"I can't afford to start a business"** — you, holding a $9 *Venti Macha Luxa Choco-Caca Laka Frappé*.

Meanwhile, the actual cost:

| Your coffee | What it covers |
| --- | --- |
| one $5 drink | one month of a real server |
| one $10 drink | a real domain, for a whole year |
| three drinks | your entire business — live and running, for a month |

The drinks have names longer than your business plan, and they still cost more than the infrastructure that could be hosting it. **You're not broke — you've been paying for the wrong thing.**

Bring the $5 server and the $10 domain. Deckhand does the rest while you go find the client.

**Broke? Good news — keep the coffee.** There is a real $0 track: a free server + a free domain + HTTPS, live in production. Prove the business on zero first — paying is an offer, never a gate.

## ☕ Support Deckhand

The pack is free, forever — MIT, no tiers, no paywalls, no upsell. If it saved you time or made you money, you can fund the tokens, the servers and the next bricks:

**[☕ Buy me a coffee →](https://buymeacoffee.com/takimdigital)** · or just ⭐ star the repo — both count.

## 🪙 Why it uses so few tokens

Most AI workflows burn tokens re-inventing things. Deckhand is engineered the other way:

- **Procedures live in compact playbooks, not in the model's head.** The agent *reads* a deployment runbook once — with real API shapes and known pitfalls — instead of re-deriving the whole process from scratch. Re-deriving is what costs a fortune.
- **Scripts do the labour.** Template scoring, cloning, swap checks, deploy API calls, health checks — deterministic Python scripts handle the boring parts, so you're not paying tokens for boilerplate.
- **Clone, don't generate.** The app comes from an already-working open-source template with a licence and a commit history, not from raw model output. Skipping "generate a whole product from nothing" removes the single most expensive part of an AI build.
- **Gates, not retry spirals.** Execution loops with verification: run → check → move on, or stop and fix the real error. No long "advice essays", no blind retrying.
- **Failures are paid for once.** `session-autopsy` turns any red run into a pre-flight check the next agent can't miss — the pack gets sharper with use, never noisier.
- **You answer once, ever.** `deckhand-profile` keeps your accounts, providers and defaults in one portable file — every agent reads it first instead of interrogating you again.

## 🗣️ Things you can just say

```text
Create my deckhand profile.
Build me an invoicing SaaS for freelancers.
Deploy it to my VPS with the domain billing.example.com.
Deploy it to the free Oracle server first — I'll pay for hosting once it makes money.
Add login emails — signup verification and password reset.
Add dark mode and ship it.
Something broke in production — check the logs and roll back.
```

The agent drives the whole pipeline and reports back with deploy and health-check evidence — never a to-do list for you.

## 🗺️ The two tracks, both shipped

**Track P — your own VPS + domain (paid).** Bootstrap any Ubuntu VPS (SSH keys, firewall, Coolify, hardened dashboard on a tunnel) → DNS + SSL via Cloudflare → deploy (Nixpacks or Dockerfile; public repos and private repos via deploy keys) → first-run data (migrations, seed, production owner) → ongoing pipeline: change → push → deploy → smoke test, rollback, env vars, logs, backups + restore drills. Every deploy also writes the app's **`OPS.md`** — a cold-start handoff (access, secret locations, everyday commands) so any future session starts with zero re-discovery. Proven end-to-end on a live deployment.

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
- [x] **Unit suites green** — every skill's scripts are covered by pytest (standard library only), and CI runs the whole suite on every push
- [x] **Template factory** — the registry, the clone, the swap gate and the leak check are covered by offline tests and exercised end-to-end on a real MIT template: cloned, installed, built and served with a build-id freshness proof, with both gates red where they must be — leftover vendor references in the unswapped clone and the template's own name on the served page — because a gate that can't fail isn't a gate.
- [x] **Paid track validated live** — a real Next.js + Postgres SaaS deployed end-to-end on a rented VPS: Coolify → Cloudflare DNS-only → Let's Encrypt, with migrations, seed data and a production-owner flow — every error it surfaced is now folded back into the runbooks.

## ⚡ The skills

| Skill | What it does |
| --- | --- |
| [`buildout`](skills/buildout) | **Idea → live business, from a vetted template.** The assistant is a Matchmaker + DevOps Automator, not an architect: ≤10 questions → a registry of MIT/Apache full-app templates **measured through the GitHub API** (license, stack, vendor deps, risk, boot scorecard) ranks the pool deterministically → the chosen match is cloned into a fresh project folder with its own git history → proprietary services (Clerk, Neon, Resend, Sentry, S3, Plausible…) are swapped for open-source targets and **proved gone by `swap_check`** → the owner's brand replaces the template's (template-leak check included) → a 6-row verify tail → Coolify. Cloning and booting third-party code is consent-gated; intake never clones. No code generation, no component assembly, no design systems. |
| [`component-library`](skills/component-library) | **Build → reuse.** Save any component you build; the next project starts from what you already made. |
| [`vps-ops`](skills/vps-ops) | **Codebase → live business.** Two tracks: **paid** (your VPS + domain) or **free preview** ($0 on Oracle Cloud Always Free + a free `.pp.ua` domain). Bootstraps Coolify, wires domain/SSL, deploys with Nixpacks or Dockerfile, then runs the everyday pipeline: deploy, monitor, env changes, database + backups, rollback — plus a migration runbook to move from the free preview to a paid host. And **login email that actually arrives**: a free multi-provider chain (Resend → Mailgun → Brevo) behind a drop-in failover router + deliverability DNS, with a modular MCP catalog for DNS/registrar/email. Backups are **offsite by default** — dual cloud targets (Backblaze B2 + Tigris, both **card-free**; R2 optional), 3-copy retention, verified restore drills (all live-proven), an optional home copy with a scheduled watchdog — and apps with uploads get RustFS S3 storage, backed up the same way. |
| [`session-autopsy`](skills/session-autopsy) | **Failure → fix.** When a run goes red, it dissects the session, finds the instruction that allowed the wrong path, and rewrites it — on a strength ladder (eliminate → pre-flight → reorder → gate → pitfall). Pitfalls are counted as debt, not solutions. |
| [`deckhand-profile`](skills/deckhand-profile) | **You, once.** One portable file (`~/.deckhand/profile.md`) with your accounts, providers and defaults — every agent reads it first and never re-asks. Copy it to any harness or machine. |

## 🚀 Install

No build step, no dependencies — plain `SKILL.md` folders plus stdlib Python:

```bash
git clone https://github.com/takimdigital/deckhand-skill.git
cd deckhand-skill
```

| Harness | Copy the skill folders into |
| --- | --- |
| Claude Code | `~/.claude/skills/` |
| OpenAI Codex | `~/.agents/skills/` (legacy builds: `~/.codex/skills/`) |
| Cursor | `~/.cursor/skills/` (project-level: `.cursor/skills/`) |
| Generic agents (AGENTS.md) | `~/.agents/skills/` |
| Hermes Agent | your Hermes skills dir — `%LOCALAPPDATA%\hermes\skills\` (Windows) or `~/.local/share/hermes/skills/` (Linux) |

```bash
# example: Claude Code
mkdir -p ~/.claude/skills
cp -r skills/* ~/.claude/skills/
```

Downloaded `deckhand.zip` instead? Unzip it anywhere, then copy the folders inside the archive's `skills/` into your harness directory (same folders the clone gives you). Don't unzip straight *into* a skills directory — you'd end up with `skills/skills/`.

Then just start a conversation — the examples above work verbatim.

## 📖 Plain-words glossary (no jargon required)

- **Agent** — your AI assistant (Claude Code, Codex, Cursor, Hermes…), the thing you chat with.
- **VPS** — a small rented computer in a data centre that runs your product. ~$5/month, or $0 on the free track.
- **Domain / DNS** — your web address (like `mybakery.com`) and the system that points it at your server. ~$10/year.
- **HTTPS / SSL** — the padlock in the browser. Deckhand gets you one automatically, free.
- **Deploy** — putting your app onto that rented computer so the world can reach it.
- **Rollback** — instantly returning to the last version that worked when something breaks.
- **Coolify** — the free, open-source control panel the agent installs to run your apps, databases and backups. Think "self-hosted Vercel".
- **Token** — the unit AI models are paid in. Fewer tokens = cheaper usage.
- **SKILL.md** — how agent skills are packaged: plain-text instructions an agent reads before doing a task.

## 🔒 Principles

- **Open licences only.** Every template in the pool is licence-checked (MIT/Apache, SPDX) before it can be cloned. No pro tier, no paywalled parts, nothing proprietary bundled.
- **Measured, never asserted.** Every pool row is measured from the live repository through the GitHub API — licence, stack, vendor dependencies, risk flags, boot scorecard. Nothing is taken from memory.
- **The swap gate.** Templates lean on paid services (Clerk, Neon, Resend, Sentry, S3…). Each is replaced with a self-hosted equivalent and **proved gone** by a check that fails with file-and-line evidence — so the project is really yours, not rented.
- **Agent-first ops.** The agent manages the server over its API: deploy, env, backups, rollback, logs. You never SSH in.
- **Token-cheap by design.** Registry rows are compact facts, not documents; scripts do the deterministic work.
- **Execution over advice.** The skills drive work in loops with verification gates, not advice essays.

## 📁 Repository layout

```text
assets/                    # logo + social preview (render-social-preview.ps1)
skills/
├── buildout/              # idea → live business (Template Factory: match → clone → swap → rebrand)
│   ├── references/        # factory/ (intake · match · clone · swap · rebrand · verify) + playbooks/formats/lifecycle/jargon
│   ├── data/              # templates.seed.json · templates.db (the registry) · templates.json
│   ├── scripts/           # registry, remote intake (GitHub API), clone, swap check
│   ├── templates/         # qa/ — probe, frame, cdp.mjs, form-drive.js
│   └── tests/             # stdlib test suite
├── component-library/     # save / load reusable components
├── vps-ops/               # Coolify deploy & ops — paid VPS or free preview (Oracle + .pp.ua)
│   ├── references/        # bootstrap, domain/SSL, free preview, deploy, change pipeline, ops, migration, auth+email, MCP catalog
│   ├── assets/            # oci-cloud-init.yaml (Oracle first-boot)
│   ├── templates/         # OPS handoff + mail-router/ (failover email sender) + vps-backup/ (backup templates)
│   ├── scripts/           # Coolify API + Hostinger API clients
│   └── tests/
├── session-autopsy/       # failure → instruction fix (refs 10/20/30 + report template)
└── deckhand-profile/      # the portable user profile (format + template)
```

## ❓ FAQ

**Do I need to know how to code?**
No. You chat; the agent works. You'll answer at most a couple of simple questions (like "free preview first, or your own server?") and do the few things only you can do — like creating an account, or clicking "connect domain" when a browser is unavoidable — each explained click by click.

**Does this only work with Claude Code?**
No. The skills are plain folders with a `SKILL.md`. Claude Code, OpenAI Codex, Cursor, Hermes Agent — anything that reads skill folders.

**How much does it really cost to start?**
~$5/month for a server + ~$10/year for a domain — or literally $0 on the free-preview track. The pack itself is free, forever. For comparison: less than most streaming subscriptions you already pay. Deckhand exists to remove the *overwhelm*, not the cost.

**What do I need for the deploy part?**
A VPS and a domain — or nothing but an Oracle Cloud account if you start on the free-preview track. `vps-ops` bootstraps Coolify on the server and drives everything from there. Hostinger's API is baked in; any provider works over SSH.

**Will my design look AI-generated?**
You start from a real app that a human designed and thousands of people starred — not from a model improvising a UI. Your brand replaces the template's, and a leak check refuses to ship while any trace of the original is still on the page.

**Is anything paid required?**
No. MIT/Apache-licensed templates and open-source replacements only; Coolify (Apache-2.0) runs on your own server — including the entire $0 preview stack.

**Is my project locked into this system?**
No. It's your code on your server, built from open-source parts. Stop using the pack any time — everything keeps running.

## 📄 License

[MIT](LICENSE)
