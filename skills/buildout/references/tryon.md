# Try-on — real registry components, on a site the owner already runs

Use when the owner wants to **try** real components on their own running site and keep the one they like. Not generation: every candidate is a **licensed, installable component** from a measured MIT
registry, staged beside the original and swapped by flipping one import — the app's own HMR shows it within a second. Dev-only, journaled, revertable; nothing vendored, nothing shipped to production.

## The four pieces

| piece | file | what it is |
|---|---|---|
| catalog | `scripts/tryon_intake.py` + `tryon_catalog.py` | MIT registries measured into `registry_items` (SQLite) — never re-fetched per click |
| helper | `scripts/tryon_server.py` | loopback-only, token-gated; the browser POSTs picks, the agent polls `wait` |
| overlay | `templates/tryon/overlay.js` | the picker the owner uses (owner's own browser) |
| swap | `templates/tryon/swap.mjs` | stage the candidate, flip the import, verify, journal, revert |

`templates/tryon/loader.cjs` + `tryon-dev.tsx` are the dev-only files the installer writes;
`test-swap.mjs` (codemod battery) and `test-ladder.cjs` (slot ladder) run against the shipped files.

## 1. Catalog (once, then refresh)

```bash
py scripts/tryon_intake.py --registry shadcn --style new-york-v4   # Radix family py scripts/tryon_intake.py --registry shadcn --style base-nova     # Base UI family — crawl BOTH
py scripts/tryon_intake.py                                         # all other usable registries py scripts/tryon_catalog.py slots                                  # every slot with free counts
py scripts/tryon_catalog.py query --slot button --project D:/<slug>
```

Items are keyed `(registry, item, style)`: shadcn ships the **same names in several style families with different code** (`base-nova` = Base UI, `new-york-v4` = Radix) and `base` follows the style, so
a project only ever sees its own family. What the intake guarantees: registry-level licence gate
(`data/registries.json` — MIT/Apache only; AGPL, Commons-Clause, custom and marketplace ToS
**refused**), base detection, slot classification (keyword floor, not a promise), collision guard (an
item owning `lib/utils.ts` is never offered), and a **sampled installability probe** (per free type, up to 3 items fetched — the endpoint must embed `files[].content`, because the CLI silently drops
content-less items; re-checked per item at try time). Evidence: `data/registry-snapshots/` +
`registry-evidence.json`.

## 2. Install the plumbing into the project

```bash
py scripts/tryon_install.py install   --project D:/<slug> [--port 7799]   # exit 4 = paste the snippet py scripts/tryon_install.py status    --project D:/<slug>
py scripts/tryon_install.py uninstall --project D:/<slug>                 # byte-exact restore
```

Writes `.tryon/loader.cjs` + the dev mount (`components/dev/tryon-dev.tsx`, or under `src/…` on a src-dir project) and patches two files: `next.config.*` — merged into a config that already owns
`turbopack` (or `experimental.turbo` on Next < 15.3); only an existing `rules`/`turbo` object is
refused, with a paste-ready snippet — and the root layout (`app/layout.tsx`, `src/app/layout.tsx`, or the next-intl `src/app/[locale]/layout.tsx`). Never touches `components/ui/`. Every patch is backed
up and journaled, so `uninstall` restores byte-exact and refuses to revert a file the owner edited since. v1 = Next.js App Router dev servers.

## 3. Run the loop

```bash
py scripts/tryon_server.py serve --project D:/<slug>          # background it; the owner opens the site py scripts/tryon_server.py wait  --project D:/<slug> --follow --timeout 3600   # one line per pick
py scripts/tryon_server.py reply --project D:/<slug> --id N --status ok --message "…"
```

`wait` **without** `--follow` exits on the first request — fatal live (every later click lands with
nobody listening). Run `--follow` as a background job with a notify. The owner clicks **Try-On** in the corner of their own site, hovers (outline + `file:line` from `data-tryon-src`), picks a slot and a
candidate. Per request the agent:

1. resolves the element's file:line (walk up to the nearest `data-tryon-src`);
2. **guards BEFORE anything is fetched or written** — `py scripts/tryon_guard.py check --project
   D:/<slug> --file <owner file> --line N --candidate-slot <slot> [--element-slot <s>]
   [--candidate-base <b>] [--rescope]`; exit 4 = refused (section / slot or base mismatch / container /
   inline / no binding) → `reply --status error`: nothing fetched, staged or written;
3. queries the catalog **scoped to the project** — `py scripts/tryon_catalog.py query --slot <slot>
   --project D:/<slug> [--registry <r>]`. Hard base filter (a Radix project never sees a Base UI item;
   base-free always fits) + hidden count, e.g. `[#9 of 12 live items; 3 hidden (need base-ui)]`; the
   overlay shows the same scope from `/catalog`: *Matching your setup: Radix · shadcn-style — 12 ready
   to try, 5 hidden (they need base-ui)*. Same-registry candidates first, never an empty list;
4. fetches and **stages** the pick: `node templates/tryon/swap.mjs install --root D:/<slug> --from
   <fetched file> --slot <slot> --entry <Export>` → `components/variants/<slot>/<name>.tsx`;
5. installs the item's npm `dependencies`, fetches `registryDependencies` the same way;
6. **checks the prop shape against the real usage** — `node templates/tryon/swap.mjs props --root
   D:/<slug> --file <owner file> --line N --local <Local> --candidate components/variants/<slot>/<name>.tsx
   [--entry <E>]`: `ok:false` (`missing_required`) = the candidate needs props the usage never passes →
   refuse, `reply --status error` naming them; `dropped` = props the usage passes that the candidate
   ignores (`variant`, `size`) → carry into the reply so the owner knows what stops meaning anything;
   `unverifiable` (imported/generic props type, `{...spread}`) is said out loud, never a silent pass;
7. flips the owning import: `node templates/tryon/swap.mjs apply --root D:/<slug> --file <owner file>
   --local <Local> --to components/variants/<slot>/<name>.tsx` — HMR re-renders; the file is
   re-parsed, the new binding verified, every other import byte-identical, `from → to` journaled;
8. `reply … --status ok` (the overlay shows it).

**Keep** → leave it in, delete the slot's other staged variants, record the item + `item_url` for
**Back** → `swap.mjs revert --root … --file <owner file>` (or `--all`) — restores bytes exactly, or re-derives the swap if the owner edited the file meanwhile.

## Save
The panel's **Save** verb turns the last try into a permanent item in the owner's library (companion skill `component-library`); the agent-side loop, the licence/credential gates and the exact commands live in `references/library.md`.

## Prod rule

The loader is registered only when `NODE_ENV === "development"` and hard-refuses outside it; the overlay is appended by a `'use client'` mount that is folded away in a production build. Verify:
`py -m pytest tests/` + a clean `next build` and `grep -rl 'data-tryon-src' .next` → **zero files**
(a stale `.next/dev/` cache is not build output — `rm -rf .next` first), then `tryon_install.py
uninstall` and deploy.

## Traps that were live-hit (do not re-learn these)

- **Scope the pool to the project before ranking anything.** Without a base filter the top candidates
  for a Radix project were Base UI items (registry sort is alphabetical), and a shadcn score bonus
  decided swaps on metadata, not fit. Base = hard filter, registry = ordering, hidden = a counted
  number — never a silent drop. shadcn items are style-scoped: `base-nova` is Base UI *code*, so
  keying items without the style quietly offered Base UI buttons to a Radix project.
- **Prop shape is part of the slot contract.** Flipping an import does not adapt props: a candidate
  that needs props the usage never passes breaks at render; `variant`/`size` passed to a candidate
  that ignores them vanishes silently. Run `swap.mjs props` (project's own TypeScript) before `apply`.
- **Never `stopPropagation` in the capture phase on your own panel.** It silently killed every button
  inside it — Try, Keep, Revert *and* Close ("Apply does nothing" + "can't close" were one bug).
- **Identify your own UI by composed path, not screen coordinates.** `elementFromPoint` lies for
  keyboard/zero-coordinate clicks and shadow retargeting; check `e.composedPath().includes(host)`.
- **A one-shot `wait` dies on the first request** — the live loop needs `wait --follow` (see §3).
- **`condition` inside a Turbopack rule is a matcher, not an env gate.** A static rule stamps
  production builds too (measured: 4 files). Gate on `NODE_ENV === "development"` AND refuse in the loader.
- **A fallback must never look like a result.** With inference null the slot select kept option[0] —
  blocks sort first, so a pricing grid was silently offered `cta` and the click swapped the grid for a
  CTA. Empty inference → placeholder + disabled Try, never option[0].
- **Where Next keeps the rule is version-dependent** (read `node_modules/next/package.json`):
  `turbopack.rules` ≥15.3, `experimental.turbo.rules` below. The wrong home is *ignored* — newer Next
  warns `Unrecognized key(s)`, older Next never stamps.
- **A `<` glued to a preceding identifier / `)` / `]` is a type-argument list, never JSX**
  (`useState<boolean | null>(null)`, `Promise<Metadata>`, `<typeof x>`). After any loader change
  re-run the preflight: transform every tsx and re-parse with the project's own TypeScript (69 files
  / 1,528 tags / 0 broken is the shipped bar).
- **Check the export shape before wiring it.** A staged `registry:example` exports `default`; a named
  import 500s with `Export X doesn't exist … Did you mean to import default?` — and `//` inside JSX
  renders as page text, so markers around `<TryOnDev />` must be `{/* … */}`.
- **Served-HTML greps must tolerate React's `<!-- -->` markers** — a phrase spanning dynamic and
  static segments greps as 0 in both the swapped and restored page, "proving" a revert that never
  happened. The byte hash (`shaBefore`/`shaAfter`) is the real evidence.
- **Python text-mode I/O rewrites LF as CRLF on Windows** — a "byte-exact" uninstall silently drifts.
  Read/write project files with `read_bytes()/write_bytes()`.
- **A stale `EADDRINUSE` port owner** is found with `netstat -ano` (last column = PID) and killed
  with `MSYS2_ARG_CONV_EXCL='*' taskkill /F /PID <pid>` (`taskkill //F` is invalid here); and
  `next build` does not clean `.next/dev` — `rm -rf .next` before a production-cleanliness proof.

## Rules that are not negotiable

- **Licence first.** A registry or item that is not MIT/Apache-2.0, or is behind a paid tier / login
  (`tailark` blocks are 401; `cult-ui` unfetchable; `coss` AGPL; `animate-ui` MIT + Commons Clause),
  is refused — state the reason, never try it.
- **Match by slot = (type, exports, target, prop shape), never by name**, and match the **base/style
  family** the same way: Radix ↔ Radix or base-free.
- **The element decides; a fallback is never an answer.** Inference may return null — the panel asks
  (empty select, Try disabled). Whole sections (block slots) are never swapped in v1 (they render
  children and would lose the owner's content); a differing candidate slot needs an explicit
  re-scope tick (`elementSlot` + `rescope` on the request).
- **An impossible request is never a success.** `swap.mjs` exits non-zero for NO_IMPORT / unsupported
  namespaces, and a flag the command does not use is a usage error — no ok for a no-op.
- **Never overwrite `components/ui/*`.** Stage under `components/variants/`, flip one import.
- **Dev-only.** Anything that reaches a production bundle is a bug, not a feature.
- **Degraded mode** (no loader — webpack projects, monorepos, non-Next stacks): the owner names the
  slot, the agent locates the file by grep; catalog, staging and codemod still apply.
