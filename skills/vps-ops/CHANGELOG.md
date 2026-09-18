# Changelog — vps-ops

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
