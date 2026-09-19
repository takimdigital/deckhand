# 30 — Writing the fix (so the next agent can't miss it)

**Purpose:** the edit itself — placement, wording, versioning. Publishing = `skill-pack-publishing`.

## Placement

- Put it where the agent ACTS: the pre-flight / step block that runs BEFORE the failure point.
- Same file the failing agent actually read — check the skill's routing table path.

## Wording

- Imperative, one rule per lesson, trigger first:
  `**Before X, do Y** — <wrong thing> fails with \`<verbatim error>\` (live-verified <date>).`
- Carry the verbatim error string — grep-able, so the next agent recognizes the state instantly.
- No "be careful", no "remember to", no rationale essays. Yes: exact commands, canonical order, expected output, what the broken state looks like.

## Versioning + records

- Target skill: bump `version:`, add a CHANGELOG entry (symptom → fix, product-level — no project names).
- Additive: new steps/refs; existing refs get at most one cross-link line.
- Pack release: per `skill-pack-publishing` step 8.

## Verify before publish

- Replay: a fresh reader at the edit's location walks right — state the one-line argument in the report.
- Mechanical when possible: a grep or test that FAILS on the old state, passes on the new.
