# Changelog — vps-ops

## 0.7.2 — 2026-09-20

- Pending-ledger format gains **`WHERE:`** (exact file path / URL / menu chain) — ref 00 updated; the
  nightly nag email includes it so the owner never has to go searching.

## 0.7.1 — 2026-09-20

**The pending ledger hooks** — human tasks can no longer vanish into chat scroll:

- The promise now reads BOTH portable files (`profile.md` + `pending.md`, skill `deckhand-profile`):
  surface open items in every report, record new human tasks the moment they appear.
- ref 00: record/surface/close rules for `~/.deckhand/pending.md` (id · what · WHY · HOW · asked date · status).
- `OPS.md` template: TL;DR item 9 points at the ledger (project-tagged) before asking the owner anything.

## 0.7.0 — 2026-09-20

**The local-S3 home target (Docker Desktop + RustFS) + last-mile hardening**

- ref 55 §0b/§7: the home copy gains a target choice — plain folder (default) or a **local RustFS S3**
  with a browseable console: `templates/vps-backup/rustfs-local.compose.yml` (`rustfs/rustfs:1.0.0`
  pinned, **loopback-only** 9000/9001, creds via `.env`, named volumes). Console at
  `http://localhost:9001` (`/rustfs/console/` — `/` is 403 to curl, fine in a browser); rclone remote
  uses `force_path_style`; `LOCAL_S3_REMOTE` mirrors each provider in; **target down = one logged
  skip, never a failed run**. Verified live on Docker Desktop (health at 18s, put/get/delete, full
  mirror, PGDMP readback). Docker Desktop free for personal use; Podman/Rancher/WSL2 alternatives noted.
- `templates/vps-backup/local-pull.sh`: **clock-skew preflight** (warns before SigV4 dies — the exact
  failure the first drill hit, now impossible to hit silently), optional `LOCAL_S3_REMOTE`, unreachable
  target tolerated.
- ref 56: cross-link — a local RustFS can serve as a third browseable copy of app uploads.

## 0.6.0 — 2026-09-20 — **the first live drill** (backups, end-to-end on a real app)

Every layer exercised on CitiQuiz; the traps found live are now baked in so the next run skips them:

- **Deep layer verified**: restic → B2 + Tigris, nightly timers + weekly restore drill that really
  restores (both repos, `pg_restore`, sanity query, PASS email delivered). Templates replaced with the
  battle-tested `coolify-backup.sh` (per-repo credential wrappers, per-container DB-user auto-detect,
  LF-env guard, `flock`, per-db drill restore + `SANITY_DB`).
- **New scripts**: `b2_setup.py` (bucket + lifecycle + scoped key; v4 `bucketIds` quirk), 
  `tigris_bucket.py` (API-created STANDARD bucket + 512 KB readability proof), 
  `coolify_backup_setup.py` (storages + schedules), `backup_verify.py` (bucket listing = the proof).
- **Tigris class trap** (§0/§3/§5): a console-created bucket can be GLACIER class → lists objects but
  serves every read >1 KB as HTTP 200 + **0 bytes** (rclone `unexpected EOF`, python `IncompleteRead`).
  Agents create buckets via API; verify with a 512 KB round-trip. Deleted bucket names sit in a
  ~10-min cooldown → pick a new name.
- **Coolify v4.3.23 quirks**: DB users are per-container (auto-detect via `printenv`); on-demand
  `backup_now` re-trigger via PATCH is unreliable (DELETE + re-POST); executions can stay empty —
  **list the bucket**, the object is the proof.
- **Home copy verified** (§7): rclone sync of both buckets to a Windows PC (restic repos included →
  local restore works); Task Scheduler recipe + Hermes-cronjob watchdog (gateway must be running);
  Windows pitfalls: `C:/…` native paths, **clock skew >15 min breaks SigV4** (fix: `w32time` +
  `w32tm /resync /force`).
- **Mail-router rule** (§2): alert bodies must contain a link — guarded alert routes append the app URL.

## 0.5.2 — 2026-09-20

**Backups are a choice, and home is an option** — same spirit as the Track P/F ask:

- ref 55 §0b: one deploy-time question — **cloud dual (default) / cloud + home copy / home only** —
  an offer, never forced; ③ keeps identical restic tooling (local repo) so drills/alerts carry over.
- ref 55 §7: home copies via the **pull model** (works behind NAT): `rclone sync` from the cloud, or
  SSH-pull of `pg_dump` + volume tarballs straight off the VPS when there's no cloud at all; local
  RustFS if an S3 interface is wanted; schedulers = cron / Task Scheduler / **agent cronjob ("the
  bot")**; alerting from home posts to the app's alert endpoint.
- `templates/vps-backup/local-pull.sh` — both modes, one small script; alert + trap built in.
- ref 00: the destination question is now step zero of the backup hand-off.

## 0.5.1 — 2026-09-20

**The card-free rule, enforced by the provider list** — the first live user hit two walls: Cloudflare R2
demands a card to activate, and Backblaze's Caps & Alerts UI is card-gated. Three research agents went
out (no-card S3 alternatives; rclone fallbacks; B2-without-card policy) and the refs now carry:

- ref 55: second target is now **Tigris** (5 GB free, zero egress, official MIT MCP, Coolify partner —
  no card) with Filebase + Koofr as fallbacks; **R2 demoted to optional** (card required). New
  "B2 without a card" block: non-paying accounts are hard-capped — boundary = `403 cap_exceeded`
  (refused, never billed); caps cannot be set via API/CLI; treat 10 GB as a wall, alert loudly on
  `cap_exceeded`, never shard accounts (AUP).
- ref 55 §5: deep-layer second repo = Tigris (S3) or **Koofr via restic's rclone backend** (10 GB,
  app-password, verified end-to-end; `flock` serialization; Proton Drive blocks rclone, Telegram has no
  backend).
- ref 80: storage MCP domain gains Tigris (official) and the rclone/Koofr + Filebase notes.
- ref 00: the backup ask is now Backblaze + Tigris, both card-free.

## 0.5.0 — 2026-09-19

**Offsite backups become the day-one default** — "a backup never stays on the same VPS". Researched by
four parallel agents (source-verified against Coolify tag v4.3.23; live drill next):

- New `references/55-offsite-backups.md` — dual targets **Backblaze B2 (primary: hard spend caps +
  fully API-driven) + Cloudflare R2 (secondary: free egress = drill source)**; exact Coolify API flow
  (S3 storage create → validate; one DB schedule per target; volume schedules with S3-only streaming;
  webhook alerts into the app's mail chain), honest verification rules (list the bucket; drill the
  restore; count retention), the no-restore-API reality with the agent-side workaround, and the known
  gaps list so nobody rediscovers them live.
- New `templates/vps-backup/` — the deep layer: restic → both providers (Coolify's own `coolify-db` +
  every DB + volume allowlist), keep-last-3 pruning, weekly verified drill (subset check + real
  `pg_restore` from R2), systemd units, and the B2 hidden-version trap. `[verify at live drill]`
- New `references/56-app-object-storage.md` — apps with uploads get S3-compatible storage on the VPS:
  **RustFS 1.0 (Apache-2.0)** as the default (MinIO CE is archived + AGPL — disqualified), pinned-image
  Coolify compose deploy, the Next.js env contract with presigned PUTs, and the two-layer offsite copy
  (rclone bucket sync + weekly volume tar).
- ref 50 §5 + ref 00 §5 updated (offsite is no longer "optional"); ref 80 gains a storage MCP domain
  (official B2 MCP, MIT; R2 rides the Cloudflare MCP; RustFS MCP).

## 0.4.3 — 2026-09-19

The Brevo corner, closed — second live pass:

- ref 70 §2/§3: **Brevo's domain setup is fully API-able** — `POST /v3/senders/domains` returns the
  records (2 DKIM CNAMEs + `brevo-code` TXT + a required `_dmarc.<subdomain>` TXT), then
  `PUT /v3/senders/domains/<name>/authenticate` flips it to `authenticated:true verified:true`.
  New-IP handling documented: the 401 also triggers a one-click "authorize the new IP" email to the
  account owner (account-alerts@t.brevo.com — legitimate); both the setup machine and the app server
  must be authorised.
- mail-router template: owner alerts are now plain-language — what happened, that nothing is broken,
  that mail continues via the next provider, and that no action is needed. Written for non-dev users,
  after the first real one asked.
- Verified live: all three providers have now CARRIED real mail — resend ✓, mailgun ✓ (drain drill),
  brevo ✓ (both-drained drill) — and each restore put the primary back.

## 0.4.2 — 2026-09-19

First live run of the email chain on a real Next.js + Coolify + Postgres deployment — every finding
from the run, folded back:

- ref 70 §2: **Resend's onboarding key is Sending-only** (`401 restricted_api_key`) — creating/verifying
  a domain needs a **Full access** key (or the dashboard route). **Brevo** refuses API calls from
  unrecognised IPs (`401 unrecognised IP address`) until they are authorised at
  app.brevo.com/security/authorised_ips — both the setup machine's IP and the app server's.
- ref 70 §3: Resend's record set corrected to what the API actually returns (`send.` MX + TXT,
  `resend._domainkey` DKIM, `rsend` return-path CNAME); Mailgun live-verified with SPF + DKIM alone
  (receiving MX and tracking CNAME stay off; a Developer-role key can create + verify the domain).
- ref 70 §4: field rules — read env INSIDE functions (module-scope env breaks `next build`), env
  changes need a redeploy (restart doesn't re-read; cached rebuild ≈ 75 s), and a note that agents can
  read their own outbound back from the provider API (no inbox needed for e2e tests).
- `templates/mail-router/send.ts`: lazy env reads, alert mails carry `html`, failover alerts start
  after the failed provider by id (not array index).
- `templates/OPS-handoff-template.md`: new Email section.
- Live-verified: full password-reset cycle end-to-end + the drain drill (primary drained → next
  provider carried → restore → primary again), with `email_attempt`/`email_quota`/`email_alert_state`
  recording every hop.

## 0.4.1 — 2026-09-19

Key-handover UX, from the first real walkthrough (the keys were found — but by guessing at the
dashboard): ref 70 §2 now carries the exact per-provider key walkthrough —
Resend (key prompted at signup; `onboarding@resend.dev` only reaches your own address until a domain is
verified — never ship it), Mailgun (Settings → API security → Create key → role **Developer**; enough to
send, smallest privilege), Brevo (**API key** — the MCP server key beside it is only for the optional MCP
session, never for sending). Hand-over is now explicit with a default: paste to the agent (vaulted,
chmod 600, never echoed) or ask for the click-by-click Coolify guide — no bare "drop them into Coolify
env". ref 80's Brevo row flags the API-key-vs-MCP-key split too.

## 0.4.0 — 2026-09-19

**Auth + login email** — "no email, no business". Researched by four parallel agents, primary-source
verified 2026-09-19, then shipped as building blocks:

- New `references/70-auth-and-email.md` — the auth verdict (**Better Auth** ≥1.7.5: MIT, built-in
  verify/reset/magic-link, Drizzle `pg`; Auth.js v5 still beta + security-only; Lucia deprecated), its
  Coolify/Traefik/Next-16 facts (`BETTER_AUTH_URL`, `Invalid origin`, `nextCookies()` last, `proxy.ts`),
  the **free email chain Resend → Mailgun → Brevo** (Sept-2026 quotas + corrections), the per-provider
  sending-subdomain DNS design (one SPF include each; DMARC on the root; tracking OFF), and the
  auth+email smoke test. ONE batched human step: create the free provider accounts — everything else
  is agent work.
- New `templates/mail-router/` — drop-in multi-provider failover sender: `send.ts` (HTTP APIs only;
  Postgres quota authority; strict failover classes — never retry a bad recipient; idempotent;
  edge-triggered owner alerts via the next healthy provider; link-integrity assertion), `schema.sql`,
  `.env.example`, wiring README. No mature OSS library exists for this — hence owning it.
- New `references/80-mcp-integrations.md` — the modular MCP catalog (append one section per domain):
  DNS/registrar (Cloudflare Code Mode; Porkbun + NameSilo official servers; agent-vs-human autonomy
  table) and email read/setup servers. Policy: never install globally; workspace-scoped only; the
  stdlib scripts stay the deterministic path.
- `00-user-checklist.md` §5 — the email row now names the free chain; single batched ask.

## 0.3.1 — 2026-09-19

CI safety net for the `packageManager` pin — both failure modes live-verified (red → green) on a real repo:

1. A CI workflow that ALSO pins pnpm (`pnpm/action-setup` with `version:`) fails the job in seconds:
   `Multiple versions of pnpm specified` / `ERR_PNPM_BAD_PM_VERSION`. One source of truth: keep the
   `packageManager` pin, drop the workflow's `version:` (the action reads `packageManager` itself).
2. On the Node-24-era action majors (`checkout@v5`, `setup-node@v5`, `pnpm/action-setup@v6`), the step
   order is load-bearing: `pnpm/action-setup` must run BEFORE `setup-node` — v5 auto-caches the pnpm
   store and must find `pnpm` on PATH, or the job dies with `Unable to locate executable file: pnpm`.

Ref 30's repo-traps list now carries both; the same pass moves workflows off Node-20-era action majors.

## 0.3.0 — 2026-09-19

New: **the cold-start handoff.** Every deployment now ends by writing `OPS.md` in the app repo
(ref 30 §9 + `templates/OPS-handoff-template.md`): live URL + health checks, server/SSH, Coolify ids and
dashboard access, **a secrets inventory by location** (never values), DNS, the copy-paste everyday
commands, and the app-specific "do not" list. A fresh session — human or agent, zero context — starts
working from that one file: no re-discovery, no wasted tokens. Validated on the first live deployment
that followed this release.

## 0.2.2 — 2026-09-19

Paid track validated end-to-end by a first real deployment on a rented VPS (Coolify → Cloudflare DNS
→ Let's Encrypt, Postgres + migrations + seed data + production owner). Each item below is an error
that deployment actually surfaced, caught and fixed — now pre-listed so the next run doesn't hit them:

- ref 10: new **Step 3b — dashboard lockdown, the docker-aware way.** Host firewall rules do NOT stop
  Docker-published ports (live-tested on Docker 29: DOCKER-USER + INPUT DROP showed 0 packets while
  8000 stayed publicly reachable). New procedure: loopback-bind the ports in Coolify's own compose,
  verify three ways, and re-apply after every Coolify upgrade (upgrades re-download the compose
  files and silently restore the public binds).
- ref 10: two smaller traps caught — the API token's `|` silently breaks any unquoted env file
  (`Unauthenticated.` on every call; single-quote it), and on Windows, forwarding ports 6001/6002
  can fail as "reserved" and `ExitOnForwardFailure` then kills the whole tunnel (forward 8000 only).
- ref 12: provider notes from the same deployment — order-email contents, no cloud firewall, the
  SSH_ASKPASS key-install flow, and sizing confirmation (4 vCPU / 8 GB runs the full stack).
- ref 30: **pre-flight repo traps.** The first build died with `packages field missing or empty` (a
  placeholder `pnpm-workspace.yaml` + no package-manager pin) — the ref now checks these before the
  first deploy. Also: Postgres recovery when the container never materializes
  (`POST /databases/{uuid}/start`; trust `docker ps`, not Coolify's lagging status), and new **§6b**:
  container-side migrate → seed → production-owner creation, including removing any dev seed
  account before going live.

## 0.2.1 — 2026-09-18

- New `references/12-provider-price-sheet.md` — the "Oracle is out" answer: provider decision order +
  verified prices (Contabo / Hostinger / Hetzner / Oracle) + Coolify sizing rules. Quote the sheet,
  re-verify the one number you promise — no per-user price research.
- ref 11's "signup failed" ladder now points at the sheet instead of naming a single fallback.

## 0.2.0 — 2026-09-18

Free preview track (Oracle Cloud Always Free + free `.pp.ua` domain + Cloudflare DNS-only +
Coolify Let's Encrypt) — researched and primary-source-verified 2026-09-18.

- New `references/11-oracle-free-tier.md` — the $0 preview server: A1 2 OCPU/12 GB limits (halved
  from 4/24 in Jun 2026), capacity ladder, signup/card gates, instance creation, the two-firewall
  fix, SSH-tunnel dashboard, Arm notes, idle-reclamation risk.
- New `references/21-free-domain-cloudflare.md` — `.pp.ua` at nic.ua (card gate + Telegram
  activation + real WHOIS), Cloudflare DNS-only zone (pp.ua is on the PSL → valid), alternatives ranked.
- New `references/60-migrate-to-paid.md` — free → paid cutover: recreate (no export/import in
  Coolify), pg_dump/restore, integrity gate, DNS swap, rollback matrix, Stripe/OAuth repointing.
- New `assets/oci-cloud-init.yaml` — first-boot asset (root key + opens iptables 80/443) for OCI
  instance creation.
- SKILL.md: two-track routing (Track P paid / Track F free preview), track invariants, quickstart fork,
  expanded description + tags.
- `00-user-checklist.md`: new §3b (Track F ask-list); `10-bootstrap-vps.md` and `20-domain-dns-ssl.md`
  get one-line track forks.
- Status: researched + verified against primary sources; first live run pending (`[verify at live drill]`
  markers in refs 11/21/60).

## 0.1.0 — 2026-09-17

Initial release: Coolify bootstrap (SSH → firewall → install → admin/token → hardening → snapshot),
domain/DNS/SSL, app deploy, change pipeline, ops; Hostinger API; live-validated against a real
Coolify instance (deploy · change → smoke · broken-deploy caught → full-tag rollback → revert ·
Postgres + backup restore drill · Nixpacks + Dockerfile packs · 23 unit tests).
