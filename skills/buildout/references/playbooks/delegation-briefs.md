# Delegation Briefs — minimum sufficient context, typed returns

Load when: about to delegate work to a subagent/parallel agent, or writing a prompt another agent will execute.

In 2026 the reason to split work is **compression and isolation**, not parallelism: the worker absorbs raw material so the orchestrator never has to carry it.

## The brief contract (what every brief contains)

```
GOAL:            outcome, one sentence
CONTEXT:         minimum sufficient — exact file paths, error text, prior decisions (pinned), NOT transcripts
IDENTIFIERS:     exact names: files, symbols, APIs, commands, branch, env
CONSTRAINTS:     pinned verbatim; state what must NOT change
OUTPUT SCHEMA:   what the return looks like (fields, format)
STOP CONDITION:  completion criterion + budget ceiling + ambiguity clause
BUDGET:          iterations / time / tokens
```

Bad: "Improve the auth flow." → Good: "Add refresh-token rotation to `src/auth/service.ts` (current: single long-lived JWT, see DECISIONS.md §auth). Constraints (verbatim): 'sessions must survive deploy'. Output: PR + step-record + test evidence. Stop when: rotation tests green; budget 1 session; if spec ambiguous, inspect repo evidence before deciding."

## The return contract

```
STATUS:      terminal state (success | no-op | blocked | stalled | exhausted)
ARTIFACTS:   paths/URLs produced
EVIDENCE:    exact verify commands + results (not claims)
FAILURES:    tried + failed, why
UNRESOLVED:  open questions / UNKNOWN_EFFECT
NEXT ACTION: single next step
```

Cap length (~300 words) unless the assignment says otherwise. Error or exhausted budget is never reported as success.

## Context mode (fresh vs fork)

- **Fresh window (default)** for workers, explorers, verifiers — starts cheap (~30k tokens); isolation prevents cross-contamination and task drift.
- **Fork (full/last-N history)** only for memory/continuation agents that must know the conversation; starting cost measured at 300k–500k tokens — use deliberately.
- **Verifier gets ZERO shared context with the maker** — a clean-context reviewer catches more (measured: ~2 bugs/PR, ~58% severe).

## Write discipline

- **One writer per artifact.** Fan out reads/checks, never concurrent writes to the same target; partition by file ownership when parallel (worktrees for code).
- Structured disagreement beats consensus: prompt verifiers to object explicitly; silent agreement hides errors.
- Reference artifacts by path — never paste them into the brief.

## Failure modes to design against

| Mode | Symptom | Fix |
|---|---|---|
| Stale-state trust | acting on a progress note from an earlier step | re-verify state first (verify ladder) |
| Game of telephone | details degrade through the coordinator | typed returns; artifacts by reference |
| False consensus | several agents agree wrongly | explicit disagreement prompts; clean-context verifier |
| Token blowup | parallel children multiply cost | cap fan-out; per-unit budget; fresh windows |
| Unmerged writes | parallel writers on same files | one writer per artifact; ownership split |
