# Changelog — component-library

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
