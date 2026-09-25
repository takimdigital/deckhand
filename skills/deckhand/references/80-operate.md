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

## The learning loop (autopsy)
- Every failing command runs through `dh run -- …`; known signatures print their fix instantly.
- After fixing a new failure: `dh learn from-failure --fix "…" --cause "…" [--rung preflight|gate|eliminate]`.
- `dh learn promote` turns lessons seen twice into patch proposals for this skill (fix ladder: eliminate the
  wrong path > pre-flight check > reorder > gate > pitfall line). Apply with the owner's OK, add a test when
  it is a script change, bump `CHANGELOG.md`. Pitfall lines are debt, not solutions.

## Reuse
Owner likes the result → `dh harvest --name <base> [--repo owner/name]` (private by default): the project
becomes a base in the personal pool, brand-neutralised, with a manifest; `dh pool query` ranks it first
when it fits. Kept sections can also be saved one by one from the try-on panel (**Save to my library**).
