# Handoff Envelope — machine-first state transfer

Load when: delegating to subagents, resuming after compaction, ending a session with work in flight, or writing a status for another agent/human to continue from.

Optimize for the NEXT reader, not for readability. A transcript is never a handoff. Measured: structured-notes handoffs cut successor work by 20–59% of agent events and 42–63% of prompt tokens versus repo-only takeover (arXiv:2606.02875).

## Envelope template

```
GOAL:               one sentence; the outcome, not the activity
CONSTRAINTS:        pinned VERBATIM (security, legal, must/must-not); never summarized
KNOWN FACTS:        each with truth tag + evidence pointer (path/URL/command output)
DECISIONS:          choice + rejected alternatives + reason
DEPENDENCIES:       what depends on what; external parties/systems
EVIDENCE POINTERS:  paths/URLs/artifact ids — reference them, never copy transcripts
FAILURES:           what was tried, why it failed (do not re-attempt blindly)
UNRESOLVED:         open questions, unknowns, UNKNOWN_EFFECT situations
NEXT ACTION:        the single next step (executable)
COMPLETION:         what proves the task is actually finished
TERMINAL STATE:     success | no-op | blocked | stalled | exhausted
BUDGET:             remaining iterations/tokens/time — error or exhausted budget NEVER counts as success
```

Truth tags: `VERIFIED` (checked against an authoritative source; pointer attached) · `INFERRED` (consistent but unconfirmed) · `UNVERIFIED` (claimed, not checked) · `OBSOLETE` (superseded). Keep tags attached to their claims — compression strips bare caveats; re-check tag survival after any summarization (measured: dropping an "unverified" marker raises risky approvals from 5% to 60–98%).

## Rules

1. **Reference, don't copy.** Envelopes stay O(1) in size: artifacts by path/URL; the raw trace stays in an episodic store.
2. **Minimum sufficient context per recipient.** Subagents get only what their assignment needs — extra context degrades quality (and can silently switch the task).
3. **Typed return.** The return is the same envelope, inverted: status (terminal state), artifacts produced, evidence, failures, unresolved, next action. Cap at ~300 words unless asked otherwise.
4. **Constraints verbatim.** Pin them word-for-word (~47 tokens was enough to restore zero violations in the measured study); never paraphrase mid-flight.
5. **Idempotency.** For external side effects include the idempotency key / operation ID so a successor can check instead of retrying.

## Compact example

```
GOAL: ship email-index migration to prod without downtime
CONSTRAINTS (verbatim): "No destructive schema changes in business hours"; "zero-downtime required"
FACTS: migration 0042 written [VERIFIED: branch + local run]; staging applied OK [VERIFIED: run #483 green]
DECISION: expand/contract chosen, rejected single-shot ALTER (lock risk)
FAILURES: first attempt used CREATE INDEX (locking) — reverted; redo as CONCURRENTLY
UNRESOLVED: prod index size estimate unknown
NEXT ACTION: open PR for 0042_concurrent, link run #483
COMPLETION: index present in prod post-deploy + /healthz green + no lock waits in logs
TERMINAL STATE: success  BUDGET: 1 session
```

## Anti-patterns

- Pasting chat history or raw logs into a brief (linear bloat, injection carrier, "game of telephone").
- Constraints buried in prose or reworded "for clarity".
- Returns that are full reasoning dumps — or bare "done".
- Treating "exhausted/errored" runs as completed work.
