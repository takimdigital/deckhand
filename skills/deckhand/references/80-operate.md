# 80 — OPERATE (the business keeps running; the pack keeps learning)

## Change requests (any time after deploy)
`OPS.md` / `.deckhand/deploy.json` present ⇒ this is a live app: edit → `dh verify` → commit (conventional
message) → `dh deploy ship` → report with the smoke evidence. Content/design changes may use try-on first.
Never edit production directly; never "quick fix" on the server.

## Bots and crons
`dh ops suggest` ranks bots for this business (shape, features, deployed?). Install the top ones the owner
approves: `dh ops add <id> --runner github` (free Actions cron, state cached) or `--runner cron` (on the VPS).
Generic bots are real scripts (`watchdog`: uptime, TLS expiry, container health, backup age, disk;
`link-audit`: 404s + SEO basics; `backup-proof`; `deps-audit`). App bots (`weekly-kpi`, `lead-digest`,
`abandoned-signup`, `payment-failed`, `booking-reminder`, `review-request`, `low-stock`) ship as a spec +
skeleton: implement against THIS app's tables with a read-only DB user, idempotent, one message.
A schedule is live only after it fired once through its own trigger (the output prints the command).

## The learning loop (autopsy — deterministic, evidence only)
- Risky commands run through `dh run -- …`: every run (and every `dh` call) lands in `.deckhand/runs.jsonl`;
  a known signature prints its proven fix at once; `dh run --fix -- …` replays a recipe made only of safe,
  repeatable steps (installs, cache clears, codegen) and retries once.
- After a session (or a hard one): `dh autopsy [transcript.jsonl | --latest]` → `.deckhand/autopsy/<id>.md`.
  No model reads the log: failures (including those a `| tail` hid), their retries, **the recipe that
  actually fixed each one** (the edits and state-changing commands between the last failed attempt and the
  success), the owner (skill · environment · project), the fix-ladder rung the evidence supports, recurring
  signatures, blind retries, tool errors, and the workflows that finished a phase. Same session → same bytes.
- `dh autopsy … --apply` writes: lessons with recipes (global ledger — every future project gets them in
  `dh next` and `dh run`), skill-fix proposals in `~/.deckhand/autopsy/proposals/` (repro + the fix that
  worked + whether a regression test exists), and playbooks (a phase's working steps; after two sessions
  `dh next` shows them as `worked_before`). It never edits the skill: a person or a reviewed PR applies a
  proposal, with its regression test, and bumps `CHANGELOG.md`.
- `dh learn from-failure` / `dh learn promote` remain for a single fix recorded by hand.

## Reuse
Owner likes the result → `dh harvest --name <base> [--repo owner/name]` (private by default): the project
becomes a base in the personal pool, brand-neutralised, with a manifest; `dh pool query` ranks it first
when it fits. Kept sections can also be saved one by one from the try-on panel (**Save to my library**).
