---
name: component-library
description: "Save, find, and reuse UI components across projects."
version: 0.1.3
author: Takim, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
compatibility: "Agent Skills layout. Needs Python 3.10+ (stdlib) for scripts/library.py. Store at ~/deckhand-library (`~` = home; on Windows `C:\Users\<you>`; override: DECKHAND_LIBRARY; legacy EXPERT_BUILD_LIBRARY honored)."
metadata:
  hermes:
    tags: [components, reuse, library, shadcn, store, tokens]
---

# Component Library

Personal store for UI components the user builds or adapts, so they can be found and reused in any later project instead of rebuilt. The store is a shadcn-compatible folder (`registry.json` + `r/<name>.json` + `items/`) plus a flat `index.jsonl` the agent can grep cheaply even with hundreds of items. Companion to `buildout` (used at the end of buildout sessions to keep what was built). Store format spec: `references/store-format.md`.

## When to Use

- User says "save this component", "keep this for later", "reuse X in my other project", "find something I built".
- A component was built or meaningfully refined in a session and is worth keeping (offer to save at wrap-up).
- Before hand-building UI from scratch — check the library first.

## Don't Use For

- Third-party code with unverified provenance/license (MIT-only rule from `buildout`; record `--source` always).
- One-off style snippets — store real components.

## How to Run

```
py scripts/library.py add --name <slug> --file <path> [--file ...] [--tags a,b] [--section pricing] [--source "built 2026-09-17 @ proj"] [--strict] [--force]
py scripts/library.py find "<query>" [--limit 5]   # searches name/tags/section/source — not filenames
py scripts/library.py list [--limit 30]
py scripts/library.py show <name>
py scripts/library.py copy <name> --to <dir> [--force]
py scripts/library.py remove <name>
py scripts/library.py verify
py scripts/library.py where
```

(On macOS/Linux use `python3`; on Windows `~` = `C:\Users\<you>`. Store location = `DECKHAND_LIBRARY` if set, else `~/deckhand-library`; a legacy `EXPERT_BUILD_LIBRARY` is still honored.) Run scripts from the skill's own directory, or pass the full path to `scripts/library.py` from anywhere — a recorded `install:` line assumes the skill dir as cwd.

## Procedure

1. **Save.** Run `add` with every file of the component; keep files token-based (no raw hex, no hardcoded `fontFamily` literals — warns by default, `--strict` refuses); always set `--source` (a missing one warns; `--strict` refuses). Name grammar: lowercase letters/digits/hyphens, 2–63 chars (`PricingCard` is rejected); duplicate basenames across one component's files hard-error. Tags vocabulary: section names (`hero`, `pricing`, `dashboard`, `forms`, …) + aesthetic (`animated`, `minimal`, `editorial`).
2. **Reuse.** `find` → `show` → `copy <name> --to <project>/src/components/ui/` (the target dir is created if missing; an existing target FILE is never overwritten without `--force`). If the store is pushed to a public GitHub repo: `npx shadcn@latest add <owner>/<repo>/<name>` (the store ships `registry.json` + `r/*.json` at the repo root, so it is a valid GitHub registry as-is).
3. **Maintain.** Re-adding a name needs `--force`; `copy` refuses to overwrite existing files in the target without `--force`; `remove` archives to `_archive/` (never deletes); `registry.json` + `r/<name>.json` are re-rendered automatically on add/remove.

## Pitfalls

- Raw hex / hardcoded `fontFamily` literals in stored components — breaks token theming later; `--strict` refuses both (warn-only by default, so run with `--strict` unless intentional).
- Missing provenance — always pass `--source`.
- Tag sprawl — check `list` and reuse existing tags before inventing new ones.
- The store is machine-local by default — `git init` + push if it should travel between machines.

## Verification

- `find "<name>"` returns the item; `copy` places the files; `py -m json.tool registry.json` passes; index line count equals the number of item dirs under `items/` (a failed `--force --strict` re-add can no longer desync them — inputs are validated before anything is replaced). `verify` prints OK or the exact desyncs (index rows vs `items/` dirs vs files); `where` prints the active store path — run `verify` after any manual poke.
