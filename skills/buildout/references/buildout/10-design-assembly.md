# 10 — Design Assembly (coherent-random, lock-first)

Load when: the UI must be designed/built, or the user says "design this site / make it look good".

The problem: raw AI design output is slop (same hero, same purple gradient, same three cards), and users burn hours fixing it back and forth. The fix: **coherent randomness** — pick real components from live MIT registries at random *within* a locked design identity, so variety never breaks coherence.

**Path arbiter:** this ref drives the UI authoring — with or without a starter. A surviving match in `data/boilerplates.json` means `00-start-from-boilerplate.md` runs first (clone/strip/rebrand); on a bare scaffold (no starter), start here after the scaffold + one green baseline build. A starter that contradicts the frozen lock loses — the lock wins (ref 00's conflict clause).

## Phase 0 — Brief (one batched round, skippable, defaults apply)

Ask once, option-style, separate from the task. Questions:

1. What are you building + who is it for? (free text)
2. Pick 2 vibes: editorial · institutional (documentary/archival) · brutalist-lite · soft-tech · playful · luxe-dark · crisp-minimal (no bucket fits → add it to this list append-only; never invent in-run)
3. Palette: preset | your brand colors | **seeded surprise** (default)
4. Typography: 3 curated pairings | **seeded surprise** (display + body; OFL/SIL only — pick any known OFL family pair and record it; the license line is EXPECTED here and verified at assembly — no fetch, no bundled list at this stage)
5. Density: compact / **comfortable** / airy
6. Motion: none / subtle / **medium** (+ budget: ≤3 animated components per page)
7. Randomness dial: safe / **coherent-random** / adventurous

Skipped entirely → the bold defaults apply; left-blank answers stay blank (never invented for you).
8. Bans: colors/motifs to avoid (optional)

## Phase 1 — Lock

**Seam:** when a direction competition ran (`50-direction-competition.md`), its merge supplies the winning direction and this phase's one-round brief path is skipped — the lock is still written HERE, in this schema (format-compatible: no removed or renamed keys; new keys optional). No competition → this phase runs exactly as before.

Write `<project>/.design/design.lock.json`:

```json
{
  "version": 1, "seed": 4242, "randomness": "coherent-random",
  "vibes": ["editorial", "soft-tech"], "density": "comfortable",
  "radius": "0.75rem", "motion": "medium", "maxAnimatedPerPage": 3,
  "colors": { "background": "#faf7f2", "surface": "#ffffff", "ink": "#1c1a17",
              "muted": "#6b6560", "accent": "#c2410c", "border": "#e7e2da" },
  "fonts": { "display": "Fraunces", "body": "Inter", "mono": "JetBrains Mono",
             "license": "OFL (Google Fonts)" },
  "base": "radix",
  "sections": {}
}
```

`base` = the component primitive layer: `"radix"` (the curated shadcn/Radix base — the default) or `"none"` (hand-built from the token file; no component base). Optional keys (additive; existing locks stay valid — validated by the gate when present): `"dark"` (the same six color keys, 6-hex each — the frozen dark-scheme derivation) · `"focus_ring"` (a 6-hex color the focus ring must use).

Then set the tokens in the project's single token file — for a create-next-app + Tailwind v4 project that is `src/app/globals.css` (a v3 project: `tailwind.config.ts`) — as CSS variables. **The lock is the coherence source: color, fonts, radius, motion, density are decided once and every later component inherits them.** **Ownership of what the lock does not fix:** type scale + spacing rhythm → the design pass (token file). Focus ring → owned by the design pass, and by PASS_2 when a competition ran: the ring uses the accent token (or `focus_ring` when frozen) and the components' default `--ring` is remapped so no second accent ships. Dark scheme → the design pass, REQUIRED whenever the project ships dark mode: derive dark hexes in the token file, keep every text pair ≥4.5:1 in BOTH schemes (fills included), and optionally freeze the derivation as the `dark` block. The seed is chosen once — when a direction competition ran it is the winner's seed traveling with the merge (ref 50 rule 4); otherwise pick any fixed integer here and keep it stable (same seed + same inputs = same picks, reproducible).

## Phase 2 — Assemble, section by section

Blueprint (marketing): nav · hero · logos/social proof · features · product shot · how-it-works · testimonials · pricing · FAQ · CTA · footer. (App: shell, dashboard cards, tables, forms, settings, empty states, auth screens, 404.)

For EACH section:

1. **Freshness:** `py scripts/registry_sync.py check` → if stale, `sync`. Ensure `data/items/*.jsonl` catalogs exist — they are generated per registry, on demand: `onboard <@ns>` (only MIT-allowlisted namespaces onboard; add `--catalog-file` if the index is throttled, see the allowlist note).
2. **Candidates:** `py scripts/assemble_pick.py --section <s> --tags <brief tags> --k 3 --seed <lock.seed + section index>`
   - Weighted: section match, tag match, registry variety, smaller size preferred. Deterministic per seed. `--explain` prints per-pick reasoning to stderr.
   - **The picker is honest now:** zero tag hits across the picks → a `NO TAG MATCH` warning (stderr) — the tags did NOT drive the pick; re-tag, curate, or treat the zero-hit as evidence for the banlist override. A section with no curated rows → the documented fallback line fires; search by keyword instead: `py scripts/assemble_pick.py --section <keyword> --list` — then `verify --item` before installing (401/403 = gated — don't install). **Relevance floor:** a fallback candidate must match the keyword in its name/description/tags to count; fallback picks with zero keyword hits are NOT candidates (the tool says so loudly) — when nothing clears the floor, hand-build the section from lock tokens instead of shipping an irrelevant app component.
   - Present the 3; user picks, or "pick for me" → candidate #1. (Safe dial = always #1.)
3. **Pre-flight the item body (before install):** fetch the pick's item JSON and check, in one look: `files` is non-empty; no remote stock-photo hosts (unsplash/placeholder services); no star-rating markup; **no imports of packages the item does not DECLARE** (a bare `import` of a package missing from its `dependencies`/`registryDependencies` — including non-registry npm packages like `class-variance-authority` — means redeclare it yourself or reject the candidate); `registryDependencies` resolvable. Any miss → the picker proposes, the lock and the client's bans decide — reject and re-pick. (Field-tested misses: five "recommended" items shipped empty `files` arrays; a testimonial block shipped 5 Unsplash avatars + autoplay; a button imported an undeclared package.)
4. **Install:** `npx shadcn@latest add <target> --yes` (target comes in the pick; `--yes` = non-interactive). **A fresh scaffold has NO `components.json`** — `add` then blocks on an interactive prompt, and `init` both prompts and can die with `ERR_PNPM_IGNORED_BUILDS`; hand-write the minimal file first: `{ "$schema": "https://ui.shadcn.com/schema.json", "style": "new-york", "rsc": true, "tsx": true, "tailwind": { "css": "src/app/globals.css", "baseColor": "neutral", "cssVariables": true, "prefix": "" }, "aliases": { "components": "@/components", "utils": "@/lib/utils", "ui": "@/components/ui", "lib": "@/lib", "hooks": "@/hooks" } }`. Namespaced alternative: add the registry to `components.json` `"registries": { "@reui": "https://reui.io/r/base-nova/{name}.json" }` → `add @reui/<item>`; or ask the harness's shadcn MCP server to "add X from @ns". Read-only pack / externally-sourced registry: the supported route is an `data/allowlist.json` edit + `onboard` — when the pack cannot be edited, `onboard --catalog-file <saved index>` + install-by-URL works, and the license evidence goes into the project.
5. **Apply the lock:** ensure the component consumes the token variables; if the item ships its own `cssVars`, remap them to the lock's variables; if it hardcodes colors → small retokenize edit, or reject the candidate.
6. **Verify gates** (below), then record in `lock.sections[<s>] = { id, registry, url, pickedAt }` and continue. (`sections{}` is the lock's ONE build-time append — the pick record; it is exempt from freeze immutability and nothing else in the lock changes after freeze. A form/CTA sink shipped without a live delivery channel gets a `PENDING.md` item + honest copy — ref 40 §3.)

## Phase 3 — Verify gates (per section; then per page)

```bash
npm run build                                                     # must pass
# Coherence gate - 3 of 3 required (portable; rg may be absent entirely)
grep -rnE '#[0-9a-fA-F]{3,8}\b' src --include='*.tsx' --include='*.jsx'   # 1) raw values: expect nothing
grep -rnE '\b(bg|text|border|from|via|to|ring|fill|stroke|divide|outline|accent|caret|decoration|shadow)-(slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-[0-9]{2,3}\b' src --include='*.tsx' --include='*.jsx'   # 2) palette utilities: expect nothing
grep -rnE 'transition-|animate-|duration-[0-9]' src --include='*.tsx' --include='*.jsx'   # 3) state-motion: with motion:"none" expect NOTHING; otherwise every hit must carry a lock-governed duration (no component-default timings)
grep -rn "var(--" src/components/*                               # tokens in use: expect hits
```
`rg` may be absent entirely — these greps are the substitute and all three coherence checks must run: a clean check 1 is NOT coherence (the regex cannot see palette utilities, second fonts, radius drift, or state-motion defaults). If `rg` IS present, the same checks may be run with it: `rg -n --pcre2 '#[0-9a-fA-F]{3,8}\b' src -g '*.tsx' -g '*.jsx'` + `rg -n '\b(bg|text|border|from|to|ring|fill|stroke)-(slate|gray|zinc|neutral|stone|red|blue|indigo|violet|purple|pink|rose)-[0-9]{2,3}\b' src -g '*.tsx' -g '*.jsx'`. All checks target the component surface (`*.tsx`/`*.jsx`) — the token file legitimately contains raw hex, and comments/docs mentioning a utility name must not trip the sweep (read check 3's hits the same way — a comment is not a hit).

Plus manual: keyboard pass on interactive elements; **focus ring uses the accent token (or `focus_ring`) — remap the components' default `--ring`, never let a second accent ship**; contrast ≥4.5:1 for **every text/background pair in BOTH schemes** — light AND dark, and check *fills*, not just text on page background (a bright accent used as a button fill with white text is the classic dark-mode AA miss); ≤`maxAnimatedPerPage` animated components; `prefers-reduced-motion` respected.

## Anti-slop banlist (defaults; overridable in the brief)

- No purple→blue gradient hero on near-black. No glow-everything. No centered-everything — vary alignment across sections.
- ≤3 animated components per page; ≥3 different registries across a page (variety) while tokens keep coherence. **Precedence: an explicit client ban or brief constraint outranks this count** — a pick whose `why` carries zero tag hits is admissible evidence for invoking the override; if the pool cannot supply variety without breaking the bans, variety yields (log the override).
- No lorem ipsum shipped; no fake "trusted by" logos; max 2 font families (+mono).
- ≤6 features per row, grouped meaningfully (no icon soup); one accent color; consistent radius.
- Components must be token-based (themeable) or they get rejected/retokenized.

## Delegation

Applying a component's tokens + integration is a clean subagent unit: fresh window, brief per `references/playbooks/delegation-briefs.md` (goal, exact file paths, locked tokens, verify gates as the completion condition), one writer per file. The orchestrator never pastes registry JSON — only picks and diffs.

## Citations

`10-design-assembly` (this file) vs conversion-audit's `10-design-execution` — cite by filename stem when the pack matters.

## Pitfalls

- Skipping the lock → every section drifts; the "random" becomes incoherent.
- Curating nothing: `data/items/*.jsonl` generated catalogs have no tags; section quality comes from `overrides.jsonl` curation (add your own `{"id": ..., "section": [...], "tags": [...]}` lines).
- A `NO TAG MATCH` warning is not noise: it means section/registry-variety weights alone chose the pick — vet it against the brief before presenting it.
- `{style}` placeholders (reui): bake a concrete style into the namespace (`.../r/base-nova/{name}.json`) — the CLI substitutes your `components.json` style into `{style}`, which is not a ReUI `<base>-<variant>` and is not served; `onboard` defaults to `base-nova`. Verify at first use.
- Treating picks as final — the picker proposes; the lock + gates are what make it right.
