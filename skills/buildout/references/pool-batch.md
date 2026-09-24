# Pool batches — the owner sent repos, add them to the registry

**Trigger:** the owner (or anyone) pastes one or more GitHub repos that should join the pool. They
found them; we measure them — remotely, and the pool learns.

## The rule this file exists for

**One batch = AT MOST 3 measuring subagents, whatever the repo count.** Never one agent per repo: with
8 repos that was 8 agents doing 8 tiny jobs; the owner's rule (and the sane one) is 3 agents carrying
slices of the list. `pool_batch.py plan` does the slicing and prints the three delegations ready to
paste — do not hand-write them.

## Flow

```
1  save the owner's message verbatim -> data/details-inbox/<batch>/repos.txt   (one repo per line)
2  py scripts/pool_batch.py plan --file <that file>            # validates, slices, prints the delegations
3  delegate_task with the printed blocks (1..3 tasks)          # children measure remotely, write files
4  py scripts/pool_batch.py check <batch>                      # every file valid? repo in the registry?
5  py scripts/pool_batch.py import <batch>                     # folds them in; the registry is truth
6  report: new rows, refreshed rows, blockers — with their evidence
```

`plan` writes `data/details-inbox/<batch>/{repos.txt,batch.json}` and the children write
`data/details-inbox/<batch>/files/<slug>.json`. That inbox is scratch (gitignored) — the durable copy
is `data/details/` plus the row, which `import` writes.

## What the children are told (printed by `plan` — keep it that way)

- one JSON file per repo, schema = `references/pool-details-contract.md`; write each file as soon as
  its repo is done, never at the end;
- **remote only** — `gh api` / raw.githubusercontent; never clone, install or execute anything;
- env vars **by NAME only** (a credential-shaped value gets the file rejected);
- every non-obvious fact carries `evidence`; the only use-stopping claim is `blocking[]`, carrying
  `kind` (`injected-payload` | `install-impossible`), `why`, `evidence`;
- they are ONE of ≤3 agents: no further agents, no repos outside their slice.

## Before import

- **A repo not in the registry cannot receive details** — the importer refuses it by design. `plan`
  lists the exact `template_intake.py --repo <owner/name>` commands for the new ones; run them first
  (remote, no clone), then `check` → `import`.
- `check` is the gate: it names `MISSING` (never written), `INVALID` (contract/secret errors) and
  `NO ROW` per repo, and exits 3 unless every row is ready. Fix or re-task the named files — do not
  import around it.
- A repo already in the registry is simply **refreshed** (`details_at` moves; the detail-derived
  blockers are merged, never erased).

## Pitfalls

- **Don't re-run `plan` after the children started** — a second plan makes a second batch folder and
  the two drift apart. The batch id is printed; use it for `check`/`import`.
- **Don't let a child widen its slice** ("while I was there I also measured…") — that file belongs to
  another slice and will be overwritten by whichever agent writes second.
- **`check` also guards the skill root**: `plan` snapshots it and `check` fails with `STRAY` if any
  file appeared since (children have dropped scratch JSONs into the shipped tree before). Delete the
  named files — or say why they belong — before importing.
- **After a batch ships, diff the pack's file list against the previous release** (`unzip -l`), not
  just the tests: that diff is what caught the stray files, and no test can see the whole artifact.
- **Big lists**: keep 3 agents and run a second batch — never 6 agents "just for this one".
- A batch is not a match: importing details never ranks, clones or deploys anything.
