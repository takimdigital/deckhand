# Changelog

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
