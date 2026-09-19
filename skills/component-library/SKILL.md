---
name: component-library
description: "Save, find, and reuse UI components across projects."
version: 0.1.0
author: Takim, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
compatibility: "Agent Skills layout. Needs Python 3.10+ (stdlib) for scripts/library.py. Store at ~/expert-build-library (override: EXPERT_BUILD_LIBRARY)."
metadata:
  hermes:
    tags: [components, reuse, library, shadcn, store, tokens]
---

# Component Library

Personal store for UI components the user builds or adapts, so they can be found and reused in any later project instead of rebuilt. The store is a shadcn-compatible folder (`registry.json` + `r/<name>.json` + `items/`) plus a flat `index.jsonl` the agent can grep cheaply even with hundreds of items. Companion to `buildout` (used at the end of buildout sessions to keep what was built).

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
py scripts/library.py find "<query>" [--limit 5]
py scripts/library.py list
py scripts/library.py show <name>
py scripts/library.py copy <name> --to <dir>
py scripts/library.py remove <name>
```

(On macOS/Linux use `python3`. Store location follows `EXPERT_BUILD_LIBRARY` if set.)

## Procedure

1. **Save.** Run `add` with every file of the component; keep files token-based (no raw hex — `--strict` enforces it); always set `--source`. Tags vocabulary: section names (`hero`, `pricing`, `dashboard`, `forms`, …) + aesthetic (`animated`, `minimal`, `editorial`).
2. **Reuse.** `find` → `show` → `copy <name> --to <project>/src/components/ui/`. If the store is pushed to a public GitHub repo: `npx shadcn@latest add <owner>/<repo>/<name>` (the store ships `registry.json`, so it is a valid GitHub registry).
3. **Maintain.** Re-adding a name needs `--force`; `remove` archives to `_archive/` (never deletes); `registry.json` + `r/<name>.json` are re-rendered automatically on add/remove.

## Pitfalls

- Raw hex / hardcoded fonts in stored components — breaks token theming later; run with `--strict` unless intentional.
- Missing provenance — always pass `--source`.
- Tag sprawl — check `list` and reuse existing tags before inventing new ones.
- The store is machine-local by default — `git init` + push if it should travel between machines.

## Verification

- `find "<name>"` returns the item; `copy` places the files; `py -m json.tool registry.json` passes; index line count equals item count.
