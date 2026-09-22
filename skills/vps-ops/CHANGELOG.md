# Changelog — vps-ops

## 0.9.9 — 2026-09-22

- **Every local-S3 probe is bounded or not run at all.** A watchdog step carrying a bare `rclone lsf -R rustfs:<app>-home` retried for minutes against a stopped Docker Desktop and ate the tool timeout (exit 124 @26 s; the bounded form exits 5 @0 s — and the state was already answered by the pull log's own `local S3 ...` line). Ref 55's fast-fail rule now scopes to EVERY probe: the pull's own probe AND any ad-hoc check inside a watchdog/health step — read the newest `local S3 ...` log line first, probe live only when it is stale, and then only bounded.
- **Default-`~/.ssh/known_hosts` repair path documented** (ref 10): `ssh-keygen -R <ip>` then re-add the current line from the vault copy — never an in-place text edit (the harness guard blocks `~/.ssh/known_hosts` edits, which left a poisoned default file stale). The agent-path stays on the vault file (`-o UserKnownHostsFile="$HOME/.vps-ops/ssh/known_hosts"`), which remains correct.
- Housekeeping from the same autopsy: the deployed local-rustfs compose pins `rustfs/rustfs:1.0.0` (it carried `:latest`, matching the pack template's pin — a silent re-pull can change a working local S3 on the next Docker start).

- **Cold-read audit fixes (pre-release; every finding verified against the files).** Step 5's `$COOLIFY_URL` now exports the tunnel's local end (`http://127.0.0.1:8000` — the old public-IP form could never answer its own verification curl once Step 3b closed :8000); Track F's skip line + the SKILL.md invariant now name the OCI Security List + tunnel as Track F's dashboard lock; ref 50's update path re-runs Step 3b after every Coolify upgrade (loopback binds are lost on upgrade); ref 55 §1/§3 clarify `backup_now` proves the dump path, never the schedule (the Coolify leg fires via `backup trigger` / `backups/run`) and §3 names `backup_verify.py`; **`backup_verify.py` now FAILS on an empty schedule list and on a failed/cancelled newest execution — both passed silently before** (+3 tests); first-deploy + change-pipeline smokes carry `--contains` (incl. the handoff table — a bare 200 can't tell your app from a default page); the DNS pre-change dump never overwrites itself (timestamped filename); the optional Coolify CLI has a documented install (ref 10) and SKILL.md states nothing requires it; the tools list gains `backup_verify.py` + the backup setup scripts; ref 50's dual-target default now reads B2 + Tigris (both card-free; R2 optional) matching refs 55/00.

## 0.9.8 — 2026-09-22

- **The backup chain can no longer silently mismatch (live-hit: the first live backup died on the raw naming mismatch).** `coolify-backup.sh` normalizes the env: `https://` prefixes on `B2_HOST`/`TG_HOST` stripped, and the vault's own names (`B2_APP_KEY_ID`/`B2_APP_KEY`, `TIGRIS_BUCKET`, `TIGRIS_ACCESS_KEY_ID`/`TIGRIS_SECRET_ACCESS_KEY`) accepted as aliases — either form works. `templates/vps-backup/README.md` step 3 maps vault → `/etc/backup/env` 1:1 and warns about CRLF (repo pins `*.sh` to LF).
- **Gates that can go red:** `backup_verify.py` and `coolify_backup_setup.py` now exit non-zero when a leg fails or a bucket listing comes back empty — both used to always exit 0 (a gate that can never fail is not a gate).
- Ref fixes from the cold-read audit: `app.<domain>` → `<domain>` / `www.<domain>` everywhere (the DNS plan owns @/www/coolify — nothing invented); ref 00 dashboard access = the agent's SSH tunnel (`http://localhost:8000`), never `http://<ip>:8000`; ref 10's firewall note scopes 8000/6001/6002 to bootstrap-only (removable after Step 3b) and the failure row no longer tells anyone to re-open 8000; ref 30's `.vps-ops.json` example gains `track` (+`region` on Track F) and the tunnel URL; the weekly harness check is now defined by pointer; SKILL.md one-time-moments wording covers Track F and the one public-key paste; a placeholder key (`$VPS_IP`/`$DOMAIN`/`$CF_ZONE_ID`) is stated once in SKILL.md; ref 60's migration dump/restore detect the per-container DB user (ref 55 §5) instead of hardcoding `-U postgres`.

## 0.9.7 — 2026-09-21

- **The "every agent-side ssh carries the vault flag" rule is now exhaustive — references AND templates.** The 0.9.6 fix covered the gate, the tunnel, and ref 55's rule; a two-pass sweep then closed every remaining EXAMPLE a copy-paste agent could follow: ref 10 (ufw firewall, loopback-bind compose edit, Coolify install + container check, hardening + password test), ref 11 (Oracle iptables verify/fallback, access gate, tunnel), ref 30 (first-run data steps: container find, migrate, seed, owner delete/create), ref 50 (restore drill, incident table, Coolify/OS upgrades), ref 55 §7 choice ③, ref 60 (migration dump/scp/restore), and the OPS-handoff template (ssh info, tunnel, everyday commands). 40 ssh lines now carry `-o UserKnownHostsFile="$HOME/.vps-ops/ssh/known_hosts" -o StrictHostKeyChecking=yes`; the closing check is an exhaustive grep classifier (prose and anti-examples excluded) — zero bare runnable forms remain.

## 0.9.6 — 2026-09-21

- **Unattended checks survive Windows SSH quirks (live-hit):** a scheduled harness check died with `Host key verification failed` — its ssh was bare, and MSYS ssh resolves `~` to `/home/<user>`, so the vault known_hosts was never read. Every agent-side ssh recipe now carries `-o UserKnownHostsFile="$HOME/.vps-ops/ssh/known_hosts" -o StrictHostKeyChecking=yes` from first contact (the Step-2 gate stores the host key in the vault); the ref 10 trap is scoped to ALL ssh (not just tunnels) and its failure-table remedy for `Host key verification failed` is corrected (the old `ssh-keygen -R` advice ignored the home-resolution cause).
- **Agent-cron fires: shell `-c`/`-lc` wrappers are refused by the harness approval guard** (live-hit — the Task-Scheduler form `bash -lc "HOME=… bash …"` cannot run unattended). Ref 55 §7 now says: invoke scripts directly (`bash /path/script.sh`) in agent-cron recipes; keep the `-lc` wrapper only for Windows Task Scheduler.

## 0.9.5 — 2026-09-21

- **Pre-push lockfile pre-flight (ref 40 §3):** when `package.json`/`pnpm-lock.yaml` changed, run `CI=true pnpm install --frozen-lockfile` (exit 0 required) BEFORE the push; deploys install frozen and die on drift (`ERR_PNPM_OUTDATED_LOCKFILE` — a real deploy was lost to this exact class). The repair line — `CI=true pnpm install --no-frozen-lockfile` + commit the lockfile in the same push — is inline with the check.

## 0.9.4 — 2026-09-21

- **`coolify_api.py dlogs <APP_UUID>`** — the newest deployment's build log, JSON-decoded, tailed (`--tail N`) and greppable (`--grep ERR_PNPM`, `--deployment <id>` to pin). Build failures are now read from one command — before, the raw listing's `logs` field was the only path and needed a custom script.
- **Release versioning checkpoint (ref 40 §6b + hard rule 11):** the tags are the source of truth — read `gh release list` before choosing the next version; a wrong tag/release is deletable and re-cuttable (`gh release delete` + `git tag -d` + push the ref deletion). Born from a live drift: releases at v1.2.0 while package.json/README still said 1.0.0, which briefly cut a numerically-older "latest" release.
- **Failure-table row + repair:** `ERR_PNPM_OUTDATED_LOCKFILE` kills the DEPLOY at install (never the local build) — `CI=true` installs are frozen by default; repair with `CI=true pnpm install --no-frozen-lockfile`, commit `pnpm-lock.yaml`, redeploy. (Also: never `| tail` an install whose exit code matters — the pipeline reports tail's exit.)

## 0.9.3 — 2026-09-21

- **ref 40 — optional design gate for user-facing changes:** when an app ships the design-audit kit (buildout ref 30), run `pnpm design:audit:fast` + `pnpm design:fails` before the release step and carry one `Design:` line in the receipt; baselines are never regenerated during a deploy (they move only in their own explicit commit). New hard rule #10: a red gate blocks the release like a red build.

## 0.9.2 — 2026-09-21

- **"A schedule is verified only by its own trigger" (new invariant + ref 55 §3).** The verification section now requires EVERY scheduled leg — systemd unit, Windows task, cronjob, Coolify schedule — to fire once through the mechanism that will run it and leave a fresh artifact from THAT run before "backups live" may be claimed. Manual script runs prove the script, never the schedule (live-hit twice: a Windows task that had never run, then a systemd unit that died on its first fire while every manual drill passed).
- **First-fire proof is now an install step** in the backup template README: fire both units by hand, require `rc=0` + `status ok` + a fresh snapshot on each repo + the verify PASS email.

## 0.9.1 — 2026-09-21

- **First-scheduled-run hardening (live-hit):** the nightly backup failed under systemd — restic 0.19 hard-fails without `$HOME` (`unable to locate cache directory: neither $XDG_CACHE_HOME nor $HOME are defined`) while every manual drill passes in an interactive shell. The script now pins `RESTIC_CACHE_DIR` itself, and it was proven by re-running the exact failing unit (`status ok`, fresh snapshots on both repos).
- **Failure emails must show the FAILING run:** `die()` tails the append-only log — steps that don't tee their output made the failure email show the previous run's output (exactly what happened: the failed nightly's body was the last drill's tail). All restic steps now append to `$LOG`; every run opens with a `=== run start ===` marker. Template + templates README + ref 55 carry both traps.

## 0.9.0 — 2026-09-20

- **Access before asks (new invariant + refs 21/70):** the Cloudflare token is created with the FULL pipeline scope set in one go (`Zone → Zone → Read` + `Zone → DNS → Edit` + **`Zone → Email Routing → Edit`**) and Cloudflare-touching phases open with cheap capability probes — a scope wall found in planning is one batched ask; found mid-wiring it is a stall (live-seen: Email Routing bounced back to the user because the token predated the need). A later gap = EDIT the same token (one click, no new secret).
- **Brand mailboxes (`support@`) end-to-end in ref 70:** scope probe → routing → destination → rule → DNS confirm, with the single unavoidable user click (destination verification) batched + ledgered; product mail leaves `Reply-To: support@`; contact-route smoke check added — the founder's personal inbox never appears on a live product.
- **ref 40:** new hard rule — reads MASK credential-looking strings (`Bearer …` → `***`); never retype such a line into an edit, and grep for `***` after editing credential-bearing files (a pasted mask fails at runtime). Ship receipts: the 5-line report block goes in every shipped-pass report — it is the answer to "did it deploy?".

## 0.8.1 — 2026-09-20

- **gh target trap documented** (ref 40 §6b + repo-presence README): a repo with a second remote (`upstream` = the starter) makes `gh` aim at upstream — releases and `repo edit` 404 unless `gh repo set-default <owner>/<repo>` ran once (or `-R` is passed). Live-verified; the kit already prints the set-default step.

## 0.8.0 — 2026-09-20

- **New: the repo-presence kit** — `templates/repo-presence/` + `scripts/repo_presence.py`: fill ONE JSON (facts only; our style) and the script renders README (empty sections dropped), LICENSE (proprietary notice; upstream MIT retained), `package.json` metadata, and sets the repo description + topics (`--gh`). Fails loudly on missing fields — never a half-README. 7 new tests (37 total). Nobody hand-builds a README again.
- **§6b — the release rule: a shipped change is a published change.** The change loop now ends *tag + GitHub Release* once smoke is green (SemVer judged by the user's world; ≤ 8 user-facing bullets, no internal narration; first release in an app's life = v1.0.0). Docs-only commits deploy nothing and release nothing. The **first release also runs the one-time repo-presence pass** — via the kit.
- **§4 de-mystified: "automatic via GitHub App" was wrong for our default.** A loopback-locked dashboard receives no webhooks — the push alone deploys nothing; trigger explicitly (`deploy` / REST) and confirm the newest deployment's commit. Verified against a live deployment (zero webhooks; deploys were explicit) and folded into the loop diagram + hard rule #8.

## 0.7.7 — 2026-09-20

- **`wait --expect-commit`** — the deploy wait can no longer green-light a stale build: a finished/failed deployment carrying a different commit is skipped until YOUR commit is terminal, and SUCCESS prints the commit it verified. ref 40 now binds the wait to `git rev-parse --short HEAD`. +2 tests (30 total).
- ref 10: **Step 3b marked ⏩ run-AFTER-Step-4** (it edits installer-created files) + a pointer from Step 4; Step 5 now **appends** (`>>` — no more clobbering Step 1a's provider token) and writes `VPS_SSH_HOST`/`VPS_SSH_KEY` (the tunnel auto-start keys).
- **B2 region de-hardcoded**: `b2_setup.py [region]` writes `B2_HOST`/`B2_REGION`; `coolify_backup_setup.py` reads them (default `us-east-005`).
- ref 55 / README / templates README: "both modes" claim dropped (the script is a cloud-mode mirror pull; choice ③ is the documented manual ssh recipe), `status.json` contract aligned to `{status,step,ts}`, scoped-key root-403 wording fixed, `fix-clock.cmd` shipped as a template, dangling `cf_dns_upsert` reference removed, test counts fixed.

## 0.7.6 — 2026-09-20

- **The tunnel self-heals now** (`tunnel` subcommand + deploy preflight): the dashboard is loopback-only, so a dead tunnel used to surface as a bare `10061` mid-deploy. `coolify_api.py tunnel` health-checks and — when `VPS_SSH_HOST`/`VPS_SSH_KEY` are set (vault env / config, one-time) — starts it as a **detached background ssh**; `deploy` preflights it automatically; the refused-connection message points at it. Live-proven: tunnel down after a reboot → one command → health OK.
- refs 10/40 updated; +5 tests (28 total).

## 0.7.5 — 2026-09-20

- **The home-pull hardening** (born from the first real STALE email — the watchdog caught a pull that was killed mid-run; the server side was green the whole time): `local-pull.sh` v3 — fast-fail local-S3 probe (`--contimeout/--retries`), **one** probe per run, per-step `done … (Ns)` lines + `pull OK (total Ns)`. A stopped Docker Desktop previously made the probe retry for minutes and blow an agent-tool timeout — start-only logs then made it *look* like a tigris hang (it wasn't; tigris answered in 0.3 s).
- **Windows Task Scheduler trap list** (ref 55 §7 + templates README): bash path discovery (`where bash`; System32 bash = WSL), HOME pinning, PATH for %USERPROFILE%\bin, battery conditions (`0x800710E0`), `StartWhenAvailable` catch-up, `PT1H` cap, CRLF+ASCII `.cmd` — plus the rule: **fire it once, require Last Result 0 + a fresh `pull OK`; an unverified schedule is not a backup** (the original task had a nonexistent bash path and never could have run).
- New template `run-pull.cmd`; `local-pull.sh` template → v3; counts/codes that lie documented (directory markers; scoped-key 403 `not entitled`; `provider = Other` for B2-S3).

## 0.7.4 — 2026-09-20

- **Tunnel-death trap fixed + documented** (ref 10): MSYS ssh on Windows resolves `$HOME` to `/home/<user>` → a tunnel without a durable `known_hosts` dies with "Host key verification failed", silently when backgrounded. Canonical tunnel command now carries `-o UserKnownHostsFile="$HOME/.vps-ops/ssh/known_hosts" -o StrictHostKeyChecking=yes`; symptom → cause table added (`10061/refused` = tunnel dead, not Coolify).
- `coolify_api.py`: connection-refused now prints the exact tunnel-restart command instead of a bare traceback.

## 0.7.3 — 2026-09-20

- ref 40 §2b **checkpoints** became a hard rule: milestone → verify early (typecheck, not at the end) → **commit** → continue; wide requests are passes, each shipped end-to-end; rule #7 — never end a turn with more than one milestone of uncommitted edits. Born from a real interrupted run: 27 files, one hour, zero commits, stream cut — nothing shippable. An interrupted run must leave shippable, committed work.
- ref 40 "Use when" now names the cold-start case: a project directory with `OPS.md`/`.vps-ops.json` handed over IS a deployed app — local-only is never done.

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

Every layer exercised live; the traps found are now baked in so the next run skips them:

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
