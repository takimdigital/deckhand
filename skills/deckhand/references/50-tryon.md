# 50 — TRY-ON (live section/component swap, zero model calls per click)

**Objective:** the owner compares real, licensed alternatives for any part of their running site — in
their colours, with their words — and keeps one. **Done:** no open session. **Gate G3:** design approved.

## Operate
```bash
T="node <skill>/tryon/cli.mjs"
$T doctor --project .          # framework, wiring, dev server, stamps in HTML, tokens
$T setup  --project .          # dev-only stamp loader (next.config / vite.config wrapped once, journaled)
# restart the dev server, then:
$T serve  --project .          # prints http://127.0.0.1:3999 — give THIS URL to the owner (background it)
```
The owner: click **Try-on** (bottom right) → click any section/button → confirm what it is (hero, pricing,
cta…) → **Show variants** → ←/→ to compare (instant) → **Keep** (Enter) or **Discard** (Esc) → optional
**Save to my library** (ranks first next time). The agent does nothing per click; do not poll.

Headless (no browser in the harness, or scripted):
```bash
$T query --slot hero --project .                                   # ranked candidates, no writes
$T try --file components/hero.tsx --line 6 --col 5 --slot hero --count 4
$T show --id <S> --idx 2      # the dev page now shows variant 2
$T keep --id <S> --idx 2      # or: discard --id <S>   (byte-exact restore)
```
`--no-install` refuses candidates needing new npm packages instead of installing them.

## What the engine guarantees
- Location: every JSX element carries `data-dh="file:line:col"` in dev (AST, vendored parser — works with
  TypeScript 7 projects); the overlay resolves the clicked node and its owners.
- Candidates: `data/components.index.json` (738 MIT items), ranked by slot, primitive base (a Radix project
  never gets Base UI code), missing deps, personal library first, then design diversity.
- Theme: palette classes → the project's semantic tokens; the site's own `components/ui/*` primitives are
  reused; a site without tokens gets a token layer derived from its own background/foreground + measured accent.
- Content: headings, text, prices, buttons+links, images, inputs and `.map()` list data are transplanted by
  role/order; repeated cards pair item by item; extra demo buttons/cards hide; brand-logo rows and stock
  photos never pass as the owner's. The bar shows the fit ("your content 8/8") and dashes any demo copy.
- Keep: wrapper collapses to one component under `components/sections/<slug>/`, literal copy baked in,
  show/hide switches resolved, unused files pruned, `THIRD_PARTY_NOTICES.md` updated.
- Production: stamps are dev-only (`dh verify` row `prod-clean`); `$T clean` unwires before release
  (the token layer stays if a kept section uses it).

## Troubleshooting
| symptom | cause → fix |
|---|---|
| bar says "page did not update" | compile error in the dev server log → fix or Discard; `dh learn match --log .deckhand/dev.log` |
| no stamps (`doctor: stampsInHtml false`) | dev server not restarted after `setup` |
| HMR blocked / "Blocked cross-origin request" | open the helper URL (it rewrites Origin to localhost), not 127.0.0.1:3000 |
| `NO_CANDIDATES` | slot mislabeled, or base mismatch (`hidden` count) — pick the right slot |
| `POOR_FIT` skips | the design cannot hold ≥50% of the owner's content — honest skip, try More |
