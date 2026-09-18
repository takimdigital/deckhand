# 60 — Maintain: runbooks, drills, and drift control

Load when: operating a live product, handling incidents, or scheduling maintenance.

> Day-2 execution is owned by the companion skill `vps-ops` (`50-ops-monitoring.md`: status, logs, metrics,
> backups, updates, incidents). This file stays conceptual.

## Constraints (hard)

- Every critical flow has a written runbook (rollback, DB down, cert expiry, provider outage).
- An UNTESTED backup is not a backup — restore drills on a schedule, with a timestamped record.
- Incidents get blameless postmortems with concrete actions (owner + date).
- Security patches: critical ≤ 72h, high ≤ 1 week, routine monthly cycle.
- Traffic-critical alerts have named owners; unowned alerts get deleted.

## Procedure

1. **Runbook index.** Top 5 failure scenarios, each: symptom → first check → mitigation → escalation.
2. **Incident flow.** Detect → mitigate (stop the bleeding first) → communicate (status page/affected users) → postmortem within a week → actions tracked.
3. **Dependency cadence.** Automated patch/minor updates reviewed weekly; majors reviewed monthly with a rollback plan. Never freeze for a year.
4. **SLOs from SLIs.** Pick 1–3 user-visible signals (availability, latency, task success); set SLO + error budget; when the budget burns, reliability work preempts features.
5. **Drills.** Restore drill per quarter (pick a backup, restore it, verify data); rollback drill after any pipeline change.
6. **Tech-debt budget.** ~10–20% of capacity reserved; logged as items, not vibes.
7. **Deprecation policy.** Announce window → mark deprecated in code → remove on schedule.
8. **Monthly review.** Costs, capacity, top errors, dependency drift, alert noise.

## Anti-patterns

- Hero-mode fixes with no postmortem; repeat incidents.
- Backup theater ("we have snapshots" — never restored).
- Alerts nobody owns; alert fatigue muting.
- Dependency freeze → giant scary upgrade.
- Silent deprecations breaking downstream users.

## Jargon

runbook · postmortem (blameless) · SLI/SLO/SLA · error budget · RTO/RPO · dependency drift · deprecation window · on-call.

## Verify

- Restore drill done this quarter (timestamp + result).
- Runbook index exists; each top scenario has one.
- Every alert has an owner; patch SLA met last cycle.
- Error budget status visible on the dashboard.
