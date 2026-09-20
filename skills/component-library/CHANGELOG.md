# Changelog — component-library

## 0.1.1 — 2026-09-20

- Store renamed with the pack: default `~/deckhand-library`, override `DECKHAND_LIBRARY`; the legacy `EXPERT_BUILD_LIBRARY` (env or existing `~/expert-build-library` dir) is still honored so no old store is orphaned.
- `references/store-format.md` is now linked from SKILL.md (was unreferenced).
- +1 test (legacy-env fallback) — 5 total.

## 0.1.0 — 2026-09-17

- Initial: save / find / list / show / copy / remove components; shadcn-compatible store (registry.json + r/<name>.json + items/ + index.jsonl); token-strict checks.
