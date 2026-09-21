# 10 — Design Assembly (coherent-random, lock-first)

Load when: the UI must be designed/built, or the user says "design this site / make it look good".

The problem: raw AI design output is slop (same hero, same purple gradient, same three cards), and users burn hours fixing it back and forth. The fix: **coherent randomness** — pick real components from live MIT registries at random *within* a locked design identity, so variety never breaks coherence.

## Phase 0 — Brief (one batched round, skippable, defaults apply)

Ask once, option-style, separate from the task. Questions:

1. What are you building + who is it for? (free text)
2. Pick 2 vibes: editorial · brutalist-lite · soft-tech · playful · luxe-dark · crisp-minimal
3. Palette: preset | your brand colors | **seeded surprise** (default)
4. Typography: 3 curated pairings | **seeded surprise** from the OFL pool (display + body; OFL/SIL only)
5. Density: compact / **comfortable** / airy
6. Motion: none / subtle / **medium** (+ budget: ≤3 animated components per page)
7. Randomness dial: safe / **coherent-random** / adventurous
8. Bans: colors/motifs to avoid (optional)

## Phase 1 — Lock

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

Then set the tokens in the project's single token file (CSS variables). **The lock is the coherence source: color, fonts, radius, motion, density are decided once and every later component inherits them.** Record the seed (same seed + same inputs = same picks, reproducible).

## Phase 2 — Assemble, section by section

Blueprint (marketing): nav · hero · logos/social proof · features · product shot · how-it-works · testimonials · pricing · FAQ · CTA · footer. (App: shell, dashboard cards, tables, forms, settings, empty states, auth screens, 404.)

For EACH section:

1. **Freshness:** `py scripts/registry_sync.py check` → if stale, `sync`. Ensure `data/items/*.jsonl` catalogs exist (`onboard <@ns>` if missing).
2. **Candidates:** `py scripts/assemble_pick.py --section <s> --tags <brief tags> --k 3 --seed <lock.seed + section index>`
   - Weighted: section match, tag match, registry variety, smaller size preferred. Deterministic per seed.
   - Present the 3; user picks, or "pick for me" → candidate #1. (Safe dial = always #1.)
3. **Install:** `npx shadcn@latest add <target>` (target comes in the pick; or add the registry namespace to `components.json` first: `"registries": { "@reui": "https://reui.io/r/radix/{name}.json" }` → then `add @reui/<item>`; or ask the harness's shadcn MCP server to "add X from @ns").
4. **Apply the lock:** ensure the component consumes the token variables; if the item ships its own `cssVars`, remap them to the lock's variables; if it hardcodes colors → small retokenize edit, or reject the candidate.
5. **Verify gates** (below), then record in `lock.sections[<s>] = { id, registry, url, pickedAt }` and continue.

## Phase 3 — Verify gates (per section; then per page)

```bash
npm run build                                                     # must pass
rg -n --pcre2 '#[0-9a-fA-F]{3,8}\b' src --glob '!*.css' --glob '!*.svg'   # expect: nothing in section components
rg -n "var\(--" src/components/<section>*                          # expect: tokens in use
```
Plus manual: keyboard pass on interactive elements; contrast ≥4.5:1 for **every text/background pair in BOTH schemes** — light AND dark, and check *fills*, not just text on page background (a bright accent used as a button fill with white text is the classic dark-mode AA miss); ≤`maxAnimatedPerPage` animated components; `prefers-reduced-motion` respected.

## Anti-slop banlist (defaults; overridable in the brief)

- No purple→blue gradient hero on near-black. No glow-everything. No centered-everything — vary alignment across sections.
- ≤3 animated components per page; ≥3 different registries across a page (variety) while tokens keep coherence.
- No lorem ipsum shipped; no fake "trusted by" logos; max 2 font families (+mono).
- ≤6 features per row, grouped meaningfully (no icon soup); one accent color; consistent radius.
- Components must be token-based (themeable) or they get rejected/retokenized.

## Delegation

Applying a component's tokens + integration is a clean subagent unit: fresh window, brief per `references/playbooks/delegation-briefs.md` (goal, exact file paths, locked tokens, verify gates as the completion condition), one writer per file. The orchestrator never pastes registry JSON — only picks and diffs.

## Pitfalls

- Skipping the lock → every section drifts; the "random" becomes incoherent.
- Curating nothing: `data/items/*.jsonl` generated catalogs have no tags; section quality comes from `overrides.jsonl` curation (add your own `{"id": ..., "section": [...], "tags": [...]}` lines).
- `{style}` placeholders (reui): bake a concrete style into the namespace (`.../r/radix/{name}.json`); verify at first use.
- Treating picks as final — the picker proposes; the lock + gates are what make it right.
