# Changelog — component-library

## 0.1.4 — 2026-09-24

- **Ready for try-on saves.** `add` records what a try-on save must carry: the licence triple
  (`--license`, `--source-url`, `--license-evidence`; a licence without a source URL warns — the
  claim cannot be re-checked later), `--base radix|base-ui|aria|none`, `--slot`, and **per-file
  sha256 hashes** (`fileHashes`) so `verify` can catch a stored file that changed after it was saved.
- **Credential gate:** a credential-shaped value anywhere in a saved file refuses the whole save —
  nothing is written, the message names the file, never the value.
- **Local install is real:** `r/<name>.json` carries each file's content **inline** (the only shape a
  local `npx shadcn add <path>.json` installs — a content-less entry is silently skipped by the CLI).
- **Idempotent re-add:** re-adding a name with bytes-identical files prints "already in your library
  … nothing changed" and exits 0 (no `--force` needed, nothing rewritten); different bytes still need
  `--force`. `meta` on the rendered item now carries `base`/`slot`/`license`/`sourceUrl`/
  `licenseEvidence`/`imports` when recorded; aliased imports are never emitted as
  `registryDependencies` (an unknown `@scope/name` there is a hard install error in the CLI, measured
  with 4.21.0).
- Suite 11 → 16 (credential gate × whole save, licence-triple recording, hash recording + `verify`
  hash mismatch, bytes-identical no-op, inline content in the rendered item).
- Store resolution unchanged: `DECKHAND_LIBRARY` > legacy `EXPERT_BUILD_LIBRARY` (env or an existing
  `~/expert-build-library` dir) > `~/deckhand-library`.

## 0.1.3 — 2026-09-22

- Windows home note for the store path: `~` = `C:\Users\<you>` (compatibility line + the invocation note). No behavior change.

- Cold-read audit fixes (pre-release, same batch): `add` warns without `--source` and `--strict` refuses it; `--strict` also catches hardcoded `fontFamily` literals (new `FONT_RE`); `copy` refuses to overwrite existing target files without `--force`, pre-flights missing store files and directory targets (no partial installs, no raw tracebacks), and `add` rejects directory arguments with a message; new `verify` (index rows vs `items/` dirs vs files) and `where` (active store path) subcommands; name grammar + the duplicate-basename abort documented in SKILL.md; legacy-store behavior documented truthfully (the fallback is THE store — reads AND writes); recorded `install:` lines carry the cwd caveat; `find`'s scope + `list --limit` documented. Suite 8 → 11.

## 0.1.2 — 2026-09-22

- `library.py add` validates ALL inputs before touching the store — a failed `--force --strict` re-add used to delete the old item first and leave `index.jsonl`/`registry.json` pointing at files that no longer existed; duplicate basenames now hard-error instead of silently overwriting (+3 tests).
- `copy` creates the target directory if missing (was: abort with "target dir not found").
- Registry identity renamed `expert-build-library` → `deckhand-library` (registry.json `name`, store-format docs; legacy stores/env vars still read).

## 0.1.1 — 2026-09-20

- Store renamed with the pack: default `~/deckhand-library`, override `DECKHAND_LIBRARY`; the legacy `EXPERT_BUILD_LIBRARY` (env or existing `~/expert-build-library` dir) is still honored so no old store is orphaned.
- `references/store-format.md` is now linked from SKILL.md (was unreferenced).
- +1 test (legacy-env fallback) — 5 total.

## 0.1.0 — 2026-09-17

- Initial: save / find / list / show / copy / remove components; shadcn-compatible store (registry.json + r/<name>.json + items/ + index.jsonl); token-strict checks.
