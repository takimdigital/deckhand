# 45 — The Map (consume it; the build's contract)

Load: at project start (after intake / boilerplate decision) whenever the project has a `map/` directory — and again at verify time, because the map is the row source for acceptance tests.

**Why the map exists (field-test lesson):** all three defects that every mechanical gate missed were three blank map cells — an error state nobody rendered, a footer link to a page that never existed, a builder note printed as client copy. The map is the spec of what WILL exist; the build consumes it instead of re-deriving scope from chat.

## What it is / who owns it

One schema, two directions: **audit mode** (existing site — companion skill `conversion-audit`, refs 02/03) · **spec mode** (greenfield / rebuild — ref 11, future tense). buildout CONSUMES the map; `conversion-audit` OWNS the schema — never redefine map fields here. No companion installed → no spec map gets authored (hand-written maps following the layout below still gate identically); builds without a map behave exactly as before.

Layout at the project root: `map/{summary.md, inventory.md, charters/<id>.md, flows/<flow_type>.md, edges/<flow_type>.md}`; `depth: lean|full` in summary's first lines sets the completeness bar (ref 11).

## What the build reads from it (and only this)

| Map piece | The build decision it settles |
|---|---|
| inventory + charters | build scope + order — one section per charter in smallest-useful order; nothing not in the inventory gets built, nothing in it gets skipped silently |
| charter `step_sequence` / `user_state_per_step` | the states each screen must actually render (the error state is the one nobody builds) |
| `edges/<flow>.md` | required per-screen states + behaviors across the 11 categories — every `Y` row is an implementation with its own render/behavior check |
| `flows/*.md` `exit_points` | link targets — every exit lands somewhere (zero dead-ends) |
| charter `next_action` | every screen's next step is wired |
| summary.md Open questions | PENDING.md items or an explicit recorded default — never a silent guess |

## The freeze gate (run BEFORE the lock freezes)

`py <buildout>/scripts/map_check.py --map map` — **run it FROM THE PROJECT ROOT** (both paths are project-relative; the script lives in the skill, so pass its path — from the skill's own dir, `--map map` finds nothing and the arm skips silently). Depth-aware (lean = 6 core edge categories, full = all 11), requires `map_version`, and fails on unresolved markers (`<...>` anywhere in the map — summary included — plus `[STATUS]`, `FILL_ME`, TBD/TODO/FIXME). A FAIL refuses the freeze: fix the map, not the gate. **No map dir → the check prints SKIP, exit 0 — the stage is skipped silently, exactly like builds that never had a map (graceful, never mandatory).** The gate is demonstrated to fail on known-bad input — `tests/test_map_check.py`: every rule carries its own known-bad fixture (silent blank, dead-end, count mismatch, placeholder, FILL_ME marker, merged flows, missing source, missing depth, missing `map_version`, TBD marker, …) — and both arms pass on the shipped fixtures from the skill's own dir: `py scripts/map_check.py --map tests/fixtures/map-lean --direction tests/fixtures/freeze-project/direction`. On a PASS it also prints the **`ADD` row count** (checks the map adds beyond the brief) — every one must become an acceptance row at verify (`40-verify-the-product.md` §1).

Freeze = map + `.design/design.lock.json` (a hidden directory — plain `ls` won't show it; `ls -la` will) + the ownership table (who writes what). After freeze, changes go through the change path, never silent drift. The same script's `--direction` arm checks the direction-stage artifacts + the merged lock's format the same way (skip-graceful when no competition ran).

## Working rules during build

- **The map is default state:** when a build discovery changes it (a flow gains a screen, a state becomes reachable), update the map — ONE writer — and record it as a **spec-delta** (what changed, why, appended to the map's delta log), never a silent rewrite. Cloned maps carry `map_version` + deltas so rot is visible. Code and map drifting apart silently is the defect class this ref exists to kill.
- **Cast follows the map:** no role / persona / task for anything that is not on the map — and none missing for anything that is on it.
- **Acceptance rows come from the map when it exists** — charter → row with exact probe, edge state → render check, exit → link check (`40-verify-the-product.md` §1); row criteria keep the map's **Given/When/Then** shape. No map → the hand-built rows path there is unchanged.

## Reading map (mirror of the pipeline stages)

- This stage (MAP) reads: `map/` (or builds it via `conversion-audit` ref 11) + the brief.
- DIRECTION reads the map as shared input for both directors (`50-direction-competition.md`).
- FREEZE reads: `map_check.py` result + the lock + ownership.
- VERIFY reads: `30` + `40` + the map (row source).
- BUILD reads: `10` + `20` + this file.

## Pitfalls

- Treating the map as decoration — every cell the build ignores ships as a defect; every cell the build contradicts is a drift incident, not a detail.
- Editing map files after freeze to make the gate pass — fixes go through the change path; the gate refuses, the map doesn't bend.
- Scope creep in either direction: building states/features not on the map, or leaving on-map states unbuilt (the blank-cell class).
