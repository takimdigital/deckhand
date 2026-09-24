# Store Format — ~/deckhand-library

(Legacy stores at `~/expert-build-library` / `EXPERT_BUILD_LIBRARY` remain THE store when present — `store_root` falls back to them for reads AND writes, so nothing is orphaned.)

Load when: inspecting or extending the store layout, or debugging `library.py` behavior.

```
deckhand-library/
├─ index.jsonl     one line per component (the query surface; greppable, token-cheap)
├─ registry.json   shadcn registry (derived from index; enables GitHub-registry installs)
├─ r/<name>.json   registry-item JSON per component (derived; carries file CONTENT inline)
├─ items/<name>/   the actual files
└─ _archive/       removed items, timestamped (archive, never delete)
```

## index.jsonl — one line per item

```json
{"name":"pricing-card","tags":["pricing","cards"],"section":"pricing","files":["items/pricing-card/pricing-card.tsx"],"deps":["motion"],"imports":["@/components/ui/card"],"fileHashes":{"pricing-card.tsx":"9f2c…"},"license":"MIT","sourceUrl":"https://ui.shadcn.com/docs","licenseEvidence":"registry claim","base":"radix","slot":"pricing","depVersions":["motion@12.3.4"],"source":"built 2026-09-17 @ saas-x","createdAt":"2026-09-17T15:00:00Z","install":"py scripts/library.py copy pricing-card --to <dir>   # run from the component-library skill dir"}
```

Rules: `name` is the identity (lowercase-hyphen, 2-63 chars). `files` are store-relative paths. `deps` are npm packages extracted from imports (aliases like `@/` and relative paths excluded; react/react-dom/next skipped; subpath imports collapse to the package root, e.g. `motion/react` → `motion`). `imports` are the aliased/local specifiers the component needs on the other side — recorded, never emitted as `registryDependencies` (an unknown `@scope/name` there is a hard install error in the shadcn CLI). `fileHashes` map basename → sha256 of the stored bytes (drives the identical-bytes no-op + `verify`). `license` + `sourceUrl` + `licenseEvidence` are the licence triple (`unknown` when not recorded). `base` / `slot` exist for the buildout try-on catalog importer (rows without them are not offered). `source` is provenance — `add` warns without it, and `--strict` refuses; keep it in every stored item.

## registry.json (derived — do not hand-edit)

Standard shadcn registry: `$schema`, `name: deckhand-library`, `items[]` with `type: registry:component`, `files[]` (store-relative), `dependencies[]`, `categories[]` (from tags).

## r/<name>.json (derived — do not hand-edit)

One registry-item JSON per component. `files[]` entries carry the file's **content inline** (measured: the shadcn CLI skips a content-less entry on a local install — "No files updated." — so content is what makes the local path real). A `meta` block carries `imports`, `base`, `slot`, `license`, `sourceUrl`, `licenseEvidence` when recorded. Three reuse paths:

1. **Local copy** (no hosting, no auth): `library.py copy <name> --to <project-dir>` — the default.
2. **Local install**: `npx shadcn@latest add <path-to>/r/<name>.json` (needs a `.json` path and a project with `components.json`).
3. **GitHub registry** (once pushed): `npx shadcn@latest add <owner>/deckhand-library/<name>` (public; private works with `gh auth login` / `GH_TOKEN`). Pin with `#v1.0.0` or a commit SHA if you tag releases.

## Conventions

- Token-based files only: theme values come from CSS variables, never raw hex.
- Credential-shaped values (API-key shapes, private-key headers, tokens) refuse the whole save — the store is meant to be shareable, so secrets never enter it.
- Multi-file components keep their basenames under `items/<name>/`.
- Keep `index.jsonl` and `items/` in sync — only edit via `library.py`; `verify` then checks existence and hashes.
