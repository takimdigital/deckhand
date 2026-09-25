# Use cases — copy a sentence, get a result

Every case below has the same shape:

- **Say:** the exact sentence to paste to your AI agent.
- **What happens:** what you'll see.
- **You do:** the only things a human has to do (usually nothing, or one click).
- **Under the hood:** the commands, for the technical readers. Skip it if you're not one.

Install once first ([README](../README.md#-start-in-2-minutes)). In any case, the agent starts with `dh next`
(or `dh resume` in a project that's already under way), and it stops at the ✋ checkpoints until you say go.

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
| 11 | get found on Google and in AI answers | [→](#11-get-found-on-google-and-in-ai-answers) |
| 12 | start a fresh session (or switch AI) without losing anything | [→](#12-start-a-fresh-session-or-switch-ai-without-losing-anything) |
| 13 | build a product to sell, then reuse the path for the next trade | [→](#13-build-a-product-to-sell-then-reuse-the-path-for-the-next-trade) |
| 14 | find out what went wrong (and what I should have been asked) | [→](#14-ask-what-went-wrong-and-what-i-should-have-been-asked) |
| 15 | know what to do next | [→](#15-know-what-to-do-next) |

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
- **No browser handy?** Say it in chat: *"make the hero airier"*, *"warmer greys and rounder corners"*.
  The agent applies the same changes, and you can undo them just as easily.

**You do:** click and choose. That's the whole job.

**Under the hood:** `dh adopt <path>` → `tryon setup` → `tryon serve`. Swap, Tune and Site write your code
directly (with byte-exact undo). No AI runs per click. From chat: `tryon tune …` / `tryon theme …`.

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

- Starting a session with an AI that has never seen this repo? Tell it to read
  [`LLM_CONTEXT.md`](../LLM_CONTEXT.md) first. It holds the whole repo in one file: how it works, where
  everything lives, and every command and function with its line number. It's regenerated from the code, so
  it's never out of date.
- Read [`skills/deckhand/SKILL.md`](../skills/deckhand/SKILL.md) (~160 lines). Every command prints one
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

## 11. Get found on Google and in AI answers

**Say:**
> Make sure my site can be found on Google and in ChatGPT. Tell me exactly what you need from me.

**What happens:**
- **Built from scratch, or your own folder:** SEO goes in automatically.
- **Built from a template or one of your starters:** the agent checks what's missing, shows you a report, and
  strongly recommends adding it before launch.

Either way, the scripts write it from your own facts, and your own titles and words are never overwritten. You get:
- a score;
- the launch-breakers (fixed before going live);
- your to-do list, with the exact clicks for each item:
  - your Google Business Profile;
  - Google Search Console;
  - Bing, which feeds ChatGPT search and Copilot;
  - your first reviews;
  - facts only you know: your address, opening hours, social profiles and category.

That list stays in every report until it's done.

**You do:** the items on that list. Nothing else.

**Under the hood:** `dh seo audit` → words in `.deckhand/copy.json → seo.pages` → `dh seo apply` → `dh verify`
(row `seo`) → after launch `dh seo audit --url https://<domain>`; every production `dh deploy ship` pings IndexNow.
Nobody can promise #1 on Google; this makes sure nothing in our control is missing.

## 12. Start a fresh session (or switch AI) without losing anything

**Say** (in the old session, before you leave):
> Can I start a fresh session now?

**What happens:** the agent answers from a computed check, not from a feeling:
- **YES** → nothing lives only in this chat. Open a new session.
- **NO, and why** → for example, "2 files changed since the last note". The agent writes down what it was doing,
  in one line, and then it's a YES.

After a checkpoint you approved (✋), the agent tells you on its own when it's a good moment to start fresh.

**Then, in the new session** (any agent: Claude, Codex, Cursor…):
> Continue my bakery site.

It reads the project's one-page summary: where it stands, what's done and the proof, your decisions, what's
waiting on you, and the exact next step. Then it carries on. If you're not sure the summary still matches
reality, say *"check that everything is still true"*.

**Working for clients?** Say *"this one is for a client"* at the start. That client's settings and keys stay in
that client's project folder, on your computer only. They're never used for another client and never pushed to
GitHub.

**You do:** nothing. With Claude Code, `./install.sh --claude-hook` once makes every new or compacted session
pick up the summary on its own.

**Under the hood:** `.deckhand/RESUME.md` is regenerated after every `dh` command (gitignored, under ~1,500
tokens) · `dh note decision|doing|next "…"` · `dh resume` (verdict: SAFE TO START A FRESH SESSION) ·
`dh resume --check` (re-proves the claims) · `AGENTS.md` block written by `dh init` · SessionStart hook
`dh resume --hook` · `dh init --for client` + `dh vault set NAME` (project layer).

## 13. Build a product to sell, then reuse the path for the next trade

**Say:**
> Build me a premium, production-ready boilerplate for cleaning companies that I will sell. Phased mode.

**What happens:** before any question, the agent asks Deckhand for the 3 proven paths that fit ("a multi-role SaaS
product for a home-services trade") and shows them to you with their proof. You pick one; from then on it follows
that path step by step. All its questions come in ONE message, including the ones earlier runs learned too late
("a fictional demo company, or yours?"). The demo company lives only in the seed, with a script that wipes it; each
buyer's own details go in the app's settings; the review checks the buyer's kit (README, licence, customization
guide). For a bigger app it builds the foundation itself, then splits the rest across parallel builders who never
touch the same folder, and re-checks their work before showing you.

**Next time:**
> Now the same for plumbing companies.

The cleaning path comes back first ("same family: the path transfers, the words change"), improved by what the first
run taught it.

**You do:** answer the first message, approve the plan and the running app.

**Under the hood:** `dh workflow query` · `dh workflow use` · `dh brief set deliverable=product` · `dh plan split
--agents N` (AGENT-n.md + CONVENTIONS.md) · `dh dev add db …` · `dh verify` (row product-kit) · `dh harvest --push`.

## 14. Ask what went wrong (and what I should have been asked)

**Say** (at any moment — mid-build is fine):
> Run the workflow autopsy.

**What happens:** Deckhand replays the session with no AI involved. You see:
- every question the agent asked you and what you answered;
- which answers came too late and made it redo work;
- where it left its workflow;
- what each failure cost, in minutes.

Then comes a short list of proposed fixes to the workflow, each with the reason and the evidence. You choose where the
ones you accept go:
- **your own workflows**, on your computer only;
- **the community**, as a reviewed pull request;
- **nowhere**.

Anything that is Deckhand's own bug goes into a separate report you can send to its maintainer. The autopsy never
changes Deckhand itself.

**You do:** read the list, say which ones to keep and where.

**Under the hood:** `dh autopsy --workflow [--part questions]` (reads Claude Code sessions, Hermes' `state.db` or any
chat log) · `dh workflow save --from-autopsy W-… --proposals P1,P3 [--public]` · `.deckhand/autopsy/W-….maintainer.md`.

## 15. Know what to do next

**Say:**
> What should I do next?

**What happens:** after the list of what waits on you, the agent reads out a few suggestions, most important first:

```text
NOW   · Stop retrying: the same command failed 3 times — `npm run build` → dh learn match --text "npm run build"
SOON  · Decide on 2 workflow improvements: keep them for next time, share them, or skip → dh workflow save --from-autopsy W-… --proposals P1,P2
LATER · A fresh session is safe now (and sharper) → dh resume
```

They're computed from your project's files: a failure that keeps coming back, a plan changed after you approved it, a
checkpoint worth reviewing, a task you deferred that is now due, a finished run worth keeping as a workflow. Every
report ends with them. They're optional: say *"not now"* and that one goes quiet for a week.

**You do:** pick one, or ignore them.

**Under the hood:** `dh suggest [--all]` · `dh suggest dismiss ID [--days N]` · the `suggest` field of `dh next` ·
the "Next" section of `.deckhand/RESUME.md`.

Stuck, or found a better way? [Open an issue](https://github.com/takimdigital/deckhand-skill/issues).
That's how this gets better for everyone.
