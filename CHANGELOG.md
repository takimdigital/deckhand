# Changelog

## 2026-09-20 — release hygiene: the leak gate (pack v0.12.2)

- **New gate — `scripts/leak_sweep.py`:** one command scans the repo tree, the commit history and
  every harness copy for private-project terms (list kept privately at `~/.deckhand/private-terms.txt`
  — never in this repo), and `--file` gates a release-notes draft too. Non-zero exit on any hit.
- **New — `RELEASING.md`:** the release checklist at the repo root where the work happens — load
  `skill-pack-publishing` → run the gate → parity → zip → tag → release with product-only notes
  (improvements + fixes).
- **Fixed:** the public-record rule now explicitly covers release notes and commit messages, and it
  is enforced mechanically instead of by memory — two releases shipped a private project name
  because the rule lived in a skill that wasn't loaded when the notes were written.

## 2026-09-20 — shipped means released (vps-ops v0.8.0 / pack v0.12.0)

A live app's repo shipped with **no releases, no real README, and a stray starter LICENSE** — the
user had to ask. Fixed in the pipeline so nobody ever asks again:

- **The release rule (ref 40 §6b):** a deployed runtime change now ends *tag + GitHub Release* once
  smoke is green — SemVer, ≤8 user-facing bullets, no internal narration, no fluff. Docs-only commits
  deploy nothing and release nothing. First release in an app's life = **v1.0.0**, and it triggers the
  one-time repo-presence pass.
- **The repo-presence kit:** `templates/repo-presence/` + `scripts/repo_presence.py` — fill ONE JSON
  (content only); the script renders README (empty sections dropped, placeholder drift fails loudly),
  LICENSE (proprietary; upstream MIT retained when derived), `package.json` metadata, and sets the gh
  description + topics. Fill content — never rebuild structure. 7 new tests (51 pack-wide).
- **Corrected reality in ref 40:** "deploy: automatic via GitHub App" was false for a loopback-locked
  dashboard (verified live: zero webhooks, every deploy explicitly triggered). The loop, hard rule #8,
  and the SKILL invariant now say what actually happens.
- **v0.12.1:** the `gh`-target trap documented (a repo with an `upstream` remote makes gh aim at
  upstream — `gh repo set-default` or `-R`; live-verified).

## 2026-09-20 — the fresh-eyes audit (audit fixes across all five skills / pack v0.11.0)

Five **zero-context sub-agent audits** read every skill exactly as a first-time consumer would — then
every finding was fixed: buildout's dangling `library.py` path + working-directory/`python3` clarity;
vps-ops ref 10's Step-3b ordering trap (now ⏩ run-after-Step-4) and the env.sh clobber (`>` → `>>`,
plus `VPS_SSH_HOST/KEY` written); **`wait --expect-commit`** so a deploy can never be green-lit on the
previous build; backup docs aligned with reality (both-modes claim, `status.json` contract,
B2 region de-hardcoded + `B2_HOST/B2_REGION` emitted, `fix-clock.cmd` shipped, scoped-key 403
wording); session-autopsy's ref-budget conflict + a missing CHANGELOG; deckhand-profile's `asked`
field made required + read-first widened to "before starting any work"; component-library's store
renamed (`~/deckhand-library`, legacy honored) + `store-format.md` linked; pack "36 tests" → 44.
**44 tests green.**

## 2026-09-20 — the tunnel that heals itself (vps-ops v0.7.6 / pack v0.10.6)

The dashboard tunnel had to be remembered after every reboot — now it doesn't: `coolify_api.py
tunnel` health-checks and starts it as a detached background ssh (given `VPS_SSH_HOST`/`VPS_SSH_KEY`,
a one-time vault setting), and `deploy` preflights it automatically. Live-proven after a real reboot:
tunnel down → one command → `tunnel OK`. Deploys self-heal; nobody has to remember the tunnel.

## 2026-09-20 — the pull that never was (vps-ops v0.7.5 / pack v0.10.5)

The first real STALE email arrived — and the autopsy found three independent faults stacked into
it: (1) the Windows Task Scheduler leg **never worked** (the wrapper pointed at a bash.exe that
doesn't exist on this machine, and battery conditions blocked the catch-up — an unverified schedule);
(2) the home pull looked like "tigris hangs" but tigris answered in 0.3 s — the real time-eater was
the local-S3 reachability probe retrying for minutes while Docker Desktop was off, killing the run
inside a 300-s tool budget; (3) start-only log lines made a kill indistinguishable from a hang.
All three are fixed and live-proven: probe fails in 0.17 s, pull completes in ~2 s with per-step
timings, the scheduled task fires with `Last Result: 0`. The server side was green through all of it.

## 2026-09-20 — the dead-tunnel trap (vps-ops v0.7.4 / pack v0.10.4)

A deploy failed with `10061 connection refused` on `127.0.0.1:8000` — the SSH tunnel had died
silently (Windows/MSYS ssh resolves `$HOME` to `/home/<user>`, which was absent, so a tunnel started
without a durable `known_hosts` exits on "Host key verification failed"). Fixed durably: verified
`known_hosts` in the vault, canonical tunnel command carries `UserKnownHostsFile` +
`StrictHostKeyChecking=yes`, `coolify_api.py` now prints the restart command when it sees a refused
connection, and ref 10 documents the symptom → cause mapping. Same session: the interrupted
theme/a11y work was resumed, verified (`tsc` + `next build` clean), committed, deployed, and
smoke-verified live (`cqtheme` marker on the production HTML).

## 2026-09-20 — the checkpoint rule (buildout v0.3.1 / vps-ops v0.7.3 / pack v0.10.3)

A real session test went red in an instructive way: the pipeline triggered correctly (loaded the
skills, read `OPS.md` + the pending ledger), implemented for an hour across 27 files — and never
committed once, so when the model stream was cut mid-turn, nothing was shippable. The fix is a hard
rule, not advice: **milestone → verify early → commit → continue**; wide requests ship in **passes**,
each deployed end-to-end; an interrupted run must leave committed, shippable work. Plus the
**deployed-app rule** in buildout: a project directory with `OPS.md`/`.vps-ops.json` is a live app —
local-only is never done.

## 2026-09-20 — the autopsy trigger, spoken plainly (session-autopsy v0.1.1 / pack v0.10.2)

The question every user asks: "can I just ASK it to learn?" — yes, and now the skill says so in the
exact words to use: **"run session-autopsy"**, said in the session that went wrong (it greps its own
transcript — nothing else needed). From another session: pass the session ID or paste the key errors
+ what finally worked. Evidence required, whole log not.

## 2026-09-20 — the WHERE field (deckhand-profile v0.2.1 / vps-ops v0.7.2 / pack v0.10.1)

Pending items now say **where** — not just what and how. Every item carries `WHERE:` with the exact
place a non-tech user can find the thing: a full file path, a URL, or a menu chain. Because "escrow
your restic passwords" is useless to someone who doesn't know what a restic is or where the files
live — and knowing where to look was the last excuse.

## 2026-09-20 — the pending ledger (deckhand-profile v0.2.0 / vps-ops v0.7.1 / pack v0.10.0)

Users don't lose track anymore. A second portable file joins the profile: **`~/.deckhand/pending.md`** —
the ledger of things only the human can do, with status (`open` / `waiting-confirm`), asked-dates,
"WHY it matters" and one-line HOWs. The skills now record items the moment they ask, surface the open
list in every report, close items with a date when done — and the scheduled watchdog nags until each
item is closed. Conditional items (`when: paid launch`) don't nag before their trigger. The profile
template now also carries the standing card-free rule and the backup/automation stack.

## 2026-09-20 — the home S3 option (vps-ops v0.7.0 / pack v0.9.0)

The backup destination question gains another flavour: put the home copy behind a **local S3 with a
real UI** — RustFS in Docker (Docker Desktop), one compose file, browseable console at
`localhost:9001`, and the pipeline's pull mirrors every provider into it automatically (with a
graceful skip when Docker isn't running). Plus a **clock-skew preflight** in the home pull, so the one
failure the first live drill hit can't recur silently.

## 2026-09-20 — the first live drill (vps-ops v0.6.0 / pack v0.8.0)

The backup pipeline went through a full production drill on a real app — every layer is now proven
live, and every trap it surfaced is baked into the skill so nobody re-discovers them: a Tigris bucket
that listed objects but served 0-byte reads (wrong storage class — agents now create buckets via API
and prove readability with a 512 KB round-trip), Coolify's per-container DB users, empty executions
endpoints (the bucket listing is the proof), restic's lack of per-repo credentials, CRLF env files
that hang restic, and Windows clock skew breaking SigV4. The deep layer (restic → B2 + Tigris,
nightly timers + a weekly restore drill that really restores and emails PASS/FAIL) and the home copy
(rclone sync to the owner's PC; Windows Task Scheduler **or** an agent cronjob watchdog) are
template-fresh and verified.

## 2026-09-20 — backups are a choice (vps-ops v0.5.2 / pack v0.7.2)

Every user gets the same deploy-time question the tracks get: **where should the backups live?** —
cloud dual (smart default), cloud + a home copy, or home only (no cloud accounts at all). The home
copy is a **pull** model, so it works behind NAT and nothing ever reaches into the user's network:
mirror the cloud buckets with rclone, or SSH-pull dumps straight off the VPS into a local restic repo
with the exact same tooling the cloud path uses. Scheduling is the user's pick too — plain cron,
Task Scheduler, or an **agent cronjob ("the bot")** that also runs the freshness check and emails on
failure. One script covers both modes: `templates/vps-backup/local-pull.sh`.

## 2026-09-20 — the card-free rule (vps-ops v0.5.1 / pack v0.7.1)

The first live user hit two card walls: R2 won't activate without one, and B2's caps UI is gated too.
The pipeline rule is now explicit — **the free path never asks for a card** — and the provider list was
re-researched to match: the second backup target defaults to **Tigris** (5 GB free, zero egress,
official MCP, no card), with Filebase and Koofr as verified fallbacks; R2 stays as an optional
card-holders' upgrade. Verified live: card-less Backblaze hard-caps accounts at the free-tier boundary
(refused with 403 `cap_exceeded` — never billed), so the primary target is safe without a card, with
loud `cap_exceeded` alerting as the guardrail.

"A backup never stays on the same VPS" is now the pipeline's default: dual offsite targets — Backblaze
B2 primary (hard spend caps, fully API-driven after signup) + Cloudflare R2 secondary (free egress) —
with 3-copy retention so usage stays flat inside the free tiers. Agents configure everything through
Coolify's API (S3 storages, per-target schedules, volume backups with S3-only streaming, backup alerts
into the app's mail chain), verify by listing buckets and running real restore drills, and there's a
deep restic layer for full-VPS disaster recovery. Apps that need uploads get RustFS 1.0 (Apache-2.0;
MinIO CE is dead) with its own two-layer offsite copy. Human steps stay at ONE batched ask.

The chain's coverage is now complete and proven: Brevo's corner closed via its API (domain created,
records added, `authenticate` → verified — plus the new-IP dance: a one-click email to the owner,
both the setup machine and the server authorised). And the first non-dev feedback landed: owner
alerts rewritten in plain language — what happened, that nothing is broken, and that no action is
needed. Drilled live: every provider has carried real mail, and every restore returned the primary.

The failover chain went through a real deployment end-to-end — password reset live, every hop
watched — and the run's findings are folded back: Resend's onboarding key can't manage domains
(a Full-access key is needed for setup), Brevo needs the server's IP authorised before it will
answer at all, Resend's DNS record set corrected to the API's actual output, Mailgun verified with
SPF+DKIM alone, and two field rules for Next.js/Coolify deployments (read env lazily or the CI
build breaks; env changes need a redeploy). The mail-router template carries the fixes. Verified
live: full reset cycle + "drain primary → next provider carried → restore" drill.

## 2026-09-19 — key handover, spelled out (vps-ops v0.4.1 / pack v0.6.1)

First live key walkthrough surfaced the gap: users have no idea *which* key to create, and "add them to
the Coolify env" means nothing outside of dev circles. Ref 70 now walks it provider by provider —
Resend (key prompted at signup; testing address caveat), Mailgun (Settings → API security → Create key,
**Developer** role), Brevo (**API key**, NOT the MCP server key) — and the hand-over ask has a clear
default: paste to the agent (vaulted chmod 600, never echoed) or take the click-by-click Coolify guide.

## 2026-09-19 — auth + login email: the free failover chain (vps-ops v0.4.0 / pack v0.6.0)

"No email, no business." Four research agents verified the September-2026 landscape, and the pack now
ships the missing piece — **login email that actually arrives, at $0**:

- **Auth verdict:** Better Auth (MIT) — verification/reset/magic-link built in, Drizzle `pg`, env-only
  config; Auth.js v5 is still beta + security-patches-only; Lucia is deprecated. The new ref carries
  the Coolify/Traefik/Next-16 gotchas with their exact error strings.
- **Free email chain:** Resend → Mailgun → Brevo (SMTP2GO as the no-branding substitute) behind a
  drop-in `send.ts` router: silent failover, Postgres quota accounting, never retries a bad recipient,
  alerts the owner through the next healthy provider when one throttles — plus the deliverability
  design (one sending subdomain per provider, single SPF include each, DMARC on the root) that makes
  multi-provider sending safe.
- **MCP catalog (modular):** DNS/registrar (Cloudflare, Porkbun, NameSilo official servers) and email
  servers — agent-vs-human autonomy table, never-install-globally policy; extend by appending a section.
- Human steps stay at a single batched ask: create the free provider accounts. DNS records, env wiring
  and the router are agent work.

## 2026-09-19 — deckhand-profile v0.1.1: cold start first-class (pack v0.5.1)

The user-profile create flow now treats the ~90% case as the main path: **cold start** says plainly that nothing is on file yet, then runs the initial interview in one batch (defaults offered; the answers ARE the profile). Context-rich sessions keep the draft-and-ask-only-gaps branch. New **source rule** (SKILL + ref 10): the profile is built ONLY from this workspace and the user's answers — never imported from harness profiles or memory files, so it cannot drift. Updates follow real work as one-line offers; unknowns are omitted, never guessed.

## 2026-09-19 — deckhand-profile: the user, once (pack v0.5.0)

Fifth skill: **`deckhand-profile`** — one portable file, `~/.deckhand/profile.md`, that holds what the pipeline needs to know about the USER: accounts, providers, defaults, preferences. Harness-independent and user-owned (copy it anywhere, edit by hand); no secrets, references only, ≤60 lines, no garbage. Agents read it before asking anything — the read-first rule is wired into vps-ops (SKILL + ref 00) and buildout. Create flow: "create my deckhand profile" drafts from what the agent already knows and asks only what's missing (one batch). Update flow: one-line diffs, offers rather than silent edits. Ships ref 10 (field format) + a fill-in template. Complements `OPS.md` (project cold-start) with the user-level cold-start.

## 2026-09-19 — session-autopsy: failures become instructions (pack v0.4.0)

New fourth skill: **`session-autopsy`** — the learning loop the pack was missing. Call it after any red → green run ("learn from this session", "why did it fail"): it collects evidence cheaply (grep the errors and the fix commit — never full transcripts), walks the cause-chain to the instruction that allowed the wrong path, and fixes it on a strength ladder — **eliminate → pre-flight → reorder → gate → pitfall** — with pitfall entries counted as debt. Ships refs 10/20/30 (evidence routing · the ladder with live cases · how to write the fix) and a ≤40-line report template; hands off to the publishing procedure. Validated against the day's own failures: version-pin CI traps land as rung-2 pre-flights, action order as rung-3 reorder, a dev-seed credential leak as a first-run step, the Windows folder lock as the one legitimate pitfall.

## 2026-09-19 — CI-safe package-manager pin (vps-ops v0.3.1 / pack v0.3.2)

The `packageManager` pin that makes deploys reproducible can break a repo's own CI in two ways — both now pre-listed in the deploy runbook's repo-traps: a workflow that also pins pnpm dies with `Multiple versions of pnpm specified` (ERR_PNPM_BAD_PM_VERSION); and on the Node-24-era action majors, `pnpm/action-setup` must run before `setup-node` (v5 auto-caches the pnpm store and needs pnpm on PATH). One source of truth, canonical step order — verified red → green on a real repo.

## 2026-09-19 — cold-start handoff (vps-ops v0.3.0 / pack v0.3.1)

Every deployment now finishes by writing **`OPS.md`** into the app repo — the single file a future session (human or agent, zero context) reads first: live URL + health checks, server + SSH, Coolify ids, dashboard access, a **secrets inventory by location only**, domain/DNS, and the copy-paste commands for the everyday loop (deploy a change, migrate, logs, owner re-key, smoke) plus the app-specific landmines. New `templates/OPS-handoff-template.md`; the deploy runbook gains §9. No re-discovery, no wasted tokens — the door into any deployed app is one committed file.

## 2026-09-19 — rebrand: Deckhand (pack v0.3.0)

The pack has a name now: **Deckhand** — *bring a $5 server and a $10 domain; your agent turns them into a live business while you go find the clients.* The name carries the insight: the barrier was never the money — it's the overwhelm. That pile of unfamiliar tech is the deckhand's job.

- Repository renamed `expert-build-pack` → `deckhand` (GitHub redirects old links automatically).
- Skill `expert-build-pack` renamed **`buildout`** ("idea → codebase"); cross-references in `vps-ops` and `component-library` updated. Invocation: `/buildout`.
- README rewritten around the cost reality (~$5/month server + ~$10/year domain = the whole door) and the human's job (finding clients). Social-preview + logo assets carry the new name.
- No functional changes to the runbooks; 36 tests green; zip == repo.

## 2026-09-19 — paid track validated live (vps-ops v0.2.2)

A real Next.js + Postgres SaaS was taken from a private repo to a live HTTPS domain on a rented VPS
(Coolify → Cloudflare DNS-only → Let's Encrypt; migrations, seed data, production owner). Every error
the deployment surfaced is now a pre-listed step — that is the whole point of v0.2.2:

- ref 10: new **Step 3b** — host firewall rules do NOT stop Docker-published ports (live-tested:
  0 packets, still reachable); lock the dashboard by loopback-binding 8000/6001/6002 in Coolify's
  compose and re-apply after Coolify upgrades. Plus: `1|…` tokens must be single-quoted; on Windows
  forward 8000 only (6001/6002 can be reserved ports and kill the tunnel).
- ref 12: provider notes — order-to-key flow, no cloud firewall, SSH key install, 4 vCPU / 8 GB
  sizing confirmed for the full stack.
- ref 30: pre-flight repo traps (`packageManager` pin + valid `pnpm-workspace.yaml` — the first
  build died on `packages field missing or empty`); Postgres `start` recovery; new §6b —
  container-side migrate → seed → production-owner flow (and removing dev seed credentials).
- 36 tests green; zip == repo.

## 2026-09-18 — provider price sheet (vps-ops v0.2.1)

- `vps-ops` v0.2.1: new `references/12-provider-price-sheet.md` — Oracle free tier, Contabo Core
  4/6/8/12, Hostinger KVM 1–8, Hetzner CAX11/CX22/CX42 with USD/CAD guidance and sizing rules, so
  provider choice never needs re-research. Suggested order: Oracle → Contabo → Hostinger (Hetzner
  with a price caveat). Ref 11 points at it.

## 2026-09-18 — free-preview track (vps-ops v0.2.0)

- `vps-ops` v0.2.0: new **free preview** track — Oracle Cloud Always Free (2 OCPU / 12 GB Arm) + free `.pp.ua` domain (nic.ua) + Cloudflare DNS-only + Coolify Let's Encrypt, plus a migration runbook to a paid host. New refs `11-oracle-free-tier`, `21-free-domain-cloudflare`, `60-migrate-to-paid`; new `assets/oci-cloud-init.yaml`; SKILL.md two-track routing; user-checklist §3b.
- `expert-build-pack` v0.2.2: cross-links to the free-preview track (buildout step 5 + routing row); frontmatter version corrected (was stale at 0.2.0).
- Research: 5 parallel agents, primary-source-verified — Oracle A1 Always Free halved to 2 OCPU/12 GB (Jun 2026); nic.ua free-order card gate + Telegram activation; Cloudflare accepts `.pp.ua` (PSL); Coolify v4.3.23. First live run pending. 36 tests green.

## 2026-09-17 — live validation pass

- `vps-ops` v0.1.0: full live drill on a real Coolify instance — deploy (image / public repo / private repo), change pipeline, rollback, Postgres provision + query, backups + restore, Dockerfile build pack. 23 tests.
- Fixed from the live drill: deployments API response shape + `finished` status, `envset` HTTP 201, rollback requires the full 40-char image tag, database `initdb` false-unhealthy window, custom-format dumps, database container naming.
- `expert-build-pack` v0.2.1: Buildout Engine hardened. Registry pool 372 → 282 healthy; catalogs velora 64 / reui 1,773 / cult-ui 157. 9 tests.
- `component-library` v0.1.0: save / load components. 4 tests.

## 0.2.0

- Buildout Engine: living MIT registry pool, coherent-random design assembly, design token locking, `component-library` companion skill.

## 0.1.0

- Initial release: expert references, execution-first loops, machine-first handoffs.
