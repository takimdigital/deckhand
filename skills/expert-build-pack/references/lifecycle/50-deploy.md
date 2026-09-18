# 50 — Deploy: reproducible, verified, reversible

Load when: shipping to any environment, setting up pipelines, or planning a launch.

> Execution is owned by the companion skill `vps-ops` (bootstrap → Coolify → deploy → change pipeline → ops).
> This file stays conceptual: constraints, migration strategy, rollback thinking.

## Constraints (hard)

- Deploys are reproducible from a tagged commit/artifact — never hand-edited servers.
- Migrations: expand first (backward compatible), contract later (separate release).
- A rollback plan exists BEFORE risky deploys, and has been rehearsed at least once.
- Secrets live in platform env/secret stores — never in images or the repo.
- After every deploy: health check + smoke test on real state (not just "no error").

## Procedure

1. **Environment matrix.** dev / staging / prod with stated differences (parity); staging is deploy-for-real, not a demo.
2. **Pipeline stages:** install → lint/typecheck/test → build artifact → migrate → deploy → verify. Fail fast; no skip flags.
3. **Migration order:** expand (add nullable/backfill) → deploy app → contract (cleanup) in a later release.
4. **Zero-downtime pattern** for risky changes: canary (small % traffic) or blue-green; watch error rate + latency between steps.
5. **DNS/TLS/domain checklist.** Cert automation; renewal alert before expiry.
6. **Observability baseline.** Structured logs → aggregator; uptime check with alert; error tracker; one dashboard (errors, latency, key business metric).
7. **Cost guardrails.** Budget + alert thresholds on the host bill; kill switches for runaway jobs.
8. **Launch checklist.** Backups current; rollback rehearsed; status page/contact ready; DNS TTL lowered before cutover.

## Anti-patterns

- Big-bang destructive migrations; manual prod edits (snowflakes).
- "Works locally" as deploy evidence; skipping staging.
- No smoke test (deploy "succeeded", app broken).
- Secrets baked into images; silent cost growth.
- Deploy without a rollback path and without anyone watching the first minutes.

## Jargon

artifact · pipeline · canary · blue-green · rollback vs revert · expand/contract · smoke test · healthz · IaC · parity · RTO/RPO.

## Verify

- Post-deploy: smoke result recorded (command + output).
- Rollback drill log exists (date + steps + outcome).
- Alerts fire to a real channel; owner named.
- Migration ran with no lock waits / errors (check DB logs).
