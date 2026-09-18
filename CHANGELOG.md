# Changelog

## 2026-09-17 — live validation pass

- `vps-ops` v0.1.0: full live drill on a real Coolify instance — deploy (image / public repo / private repo), change pipeline, rollback, Postgres provision + query, backups + restore, Dockerfile build pack. 23 tests.
- Fixed from the live drill: deployments API response shape + `finished` status, `envset` HTTP 201, rollback requires the full 40-char image tag, database `initdb` false-unhealthy window, custom-format dumps, database container naming.
- `expert-build-pack` v0.2.1: Buildout Engine hardened. Registry pool 372 → 282 healthy; catalogs velora 64 / reui 1,773 / cult-ui 157. 9 tests.
- `component-library` v0.1.0: save / load components. 4 tests.

## 0.2.0

- Buildout Engine: living MIT registry pool, coherent-random design assembly, design token locking, `component-library` companion skill.

## 0.1.0

- Initial release: expert references, execution-first loops, machine-first handoffs.
