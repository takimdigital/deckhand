# Store Format — ~/expert-build-library

Load when: inspecting or extending the store layout, or debugging `library.py` behavior.

```
expert-build-library/
├─ index.jsonl     one line per component (the query surface; greppable, token-cheap)
├─ registry.json   shadcn registry (derived from index; enables GitHub-registry installs)
├─ r/<name>.json   registry-item JSON per component (derived)
├─ items/<name>/   the actual files
└─ _archive/       removed items, timestamped (archive, never delete)
```

## index.jsonl — one line per item

```json
{"name":"pricing-card","tags":["pricing","cards"],"section":"pricing","files":["items/pricing-card/pricing-card.tsx"],"deps":["motion"],"source":"built 2026-09-17 @ saas-x","createdAt":"2026-09-17T15:00:00Z","install":"py scripts/library.py copy pricing-card --to <dir>"}
```

Rules: `name` is the identity (lowercase-hyphen, 2-63 chars). `files` are store-relative paths. `deps` are npm packages extracted from imports (aliases like `@/` and relative paths excluded). `source` is provenance — required in spirit even if optional in CLI.

## registry.json (derived — do not hand-edit)

Standard shadcn registry: `$schema`, `name: expert-build-library`, `items[]` with `type: registry:component`, `files[]` (store-relative), `dependencies[]`, `categories[]` (from tags). 

## r/<name>.json (derived — do not hand-edit)

One registry-item JSON per component. Two reuse paths:

1. **Local copy** (no hosting): `library.py copy <name> --to <project-dir>`.
2. **GitHub registry** (once pushed): `npx shadcn@latest add <owner>/expert-build-library/<name>` (pin with `#v1.0.0` or a commit SHA if you tag releases).

## Conventions

- Token-based files only: theme values come from CSS variables, never raw hex.
- Multi-file components keep their basenames under `items/<name>/`.
- Keep `index.jsonl` and `items/` in sync — only edit via `library.py`.
