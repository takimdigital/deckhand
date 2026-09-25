<p align="center">
  <img src="assets/logo.svg" width="108" alt="Deckhand — an agent skill that turns a $5 server and a $10 domain into a live business">
</p>

<h1 align="center">Deckhand</h1>

<p align="center">
  <b>Bring a $5 server and a $10 domain (or $0).<br>
  Your agent turns them into a live business. You go find the clients.</b>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <a href="https://github.com/takimdigital/deckhand-skill/actions/workflows/ci.yml"><img alt="CI status" src="https://img.shields.io/github/actions/workflow/status/takimdigital/deckhand-skill/ci.yml?branch=main&label=CI"></a>
  <img alt="Version: 2.0.0" src="https://img.shields.io/badge/version-2.0.0-blueviolet.svg">
  <img alt="Works with Claude Code, Codex, Cursor, Hermes, OpenCode, Gemini CLI" src="https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Codex%20%7C%20Cursor%20%7C%20Hermes-black.svg">
</p>

---

Deckhand is **one skill folder** you drop into your AI coding agent (Claude Code, Codex, Cursor, Hermes,
OpenCode, Gemini CLI…). It takes your agent from *"a bakery that delivers sourdough in Lyon"* to a site
that is **live on your own server**. It researches your market, plans every page and every click, builds
from licensed human-made designs, puts your brand on it, lets you **click any section and swap it live**,
verifies everything, deploys it and keeps it running.

The agent doesn't improvise the plumbing. A control plane called **`dh`** holds the process: nine phases,
hard gates, and a script for every deterministic step. The model writes words (your copy, research, plans)
and app logic. Scripts do the rest, and every "done" is a command's output, never a claim.

> **You:** *"Build my bakery's ordering site and put it online."*
> **Agent:** runs `dh next`, asks you three things, shows you a plan, shows you the site running locally,
> lets you swap sections until you love it, ships it, and hands you the URL, the logins and the evidence.

## 🧭 How a run goes

```text
define → research → plan ─G1→ build ─G2→ brand → try-on ─G3→ review ─G4→ deploy → operate
```

| phase | what happens | proof it's done |
|---|---|---|
| **define** | your business, audience, languages, and how you want to work: **phased** (it stops for your OK at 4 gates, recommended) or **auto** (it only stops for real decisions) | the brief is complete |
| **research** | round 1: the business, your top 3 competitors (what they do well, where they're weak), your audience, conversion plays, day-one features | 3 competitors with URLs, strengths and gaps |
| **plan** | round 2: every page, every button and every form, wired as a graph. **No dead ends**: a lint refuses a plan with an orphan page, a link to nowhere, a form without success and error states, or a login-only page with no way to log in. Split into work packages for parallel agents that share one blackboard | `dh plan lint` = 0 errors → **G1: you approve the plan** |
| **build** | four paths: a **vetted open-source base** (MIT/Apache, measured through the GitHub API), **your own** saved base, **your existing project**, or **from scratch** (pages composed from licensed blocks carrying your copy). Then it starts the app for you | the app answers locally → **G2: you tested it** |
| **brand** | your name, colours, icon and metadata in, the template's out. A leak check then proves it | 0 blocking findings (template names, lorem, demo companies, fake logos, demo copy) |
| **try-on** | click any section of your running site and flip through designs **in your colours, with your text** (below) | no open session → **G3: you approve the design** |
| **review** | typecheck, build, secrets, `.env` hygiene, every route answers, honesty, no dev tooling in the build, a11y basics, dependency audit | `dh verify` all blocking rows green → **G4: go live** |
| **deploy** | Coolify on your VPS (or the $0 track), wait for *this* commit, smoke-test, write `HANDOFF.md` (what you own, where the logins are, how to get in; never the secrets themselves) | live URL + smoke OK |
| **operate** | change → verify → ship loop, rollback, **business bots** (uptime watchdog, broken-link audit, backup proof, weekly KPIs, lead digest, payment-failed and booking reminders…), and turning the finished site into **your own reusable base** | continuous |

Changed your mind? `dh reopen plan` and it continues from there.

## 🪄 Try-on: click a section, swap it, keep your words

Most "swap a component" tools paste a demo block with someone else's colours and someone else's copy
("Build faster with Acme"). Deckhand's try-on is built on the opposite rule: **a variant must look like
your site and say what your site says**.

1. `tryon setup` → `tryon serve` → open the printed URL. A **Try-on** button sits on your real, running site.
2. Click anything: the hero, the pricing table, a button. Say what it is (it guesses).
3. Deckhand writes 4 licensed variants into your code **once**. Then ← → flips between them instantly, with
   **zero AI calls per click**.
4. Every variant:
   - **wears your theme.** Palette classes become your site's colour tokens, and missing tokens are derived from your own colours.
   - **carries your content.** Headings (including your accent words), text, prices, buttons *and where they link*, images, list items card by card, FAQ questions, footer menus from your plan, your socials.
   - **is honest about the rest.** Demo stock photos become a neutral placeholder. Fake "trusted by" logo rows, extra demo buttons and newsletter forms that post nowhere are hidden. Any leftover demo sentence is underlined, and the gate won't let it ship.
   - **shows a fit badge** ("your content 4/4"). Designs that would throw away most of your words aren't offered.
5. **Keep** bakes your text in, deletes unused files, and records the MIT licence in
   `THIRD_PARTY_NOTICES.md`. **Discard** restores your file byte for byte. **Save** puts the design in your
   personal library, and it ranks first next time.

The catalog holds **738 MIT-licensed items**: 300 Tailark OSS blocks, 197 shadcn/ui, 113 Smooth UI,
57 Magic UI, 36 basecn and 35 Kokonut UI. They are matched to your stack (Radix vs Base UI, Tailwind 4,
your aliases), and licence-unclear sources are refused, never scraped. No browser in your harness? The same
engine runs headless: `tryon try / show / keep`.

## 💡 Why it costs so little

- **The door costs a lunch.** A real online business = **~$5/month for a server + ~$10/year for a domain**.
  What stops people isn't money. It's servers, DNS, SSL, deploys and databases. That pile is what Deckhand absorbs.
- **Start at $0, for real.** The free track: an Oracle Cloud Always Free server, a free domain (or just
  the Coolify-provided URL), automatic HTTPS. When the business earns, a runbook moves you to a paid host.
  Paying is an offer, never a gate.
- **Token-cheap by construction.** `dh next` hands the agent *one* instruction and *one* reference file
  per step. Data is queried, not read. Composition, swapping, rebranding, linting, verifying and deploying
  are scripts. Try-on runs with no model in the loop.
- **Failures are paid once.** Risky commands run through `dh run`. A known error prints its fix
  immediately, and every new failure becomes a lesson that's promoted into a pre-flight check, so the
  same mistake doesn't come back.
- **Yours, forever.** MIT, self-hosted, your code, your data, your server. Nothing rented that a script
  didn't flag first (`dh swap check` finds Clerk/Neon/Resend/Sentry… and proves them replaced).

## ☕ The uncomfortable math

**"I can't afford to start a business"**: you, holding a $9 *Venti Macha Luxa Choco-Caca Laka Frappé*.

| Your coffee | What it covers |
| --- | --- |
| one $5 drink | one month of a real server |
| one $10 drink | a real domain, for a whole year |
| three drinks | your entire business, live and running, for a month |

**Broke? Keep the coffee.** The $0 track is real: free server, free domain or URL, HTTPS, in production.

## 🚀 Install

Needs Python 3.9+ (standard library only) and Node 18+ (for try-on and compose). There's nothing else to install.

```bash
git clone https://github.com/takimdigital/deckhand-skill.git
cd deckhand-skill
./install.sh            # every harness it finds: Claude Code, Codex, Cursor, Hermes, OpenCode, Gemini CLI, ~/.agents
./install.sh --link     # or symlink, so `git pull` updates every harness at once
```

Windows: `powershell -ExecutionPolicy Bypass -File install.ps1` (use `py` where the docs say `python3`).
The installer also puts a `dh` command in `~/.deckhand/bin`. Harness that doesn't load skill folders? Point
it at [`AGENTS.md`](AGENTS.md).

Then just talk to your agent.

## 🗣️ Things you can say

```text
Build me a booking site for my barbershop. Phased — show me the plan first.
Start from my own saved base "levain-v1" and make it a pastry shop.
Take my existing repo and redesign the landing page — let me try sections on.
Deploy it on the free Oracle server first; I'll pay once it makes money.
Add a weekly KPI email and a bot that checks the server is up.
Something broke in production — check the logs and roll back.
Turn this site into a reusable base for my next client.
```

## ✅ What is proven (and what isn't yet)

Verified in this release, by running it:

- [x] **Try-on in a real browser** (Chromium, Next.js 16.3.6, Turbopack): pick the hero → variants carry
  the owner's copy 4/4 (including an accent-coloured word) → flip → keep (baked, pruned, licence recorded)
  → save to library; a CTA try → discard restores the file **byte-exact**; no console errors.
- [x] **From scratch, composed**: 6 sections (hero, features, pricing, FAQ, CTA, footer) from live Tailark
  blocks in ~6 s, **34/34 of the owner's words placed**, footer menu built from the plan, typecheck clean;
  the honesty gate blocked the one demo sentence left, and passed once it was rewritten.
- [x] **Production build** after keep: 0 dev stamps in the output (`prod-clean` row).
- [x] **Suites** (offline, in CI on every push): 26 try-on (node) · 19 control plane (unittest) ·
  40 ops clients (pytest).

Carried over from v1, where they were proven live on a real Coolify server and ported unchanged with their
tests: deploy (image, public repo, private repo via deploy key), smoke test → rollback, Postgres via API,
backups + restore drill, offsite backups (B2/Tigris).

Not yet proven live in v2: `dh deploy ship` end to end against a real server (it drives the same client
as above), the first live run of the $0 Oracle track, and Windows CI (it runs on every push but doesn't
block yet).

## 🔒 Principles

- **Your facts are never invented.** Prices, reviews, addresses, client logos: if the agent doesn't know,
  it goes in `PENDING.md` and gets asked once, batched, with click-by-click steps.
- **Licences are enforced.** Bases and components are MIT/Apache only. `NOTICE` and
  `THIRD_PARTY_NOTICES.md` are never removed. AGPL and "free with attribution to a paid tier" sources
  stay refused.
- **Evidence over assertion.** A check that cannot fail isn't a check; fixes go into scripts and tests,
  not prose.
- **Dev tooling never ships.** Try-on stamps are dev-only and verified absent from production builds.
- **Secrets stay secret.** `~/.deckhand/vault.env` (0600) or your platform's env store. Never in chat,
  commits, logs or the handoff.

## 📁 Repository layout

```text
skills/deckhand/
├── SKILL.md          # the operating spec the agent reads (state machine, invariants, command surface)
├── dh.py + dhlib/    # control plane (stdlib Python): phases, gates, plan lint, pool, build, rebrand,
│                     #   verify, deploy, ops bots, lessons, harvest, handoff
├── tryon/            # try-on + compose engine (zero-dependency Node; vendored @babel/parser, MIT)
├── ops/              # Coolify / Hostinger / backup clients + tests (from v1, live-proven)
├── references/       # one short file per phase (00-define … 80-operate) + ops runbooks
├── data/             # component catalog, base pool, bots, seed lessons, registries (+ refused list)
├── templates/        # brief, research, sitemap, work package, scaffold, bots, OPS handoff
└── tests/
install.sh · install.ps1 · AGENTS.md · CHANGELOG.md
```

## ❓ FAQ

**Do I need to code?** No. You answer a few questions, approve four checkpoints (or choose auto), and do
the few things only you can do, like creating an account. Each of those comes with exact click paths.

**Will it look AI-generated?** No. Sections come from human-designed, MIT-licensed blocks, restyled to your
colours and filled with your words. You pick them by clicking through them on your own site.

**I already have a site.** Use the `existing` path: Deckhand adopts it, and try-on works on it directly.

**Is anything paid required?** No. Open-source bases and components, Coolify (Apache-2.0) on your own
server, and a real $0 track.

**Am I locked in?** No. It's your code on your server. Stop using Deckhand any time and everything keeps running.

**Coming from v1?** The five v1 skills (buildout, vps-ops, component-library, session-autopsy,
deckhand-profile) are now one: `skills/deckhand`. See [CHANGELOG.md](CHANGELOG.md) for why try-on didn't
work in v1 and what replaced it.

## ☕ Support Deckhand

Free forever. MIT, no tiers, no paywalls. If it saved you time or made you money:
**[☕ Buy me a coffee →](https://buymeacoffee.com/takimdigital)**, or ⭐ star the repo.

## 📄 License

[MIT](LICENSE)
