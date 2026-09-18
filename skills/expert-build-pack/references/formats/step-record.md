# Step Record — the atomic unit of execution

Load when: planning/reporting multi-step work, writing any prompt that another agent will execute, or touching risky/consequential actions.

A step record represents work from the perspective of the actor who must execute it. It is executable precision, not verbosity — expose states, actions, and checks that actually matter.

## Template

```
CURRENT STATE:  what is true right now + how it was verified (or UNVERIFIED)
ACTION:         exact tool/command + path + arguments (no prose descriptions)
EXPECTED:       observable, testable post-condition (a thing you could assert)
VERIFY:         the specific check that proves EXPECTED
                (strongest source first: API/DB > operation ID > durable artifact > UI/transient)
NEXT / RECOVER: branch on mismatch. Ambiguous outcome -> record UNKNOWN_EFFECT and re-observe.
                Never blind-retry a consequential action.
```

## Rules

1. **Fresh-state precondition.** Never act on state that may have changed since observed (identity, amount, destination, auth, environment). Re-observe before consequential actions.
2. **Bigger action units are fine; unverified ones are not.** Multi-action batches or generated code are allowed — but no batch is atomic: gate each consequential member and re-observe after it.
3. **One verify per action; verify by reading back real state** — run the test, read the file, re-query the API. A success banner is weak evidence about business state.
4. **Granularity is task-dependent.** Split further when steps are risky, uncertain, or state-dependent; collapse micro-steps that can't fail meaningfully. ("Move cursor 2cm" — no. "Open Settings → Integrations; verify the panel is visible" — yes.)
5. **Boundary block.** For any delegated unit, state: what one step covers, scope in/out, and the completeness criterion (what counts as done). Default failure bias is *under-action* — agents systematically underestimate completeness; explicit boundaries measurably raise success.

## Example

```
CURRENT STATE:  repo clean @ a1b2c3 (verified: git status), CI green (verified: run #482)
ACTION:         apply migration 0042_users_email_idx via `pnpm db:migrate`
EXPECTED:       migration applied; users.email_idx present; app starts
VERIFY:         `pnpm db:migrate` exit 0; query pg_indexes shows email_idx; smoke: GET /healthz 200
NEXT:           run test suite. RECOVER: if index exists but app fails, re-read logs; do NOT rerun migration blindly.
```

## Anti-patterns

- Narrative steps ("configure the database") with no command, no expected state, no check.
- Verification by assumption ("it should work") or by the agent's own summary.
- Retrying a side-effecting action after an ambiguous timeout without checking what actually happened first.
- Certainty incantations ("be absolutely sure") — measured cost, null gain; use a concrete VERIFY instead.
