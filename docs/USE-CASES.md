# Use cases — copy a sentence, get a result

Every case below has the same shape:

- **Say:** the exact sentence to paste to your AI agent.
- **What happens:** what you'll see.
- **You do:** the only things a human has to do (usually nothing, or one click).
- **Under the hood:** the commands, for the technical readers. Skip it if you're not one.

Install once first ([README](../README.md#-start-in-2-minutes)). In any case, the agent starts with `dh next`,
and it stops at the ✋ checkpoints until you say go.

| # | I want to… | jump |
|---|---|---|
| 1 | turn an idea into a live website, with zero tech | [→](#1-idea--live-website-zero-tech) |
| 2 | use a template I found on GitHub | [→](#2-a-template-i-found-on-github) |
| 3 | make my existing site look premium | [→](#3-make-my-existing-site-look-premium) |
| 4 | get a design that no library has | [→](#4-a-design-no-library-has) |
| 5 | launch for $0, even without a domain | [→](#5-launch-for-0-even-without-a-domain) |
| 6 | go live on my own domain | [→](#6-go-live-on-my-own-domain) |
| 7 | keep it running while I sleep | [→](#7-keep-it-running-while-i-sleep) |
| 8 | stop the agent repeating the same mistake | [→](#8-stop-the-agent-repeating-the-same-mistake) |
| 9 | reuse this site for my next client | [→](#9-reuse-this-site-for-my-next-client) |
| 10 | work on it as a developer | [→](#10-for-developers) |

---

## 1. Idea → live website, zero tech

**Say:**
> Build a website for my business: *[what you sell, where, to whom]*. Phased mode: show me the plan first.

**What happens:**
1. A few short questions in one batch: languages, audience, whether you already have a logo or colours.
2. A research summary: your top 3 competitors, what they do well, where they're weak.
3. **✋ The plan:** every page and every button, and where each one goes. Nothing leads nowhere.
4. **✋ Your site running on your computer:** a link you click around.
5. Your name and colours go in.
6. **✋ You try other designs** section by section (see case 3).
7. **✋ A green report**, then it goes live.

**You do:** answer the questions, say "go" at each ✋, and create a server account when asked (click-by-click
steps included).

**Under the hood:** `dh init --mode phased --path scratch` → `dh plan lint` → `dh scaffold` + `dh compose` →
`dh dev start` → `dh rebrand apply/check` → `dh verify` → `dh deploy ship` → `dh handoff`.

## 2. A template I found on GitHub

**Say:**
> I like this template: *github.com/owner/repo*. Check it and, if it's OK, build my site from it.

**What happens:** the agent checks it before touching it. It's either **accepted** or **refused with the
reason and what to look for instead**. It's refused for:
- a copyleft or custom licence, or none at all;
- a paid tier, paid packages, or passwords committed to the repo;
- being abandoned, or not being a real app.

Accepted templates are then cloned, and their rented services (paid login, email, database vendors) are
swapped for ones you own.

**You do:** nothing, unless it's refused. Then pick another template, or go from scratch.

**Under the hood:** `dh pool vet owner/repo` → `dh pool add owner/repo --mine` → `dh clone <name> --to <dir>` →
`dh swap scan/check`.

## 3. Make my existing site look premium

**Say:**
> Take my existing site at *[folder or repo]* and let me try better designs on it.

**What happens:** the agent adopts the site and opens a link to it with a **Try-on** button.
- **Swap it:** click any section (hero, pricing, FAQ, footer…) → 4 licensed designs appear **with your text
  and your colours** → flip with ← → → **Keep** or **Discard**.
- **Tune it:** keep the design but make it *quieter, bolder, airier, clearer, softer or sharper*, or dial
  spacing, headline size, corners, depth, contrast. It changes live. **Keep** or **Reset**.
- **Site** (button next to Try-on): accent colour, warm or cool greys, corners, density, headline size,
  fonts, for the whole site at once. Preview, then **Apply** (or **Undo**).

**You do:** click and choose. That's the whole job.

**Under the hood:** `dh adopt <path>` → `tryon setup` → `tryon serve`. Swap, Tune and Site write your code
directly (with byte-exact undo). No AI runs per click.

## 4. A design no library has

**Say** (or just click **Ask AI to draft one** in the try-on panel):
> None of these fit. Draft one for this section: *[what you want, e.g. "image on the right, big serif title"]*.

**What happens:** your agent writes **one** version for that section. Deckhand checks it before you see it:
- all your words and links are there;
- only your colours are used;
- nothing new needs installing;
- no invented facts.

It then appears next to the other designs with a purple **AI-generated** badge. Any words the AI added
are listed for you to confirm.

**You do:** read the badge, compare, keep or discard. If your agent isn't watching, the panel shows the
exact sentence to tell it.

**Under the hood:** `tryon drafts --wait` → the agent writes `draft.tsx` → `tryon draft-done` (the gates run).

## 5. Launch for $0, even without a domain

**Say:**
> Put it online on the free Oracle server. No domain for now.

**What happens:** click-by-click steps to create the free Oracle account (the one part only you can do).
The agent then installs Coolify and deploys to a free generated address. It's clearly marked **preview**:
no logins or payments until there's a domain and HTTPS. When you're ready, it moves you to a paid host
with a runbook.

**You do:** create the Oracle account (the steps are given) and paste one key when asked.

**Under the hood:** `references/ops/11-oracle-free-tier.md` → `dh deploy target --url http://….sslip.io` →
`dh deploy ship` (smoke warns `NO_TLS`, and `HANDOFF.md` is labelled PREVIEW).

## 6. Go live on my own domain

**Say:**
> Deploy it on my VPS with the domain *mybakery.com*.

**What happens:** the agent sets up the server (firewall, Coolify), points your domain at it with automatic
HTTPS, deploys, waits for **this exact version** to be live, smoke-tests it, and writes `HANDOFF.md`: what
you own, where each login lives, how to get in. It never writes the passwords themselves.

**You do:** buy the domain and the server (links and prices are in the guide), and paste their access when asked.

**Under the hood:** `references/ops/10…30` → `dh deploy target --app <uuid> --url https://…` → `dh deploy ship` → `dh handoff`.

## 7. Keep it running while I sleep

**Say:**
> Set up the bots that watch my site and my business.

**What happens:** it suggests bots that fit your kind of business. What runs from day one:
- an uptime watchdog;
- a broken-link audit;
- backup and dependency checks.

Business bots (weekly KPIs, lead digest, failed payments, booking reminders, review requests, low stock)
come as specs your agent wires to your app. Alerts go to Telegram, Discord, email or a webhook, and
they're sent only when something changes.

**You do:** say where alerts should go.

**Under the hood:** `dh ops suggest` → `dh ops add watchdog --runner github` (free GitHub Actions) or `--runner cron` on your server.

## 8. Stop the agent repeating the same mistake

**Say** (after a session that went badly):
> Run the autopsy on this session and apply what it finds.

**What happens:** a script reads the session log. It isn't the AI's opinion, so the same log always gives
the same report. The report lists:
- every failure, including ones hidden behind `| tail`;
- what **actually** fixed each one;
- what came back more than once;
- where the fix belongs (the skill, your server, your project).

Applying it means:
- next time, the fix prints the moment the error appears;
- safe fixes can replay themselves;
- workflows that worked twice show up as *"this worked last time"*;
- problems in the skill itself become a proposal with a reproduction and the test it needs. The skill is
  never changed behind your back.

**You do:** nothing. If a skill proposal appears and you like it, send it as an issue or PR.

**Under the hood:** `dh autopsy --latest --apply` · `dh run --fix -- <cmd>` · `dh next` (shows `worked_before`).
Harnesses without session logs (Hermes, Codex…): commands run through `dh run` are logged, and that log is autopsied the same way.

## 9. Reuse this site for my next client

**Say:**
> Turn this site into a private starter I can reuse, on my GitHub.

**What happens:**
1. A copy is made with your client's name and brand removed.
2. A scan for passwords and keys runs. If it finds any, nothing is uploaded.
3. The copy is pushed to a **private** repo on your GitHub.
4. It's added to your private library (a README table showing "verified + live").

Next time, on any computer: *"start from my bakery starter"*.

**You do:** create a GitHub token once (the exact clicks are given) and paste it when asked. It's stored
privately, never shown.

**Under the hood:** `dh vault set GITHUB_TOKEN` → `dh harvest --name bakery-starter --push` → elsewhere:
`dh pool sync` → `dh clone bakery-starter --to ./new-site`.

## 10. For developers

- Read [`skills/deckhand/SKILL.md`](../skills/deckhand/SKILL.md) (~150 lines). Every command prints one
  JSON object: exit 0 = ok, 1 = a check failed (with why), 2 = usage.
- Headless try-on:
  `tryon try --file f --line n --col c --slot hero` → `show` / `keep` / `discard`
- Tune and Site through the helper's endpoints: `tune-*`, `theme-*`.
- Add a component library someone found:
  `tryon registry vet|add --index https://…/registry.json --repo owner/name`
  (vetted: licence, paywall, schema, usable items).
- Tests (offline, in CI on Ubuntu and Windows):
  - `python3 -m unittest discover -s skills/deckhand/tests`
  - `python3 -m pytest skills/deckhand/ops/tests -q`
  - `node --test skills/deckhand/tryon/test/*.test.mjs`
- Rule of the house: every behaviour change ships with a test. A fix that lives only in prose isn't a fix.

Stuck, or found a better way? [Open an issue](https://github.com/takimdigital/deckhand-skill/issues).
That's how this gets better for everyone.
