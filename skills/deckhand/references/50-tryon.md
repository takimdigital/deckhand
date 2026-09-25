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

## No licensed design fits? The AI draft (labelled, gated)
The owner can ask for an AI-written variant: "Ask AI to draft one" appears when a slot has no licensed
design, when none can hold their content (`NO_CANDIDATES` / `NO_VARIANTS`), and as **AI draft** in the
variant bar (it then joins the licensed variants being compared). You are called once per request, never per click:
```bash
$T drafts --project .            # pending requests; `--wait` blocks until one exists (background it, no polling)
# read brief_file → "brief": the owner's exact content (text, markup, links, images, lists), the note,
# the project's primitives/packages and the rules. Write the component into write_to/draft.tsx, then:
$T draft-check --id <D>          # optional dry run of the gates
$T draft-done  --id <D>          # gate → staged beside the other variants → the owner's page switches to it
```
Gates (a failure lists every problem; fix and re-run `draft-done`): every owner word, link target, image
and bullet present · token colour classes only (no hex/rgb/hsl/oklch, no `bg-[#…]`) · imports = react,
next/*, the project's ui primitives/utils, installed packages · images = the owner's or the placeholder ·
links = the owner's hrefs only · no fetch / env · `.tsx`/`.ts` files only. Words you add beyond the
owner's are allowed only as short UI copy, and are shown as "its own words" and recorded with `ai: true`;
`dh rebrand check` warns (does not block) until the owner confirms or rewrites them. Never invent facts
(prices, numbers, names, reviews, logos, dates). The variant is labelled AI-generated in the bar; its file
header says so on keep; no third-party licence notice is written for it.

## A registry the owner found
`$T registry vet --index https://x.dev/r/registry.json --repo owner/name` → accepted or refused with reasons
(not on the refused list · permissive licence evidenced by the source repo · shadcn schema · items that map
to slots · sampled items download with their source: a 401/402/403 or a content-less "pro" item is a
paywall). `registry add` indexes it into `~/.deckhand/catalog/` — it ranks beside the shipped catalog.
`registry list` / `registry remove --id x`.

## What the engine guarantees
- Location: every JSX element carries `data-dh="file:line:col"` in dev (AST, vendored parser — works with
  TypeScript 7 projects); the overlay resolves the clicked node and its owners.
- Candidates: `data/components.index.json` (738 MIT items), ranked by slot, primitive base (a Radix project
  never gets Base UI code), missing deps, personal library first, then design diversity.
- Theme: palette classes → the project's semantic tokens; the site's own `components/ui/*` primitives are
  reused; a site without tokens gets a token layer derived from its own background/foreground + measured accent.
- Content: headings, text, prices, buttons+links (CTA to CTA, link to link), images, inputs and `.map()`
  list data are transplanted by role/order; repeated cards pair item by item (twin rows of the same card
  shape count as one list; the row that fits the owner's count wins, unused rows hide whole); two-tone
  headings take the heading in the bright half and a subtitle, or nothing, in the muted half; extra demo
  buttons/cards hide; brand-logo rows, stock photos and the design's `©` never pass as the owner's.
- Honesty: a design form (newsletter, "enter your email") is hidden unless the slot is a form page
  (contact, login, signup) or the owner's element has one; footer/navbar menus come from the plan
  (`.deckhand/sitemap.json` nav + page titles) and social rows keep only the owner's networks
  (`brief.brand.social`). The bar shows the fit ("your content 8/8") and dashes any demo copy that is left;
  keep records it in `.deckhand/demo-copy.json`, which `dh rebrand check` blocks on until rewritten.
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
| `POOR_FIT` skips | the design cannot hold ≥50% of the owner's content — honest skip, try More, or the AI draft |
| `DRAFT_REJECTED` | read `problems`, fix the draft files, run `draft-done` again (the owner's page is untouched until it passes) |
