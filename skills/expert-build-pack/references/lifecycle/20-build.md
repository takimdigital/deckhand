# 20 — Build: verified increments, not activity

Load when: implementing features, fixing bugs, or reviewing changes.

## Constraints (hard)

- **Smallest sufficient change.** No drive-by refactors inside feature work (separate PR).
- Every change ships with its verify command; a change without a check is unfinished.
- Bugfix = reproduce the bug in a test first, then fix.
- Migrations are expand/contract (backward compatible one release); never destructive in one shot.
- Side effects (payments, emails, webhooks) are idempotent; retries have backoff + a ceiling.
- New dependency = one-line justification in the PR (what it replaces).

## Procedure

1. Work in **vertical slices** (thin UI→API→DB threads), each independently shippable.
2. Write or update the check first for critical logic (money, auth, data shape).
3. Implement the smallest change that passes.
4. Run the verify command; record the result in the step record (see `formats/step-record.md`).
5. Hide incomplete work behind a **feature flag**, not a stale branch.
6. Error policy: fail closed for auth/money; fail open never; timeouts everywhere; log with context.
7. Keep PRs reviewable (heuristic: ≤400 changed lines; split if bigger).

## Anti-patterns

- Horizontal building ("all the DB, then all the API, then all the UI") — nothing is testable until the end.
- God files/components; premature abstraction; copy-paste forks.
- Unbounded retries; silent catch blocks; disabling a failing test to "unblock".
- TODO comments as promises (must carry an issue link or die).
- Testing only the happy path on moneymaking flows.

## Jargon

vertical slice · feature flag · expand/contract migration · idempotency key · exponential backoff · N+1 query · god object · YAGNI · regression test · smoke test.

## Verify

- Each slice demonstrably runnable end-to-end (evidence: command + result).
- Changed behavior covered by checks; suite green.
- No unlinked TODOs in changed files; PR within size heuristic.
