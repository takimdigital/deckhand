# Changelog

## 2026-09-19 — first live deployment (vps-ops v0.2.2)

CitiQuiz went live on a real VPS: Contabo Cloud VPS 4 → Coolify 4.3.23 → https://sidehustlepaths.com
(Cloudflare DNS + Let's Encrypt). Every fix below is live-verified and folded into `vps-ops` v0.2.2:

- ref 10: new **Step 3b** — host firewalls do NOT block Docker-29 published ports; lock the Coolify
  dashboard by loopback-binding 8000/6001/6002 in its compose (+ re-apply after Coolify upgrades).
  Tunnel note (forward 8000 only on Windows) and the `1|…` token single-quoting trap.
- ref 12: Contabo live notes (order email, no cloud firewall, SSH key-install flow, 4 vCPU/8 GB sizing).
- ref 30: pre-flight repo traps (`packageManager` pin + valid `pnpm-workspace.yaml`), Postgres
  `start` recovery, new §6b — container-side migrate / seed / production-owner flow.
- First build failure fixed in the app repo: invalid `pnpm-workspace.yaml` + missing pnpm pin
  (`packages field missing or empty`) → citiquiz `778296e`.
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
