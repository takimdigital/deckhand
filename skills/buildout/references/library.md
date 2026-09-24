# Save to your library (try-on → component-library)

The panel's **Save** button copies **the thing that was just tried** into the owner's personal
component library (companion skill `component-library`; store at `~/deckhand-library`), so it can
be reused in any later project. Local only — nothing is published, nothing leaves the machine.

This file is the agent-side loop. The store's own commands/flags live in `component-library/SKILL.md`.

## When it appears

- Enabled only after the try was **answered** (staged files exist). Once saved or reverted it stays
  disabled — one save per try; a different shape means Try again first.
- Degraded mode (no staged record) → the request carries no `request` id: reply error saying so;
  never guess at file paths.

## The loop (agent side)

1. `py scripts/tryon_server.py wait --project <dir>` → `{id, type:"save", request:N, slot, element, candidate}`.
2. **Resolve the stage record** — `.tryon/manifest.json`, the entry whose `request == N`
   (fallback: the newest entry). That entry is the authority for what was tried:
   `dest`, `entry`, `sha`, `specifier`, `candidate{registry,item,style,base,type,license,license_evidence,item_url}`, `source`.
   - No entry → reply **error**: “no staged record for request N — press Try again, then Save.”
     (never save from the request payload alone: it carries no sha and no licence evidence)
   - sha256 of the staged file ≠ `sha` → reply **error** `STAGE_DRIFT`: “the staged file changed
     since the try — press Try again to re-stage, then Save.” (saving drifted bytes would attach
     evidence that no longer describes them)
3. **Save** (source the exact command from `component-library/SKILL.md`):

   ```
   py <component-library>/scripts/library.py add --name <slug> --file <staged abs path> \
     --tags <slot>,<style> --license <license> --source-url <item_url> \
     --license-evidence "<evidence>" --base <base> --slot <slot> \
     --source "try-on <date> @ <project> (request #N)" --strict
   ```

   - name = the candidate's `item` when it is a valid slug (2–63 lowercase-hyphen); else `<slot>-<item>`.
   - missing licence/evidence → **do not save**; reply error naming the field (the store refuses a
     save with no licence recorded — a licence that is not written down cannot be honoured).
   - `--strict` on purpose: raw hex / literal `fontFamily` refuse instead of warn (a stored item
     must stay token-themed).
   - exit ≠ 0 → reply **error** with the script's own words; a failed save is never an ok.
4. **Make it visible in future try-on catalogs** (idempotent; safe to re-run after every save):

   ```
   py scripts/library_import.py            # add --prune after `library.py remove` archival
   ```

   Only items with base + slot + licence are offered; personal rows rank **first** in the slot,
   under the same base filter as everything else. `--dry-run` prints the counts.
5. **Reply** — `py scripts/tryon_server.py reply --project <dir> --id <req id> --status ok
   --message 'saved as "<name>" — reuse with: py scripts/library.py copy <name> --to <dir>'`.
   On any failure: `--status error` + the plain reason. (A reply is refused twice for the same id
   unless `--force` — an answered request stays answered.)

## What lands where

- `items/<name>/…` copied files · an `index.jsonl` row · `r/<name>.json` (files **inline**, so
  `npx shadcn@latest add <path>/r/<name>.json` installs real files) · `registry.json`.
- Recorded: licence triple (`--license --source-url --license-evidence`), base, slot, tags,
  auto-extracted deps, aliased imports (`meta.imports`, never `registryDependencies`), per-file
  hashes, and the `--source` line carrying the request id.

## Storage (his call, decide once)

- Default `~/deckhand-library` on this machine; `DECKHAND_LIBRARY` overrides; legacy
  `~/expert-build-library` is honoured when it already exists.
- Wants it on a second machine → he `git init`s the store and pushes to a **private** repo he owns;
  pushing is explicit, never automatic.
- Never save into the project being worked on; never touch `components/ui/*`.

## Rules that are not negotiable

- Licence-gated: no licence or no evidence → no save; say which is missing.
- A **credential-shaped value** in any saved file refuses the **whole** save (library.py gate) —
  tell the owner which file; never paste the value into chat or the reply.
- Identical re-save is a friendly no-op (exit 0); different bytes need his explicit ask + `--force`.
- Keep it local: no hosting, no network; the private-repo flow is opt-in.
- Themes (a whole token set) and whole-project boilerplates are **not shipped yet** — do not
  promise them; component saves only.

## Verify (2-minute recipe)

```
py <component-library>/scripts/library.py verify      # → VERIFY OK
py scripts/library_import.py --dry-run                # → offered / skipped counts
```

Then open the panel on that slot again — the saved item appears **first** in the candidates.

A browser smoke (headless Chrome over CDP) can drive the whole loop against a scratch fixture:
boot → Try → reply → Save → `library.py add` → `library_import` → catalog re-rank. Two traps when
you build one: a headless viewport is short — set device metrics (e.g. 1280×820) and click only
elements whose rect is in view (the actions footer is sticky so this stops mattering for real
owners); and on Windows pick a port **outside** the Hyper-V excluded ranges
(`netsh interface ipv4 show excludedportrange protocol=tcp`; measured-blocked: 8087–8123) or
`http.server` dies with `WinError 10013`.
