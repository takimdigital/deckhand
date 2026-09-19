# 10 — Foundations: the decisions everything after inherits

Load when: starting a codebase, choosing a stack, or setting repo conventions.

## Constraints (hard)

- Stack decisions are recorded (ADR-style) with reasons and rejected alternatives BEFORE code.
- Secrets never enter the repo (`.env` git-ignored; `.env.example` maintained).
- One package manager; one language across the stack unless there is a recorded reason.
- Binding docs at repo root: AGENTS.md (agent/contributor rules), DESIGN.md (tokens/UX), README quickstart.
- Fresh clone → running app in ≤10 minutes (target), verified by actually doing it.

## Procedure

1. **Stack decision record.** Framework, database, host, auth. Bias: boring, popular, one community. Rejected alternatives listed with why.
2. **Repo scaffold.** Monorepo vs polyrepo decided; folder layout; naming conventions; license.
3. **Binding docs.** AGENTS.md: how agents/contributors must work here (verification commands, style). DESIGN.md: tokens + UX rules. README: quickstart.
4. **Environment.** `.env.example`, local setup script, dev/prod parity notes, secrets policy.
5. **Data model v0.** Entities + relations sketched; migration tooling chosen; naming convention for tables/columns.
6. **CI minimal.** Lint + typecheck + tests on every PR — before features, not after.
7. **Walking skeleton.** Thinnest end-to-end slice (UI → API → DB) deployed to staging. Deploy early; it flushes out infra pain while cheap.
8. **Observability baseline.** Structured logs, error tracking, one health endpoint.

## Anti-patterns

- "We'll add tests/CI later" (later never comes; the debt compounds).
- Stack chosen for novelty or resume value.
- Secrets in code, config sprawl, undocumented setup ("works on my machine").
- Shared "utils" packages before there is a second real use case.
- No ADR → decisions relitigated every month.

## Jargon

ADR · walking skeleton · parity (dev/staging/prod) · migrations vs seeds · monorepo/polyrepo · CI gate · least privilege (secrets) · trunk.

## Verify

- Fresh clone run-through completed using only the README (time it).
- CI green on main; branch protection on.
- Staging URL serves the walking skeleton.
- ≥1 ADR committed; `.env.example` current.
