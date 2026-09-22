# 20 — Component Library (store what you build)

Load when: a component was built/refined and is worth keeping, or the user asks to save/reuse/find components.

The companion skill `component-library` owns the store and its script — it lives at `component-library/scripts/library.py`, so run the commands below **from that skill's directory** (or from anywhere with the absolute path: `py <skills-dir>/component-library/scripts/library.py …`); this doc explains how buildout uses it.

## Save (end of a section or session)

Offer once, batched (same question policy as the update loop — never per-component nagging):
> "This `<component>` is reusable. Save it to your library? (save / skip)"

On save:

```bash
py scripts/library.py add --name <slug> --file <path> [--file ...] \
  --tags "pricing,cards" --section pricing \
  --source "built 2026-09-17 @ <project> (adapted from @velora/<item>)" \
  [--strict]
```

Rules: token-based files only (no raw hex — `--strict` enforces); provenance in `--source` always; tags from the existing vocabulary (check `py scripts/library.py list` first).

## Reuse (before hand-building anything)

1. `py scripts/library.py find "<query>"` → `show <name>` → `copy <name> --to <project>/src/components/ui/`.
2. If the store is pushed to a public GitHub repo, it is a valid **GitHub registry**: `npx shadcn@latest add <owner>/<library-repo>/<name>` (pin `#v1.0.0` or a commit SHA).
3. After copying, run the same verify gates as buildout: build, hex-lint, tokens in use, contrast.

## Growth discipline

- Dedupe by name (`--force` to replace); `remove` archives to `_archive/` (never deletes).
- Keep tags small and stable: section (`hero`, `pricing`, `dashboard`, `forms`) + aesthetic (`animated`, `minimal`, `editorial`).
- The store is machine-local by default (`~/deckhand-library`, override `DECKHAND_LIBRARY`; the legacy `EXPERT_BUILD_LIBRARY` is still honored); `git init` it if it should travel.
- Index stays greppable: one JSONL line per component — the query surface is designed to stay token-cheap at hundreds of items.

## Verification

- `find` returns the item; `copy` places files; `py -m json.tool registry.json` passes; index line count == item count; `r/<name>.json` exists for each item.
