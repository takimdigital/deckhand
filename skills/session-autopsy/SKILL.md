---
name: session-autopsy
description: "Use when a session failed — fix the instruction itself."
version: 0.1.3
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [autopsy, postmortem, failure, retro, hardening, root-cause, skill-maintenance]
    related_skills: [skill-pack-publishing, systematic-debugging]
---

# session-autopsy — failure → instruction fix

A task went red → green (deploy failed, CI broke, several retries until success). This skill converts
that failure into an edit that makes the wrong path unenterable for the next agent. The deliverable is
an edited instruction, verified — never "a lesson learned".

## When to use

- "Learn from this session / why did it fail / fix the skill so this can't happen again."
- **The phrase that always works, said in the session that went wrong: "run session-autopsy"** — that session can grep its own transcript for the errors; no extra input is needed to start (evidence-gathering is the skill's own phase 1). From ANOTHER session (or later): pass the session ID (it is read via `session_search`) or paste the key errors + what finally worked — evidence is required, the whole log is not.
- Standing rule: any pipeline task that needed a retry — run the autopsy before closing it.
- Not for: the app itself being broken (`systematic-debugging`), publishing mechanics (`skill-pack-publishing`), missing knowledge (the buildout update-loop).

## Token discipline (hard rules)

- Never read a full transcript end-to-end — grep for error strings and the fix commit (ref 10 §2–3); open a raw-transcript slice only when ref 10 §1 says the targeted greps came up ambiguous.
- Load only the ref the current phase names (10 → 20 → 30, one at a time — three max per autopsy); report ≤ 40 lines; interview = one batch of ≤ 6 questions.
- Chat output = the report only (symptom → cause → fix → proof). No narration of the process.

## Phases — in order, no skipping

1. **Evidence** (ref 10): first symptom, verbatim errors (grep-able), attempts, what fixed it.
2. **Cause-chain**: why → why → why; stop at the first layer YOU control (instruction · precondition · default · script).
3. **Locate the instruction**: quote the exact step the agent read. Say how a first-time reader goes wrong there (ambiguous / wrong order / missing check). No skill involved → classify + route (ref 10 §5). No-edit outcomes (env quirk / app defect / one-off) skip phases 5–6's version bump — for them the report + recorded debt ARE the deliverable.
4. **Fix ladder** (ref 20), strongest reachable rung:
   1. Eliminate — script/template/default makes the wrong path impossible.
   2. Pre-flight — check before the point of no return.
   3. Reorder/rewrite — correct path becomes the path.
   4. Gate — loud failure exactly at the mistake.
   5. Pitfall — ONLY non-designable environment quirks; entry says where the net is; counts as debt.
5. **Write the fix** (ref 30): at the step where the agent ACTS; imperative; verbatim error strings; one rule per lesson; bump the target skill's version + CHANGELOG.
6. **Verify**: replay the failure against the new text; mechanical check when possible (fails on old state, passes on new).
7. **Publish + report**: sync/zip/release per `skill-pack-publishing` (when present); report via `templates/autopsy-report.md`.

## Boundaries

- App broken → `systematic-debugging`. Instructions let the agent go wrong → here.
- App-specific facts (ids, seeds, owner) stay in the app repo (`OPS.md`), never in pack skills.
- Optional paths stay optional: a fix must not force a variant the user didn't choose.
