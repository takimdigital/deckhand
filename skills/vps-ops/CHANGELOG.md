# Changelog — vps-ops

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
