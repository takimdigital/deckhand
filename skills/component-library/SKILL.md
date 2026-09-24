---
name: component-library
description: "Save, find, and reuse UI components across projects."
version: 0.1.4
author: Takim, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
compatibility: "Agent Skills layout. Needs Python 3.10+ (stdlib) for scripts/library.py. Store at ~/deckhand-library (`~` = home; on Windows `C:\\Users\\<you>`; override: DECKHAND_LIBRARY; legacy EXPERT_BUILD_LIBRARY honored)."
metadata:
  hermes:
    tags: [components, reuse, library, shadcn, store, tokens, license, provenance]
---

# Component Library

Personal store for UI components the user builds or adapts, so they can be found and reused in any later project instead of rebuilt. The store is a shadcn-compatible folder (`registry.json` + `r/<name>.json` + `items/`) plus a flat `index.jsonl` the agent can grep cheaply even with hundreds of items. Companion to `buildout` (used at the end of buildout sessions to keep what was built; try-on sessions save straight from the picker panel). Store format spec: `references/store-format.md`.

Safety rules (measured, not decorative): a **credential-shaped value refuses the whole save**; every item records **provenance + licence triple** (`--source`, `--license`, `--source-url`, `--license-evidence`); `r/<name>.json` carries each file **inline** so a local `shadcn add` installs real files; re-adding identical bytes is a friendly **no-op**.

## When to Use

- User says "save this component", "keep this for later", "reuse X in my other project", "find something I built".
- A component was built or meaningfully refined in a session and is worth keeping (offer to save at wrap-up).
- After a try-on Keep — save the exact tried component (the agent does this from the staged files).
- Before hand-building UI from scratch — check the library first.

## Don't Use For

- Third-party code with unverified provenance/licence (MIT-only rule from `buildout`; record licence + source URL always).
- One-off style snippets — store real components.

## How to Run

```
py scripts/library.py add --name <slug> --file <path> [--file ...] [--tags a,b] [--section pricing]
                          [--source "built 2026-09-17 @ proj"] [--license MIT] [--source-url <url>]
                          [--license-evidence "registry claim"] [--base radix|base-ui|aria|none]
                          [--slot button] [--dep-versions "motion@12.3.4"] [--strict] [--force]
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

1. **Save.** Run `add` with every file of the component; keep files token-based (no raw hex, no hardcoded `fontFamily` literals — warns by default, `--strict` refuses). Always set `--source`; set the licence triple — a missing `--license` warns by default and refuses under `--strict` (a licence that is not written down cannot be honoured later). A **credential-shaped value in any file refuses the whole save** (nothing partial lands). Name grammar: lowercase letters/digits/hyphens, 2–63 chars (`PricingCard` is rejected); duplicate basenames across one component's files hard-error. Tags vocabulary: section names (`hero`, `pricing`, `dashboard`, `forms`, …) + aesthetic (`animated`, `minimal`, `editorial`).
2. **Reuse.** `find` → `show` → `copy <name> --to <project>/src/components/ui/` (the target dir is created if missing; an existing target FILE is never overwritten without `--force`). Local install also works — `r/<name>.json` carries each file's content inline, so `npx shadcn@latest add <path>/r/<name>.json` installs real files into a project with a `components.json` (a content-less entry is silently skipped by the CLI — never strip the content). If the store is pushed to a GitHub repo: `npx shadcn@latest add <owner>/<repo>/<name>` (public works; private works with `gh auth login` or `GH_TOKEN`). Aliased imports the component needs (`@/components/ui/card` …) are recorded in the item's `meta.imports` — they are **never** emitted as `registryDependencies` (an unknown `@scope/name` there is a hard install error in the CLI, measured with 4.21.0).
3. **Maintain.** Re-adding a name needs `--force` **unless the bytes are identical** (then it prints "already in your library … nothing changed" and exits 0); `copy` refuses to overwrite existing files in the target without `--force`; `remove` archives to `_archive/` (never deletes); `registry.json` + `r/<name>.json` are re-rendered automatically on add/remove.

## Pitfalls

- Raw hex / hardcoded `fontFamily` literals in stored components — breaks token theming later; `--strict` refuses both (warn-only by default, so run with `--strict` unless intentional).
- Missing provenance — always pass `--source`; missing licence — always pass `--license` + `--source-url`.
- Never hand-edit `index.jsonl`, `registry.json` or `r/*.json` — they desync; edit via `library.py`, then `verify`.
- Tag sprawl — check `list` and reuse existing tags before inventing new ones.
- The store is machine-local by default — `git init` + push if it should travel between machines.

## Verification

- `find "<name>"` returns the item; `copy` places the files; `py -m json.tool registry.json` passes; index line count equals the number of item dirs under `items/` (a failed `--force --strict` re-add can no longer desync them — inputs are validated before anything is replaced).
- `r/<name>.json` carries `files[].content` (a local install must not be a silent no-op) and a `meta` block with imports/base/slot/licence when recorded.
- `verify` prints OK or the exact desyncs (index rows vs `items/` dirs vs files vs saved hashes); `where` prints the active store path — run `verify` after any manual poke.
