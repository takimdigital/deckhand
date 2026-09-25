# Field tests — how to test Deckhand itself with a team of agents

For the maintainer (and anyone improving the skill), not for building a business: `references/team.md` is the
builder's side. This keeps the useful part of the "subagent team simulation" procedure (learned by a Hermes agent over
many runs) inside the repo, so no separate harness skill is needed.

## A run in five moves

1. **Rails** — use Deckhand's own: `CONVENTIONS.md` as the protocol, `dh bb post|read` as the board, `dh bb flag|wait`
   as flags. Rails check before the first dispatch (a flag that must be found, one that must time out).
2. **Cast** one sub-agent per human-felt role: CLIENT (writes the brief in its own messy voice + an "I can…" acceptance
   checklist, then uses the RUNNING app at phone width and answers its own checklist, saying what it cannot judge),
   PM (maps every acceptance item to one exact proof), BUILD (sole writer of its packages), DSGN (design layer + a
   bans list with reasons), QA (runs the definition-of-done row by row: command + observed evidence; a durability proof
   for anything that changes state — restart, re-read), SCOUT (external research with raw evidence files), AUDIT.
3. **Harvest frictions** — every role logs `F-NN | file:line | "exact quote" | what a first-timer does wrong | H/M/L`
   in its own file; a checker script verifies every quote exists at its line. AUDIT merges one entry per root cause
   (two reporters = one entry citing both), classified product-fixable vs simulation artifact, ≥ 80 % of quotes
   re-verified mechanically.
4. **Verdict** — a standalone document: the journey phase by phase (where the docs guided, misled, silently failed),
   the fix batch in ≤ 6 groups, each fix at the strongest rung (eliminate → pre-flight → reorder → gate → pitfall), a
   keep-list of what worked. Nothing under test is edited mid-run.
5. **Fix batch** — each friction maps to exactly one edit location; ship it with a regression test; re-verify that a
   representative friction is now impossible or caught earlier.

## Re-testing a fixed version (pre-registered)

- Close the protocol before any build work and commit it: held constants (case, checklist, rubric, models, tool list,
  budget caps), the ONE variable (the version), falsifiable hypotheses with numeric thresholds, the primary metric, an
  append-only deviations log. k = 1 is a case study: no significance claims.
- A sealed held-out set (~40 %), never derived from anything the fix loop touched; report SEEN vs HELD-OUT apart.
- One blind registrar/grader that never builds; anything ranked arrives anonymised.
- Contamination fence: a fresh folder and git repo; builders never read the previous run.
- A finding counts with an anchor (command / `file:line`) AND an independent reproduction → verified; anchor only →
  claimed; neither → unverified. Report the three counts; tag every headline claim MEASURED or ASSERTED.
- Re-run the previous version's friction classes as a regression table: held / recurred / not-observed (not a pass).
- Timings come from the orchestration layer, never from roles' own clocks.
- Deliverables, stable across runs: `protocol.md` · `scorecard.md` · `friction.md` (IDs continue) · `verdict.md` ·
  `ledger.md` · `limitations.md`. Never two files that differ only by case (`protocol.md` vs `PROTOCOL.md` collide on
  Windows).

## Two equal leads (when one opinion must not decide)

Two orchestrators, identical inputs, different mandates (e.g. trust-first vs character-led). They compete on cheap
artifacts only (documents, decisions — never two full builds). Every disagreement becomes a NAMED fork (question,
options, evidence) with a recorded resolution; an irreconcilable fork goes to the owner as a plain two-option
question. After the merge one lead chairs execution, the other owns independent verification.

## The verifier's obligations

- Re-run a claimed pass yourself: exit code AND output (a script that prints usage and exits 0 is a failure).
- Positive and negative controls for every query or gate; a gate that cannot fail is not a gate. A must-pass control
  should carry near-miss wording, so a substring gate that punishes honest prose is caught.
- "Rebuilt green" does not prove the original was untouched: check its mtimes and `git status --porcelain`.
- Keep the receipts (probe scripts, raw evidence) next to the verdict.

## Feeding it back

`dh autopsy --workflow` on each session gives the owner-facing proposals and a maintainer report
(`.deckhand/autopsy/W-….maintainer.md`); the maintainer report is what comes back to the Deckhand repo as issues or PRs.
