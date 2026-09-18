# Changelog — vps-ops

## 0.2.2 — 2026-09-19

Live drill: CitiQuiz deployed on Contabo Cloud VPS 4 → https://sidehustlepaths.com (Coolify 4.3.23,
Let's Encrypt, 2,417-question bank seeded, production owner created, dev seed account removed).
Every fix below is live-verified:

- ref 10: new **Step 3b** — lock the dashboard by loopback-binding 8000/6001/6002 in Coolify's
  compose (host iptables does NOT block Docker-29 published ports — 0 packets, traffic still flowed);
  tunnel note (Windows: forward 8000 only — 6001/6002 hit reserved ranges and kill the tunnel);
  token-must-be-single-quoted note (`1|…` breaks unquoted env files with `Unauthenticated.`).
- ref 12: Contabo live notes — order-email contents, no cloud firewall, SSH_ASKPASS key-install flow,
  4 vCPU / 8 GB sizing confirmed for the full stack.
- ref 30: deploy-blocking repo traps (pnpm `packageManager` pin; invalid `pnpm-workspace.yaml` →
  `packages field missing or empty`), Postgres `start` recovery for a never-materialized container,
  new **§6b** container-side migrate / seed / production-owner flow.

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
