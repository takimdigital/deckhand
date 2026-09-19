# Verify Ladder — how much a piece of evidence is worth

Load when: claiming something works, accepting someone else's claim, or designing checks for a step/subagent.

The reliability of a check depends on how close it sits to real state. Verification accelerates reasoning; only reality establishes truth.

## Ladder (strongest first)

| Level | Source | Example | Weight |
|---|---|---|---|
| 1 | Authoritative system of record | DB query, API read-back, `pg_indexes`, provider dashboard | Evidence |
| 2 | External operation identifier | webhook id, deployment id, CI run number, payment intent id | Strong |
| 3 | Durable artifact | file on disk, build artifact, test report, git commit | Medium |
| 4 | Transient feedback | success toast/banner, spinner gone, agent's own summary | Weak — never sole proof |

Rule: verify at the strongest level the task can afford, and read back *your own* effect (not just "no error"). "Do not treat done as proof: a button click is not proof a form was accepted."

## Verdicts (three-state, no silent defaults)

- `CONFIRMED` — the check ran and passed (record the exact command + result).
- `REFUTED` — the check ran and failed (record evidence; do not re-claim).
- `ABSTAINED` — the check could not run (crash, timeout, missing access). An abstention is NOT a pass and NOT a fail: retry or escalate; never count it as either.

## Ambiguity

If the outcome of an action is unknown (timeout on a side effect), record `UNKNOWN_EFFECT`, re-observe real state first, then decide. Idempotency keys exist exactly for this: check, don't blind-retry.

## Self-verification rules (measured failure modes)

- A maker cannot certify its own work: self-written tests can *lower* outcomes (weak tests dragged resolved rate from 61.2% to 57.3% in one study); independent tests from a separate role raised it to 65.3%.
- Do not trust self-assessed progress: in a pre-registered test, 56% of self-reported "improvements" measured ≤0, and the strongest in-band judge still accepted 44% regressions.
- Beware packaging: polished evidence panels (even fabricated) lift over-commitment on unknowable questions from 6.5% to 54%. Strip authority cues; demand provenance.
- Soundness beats effort: an unsound verifier gets WORSE as you scale attempts. Never scale retries past the point where the verifier is trustworthy.

## Tag survival

Truth tags must survive every handoff and every compaction. After any summarization/compression step, re-check: if a caveat detached from its claim, restore it as structured state (a tag field), not prose — prose caveats measurably fail to restore caution.
