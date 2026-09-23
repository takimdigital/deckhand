# 40 — Rebrand (make it theirs, keep the license)

Fill `.factory/brand.json`, inject at the **measured** points, prove nothing of the template is left
visible. Design comes from the template; this phase never redesigns.

## brand.json

```json
{
  "name": "…", "tagline": "…",
  "locale_default": "fr", "locales": ["fr", "ar"],
  "palette": {"accent": "#…", "ground": "#…", "ink": "#…"},   // tokens, not per-component colors
  "fonts": {"latin": "…", "arabic": "…"},                      // optional; keep the template's if unsure
  "logo": "public/…", "voice": "plain, local, no hype"
}
```

If the owner has no palette/fonts: derive them **from the template's own tokens** (shift hue, keep the
ramp). Do not import a new design system — that is how the old pipeline burned its budget.

## Injection points

Use `rebrand_surface` from the registry row (measured at intake: logo/icon files, `globals.css`,
theme/config/constants, `messages/*`). If a point is wrong, fix the **registry row**, not just the
project — the next run inherits the fix.

Order: identity (name, logo, favicons, metadata) → tokens (palette/fonts/radius) → copy
(headlines, sections, emails, legal pages) → locales (default + RTL if asked).

## The leak check (the defect owners hate most)

```
grep -ri "<template-name>" --exclude-dir=node_modules --exclude-dir=.git -l .
```
Zero hits outside `LICENSE` / `NOTICE` / `.factory/`. Also: the template's demo domain, demo user
names, stock photos, "built with <template>" badges, README screenshots, and its sample content.
The owner paid for a business, not a themed demo.

## License duties (non-negotiable)

Keep the template's `LICENSE` file and add the upstream line to `NOTICE` (name + URL + commit).
MIT/Apache is the only reason the pool is legal to use — deleting the notice breaks it.

## Content

Real copy per section from the intake (draft-then-correct if the owner asked for drafts).
No stock photos (real ones or none), no invented numbers, reviews, certifications or logos.
Anything the owner must confirm goes to `PENDING.md`, never into the page as a fake fact.

## Visual sanity (6 rows, checked by eyes — not a redesign gate)

Use `templates/qa/{probe.html, frame.html, cdp.mjs}` + screenshots read by vision. Sizes/tokens, not opinions.

| # | check | pass looks like |
|---|---|---|
| 1 | first fold at 390 | name + what it does + one action visible without scrolling |
| 2 | overflow at 320/390/1280 | 0 horizontal overflow (`probe.html`) |
| 3 | text floor | body ≥16px, no shrunken mobile text |
| 4 | contrast on rebranded tokens | text/CTA readable; the accent survives on light and dark ground |
| 5 | no dead interior | no panel/section that is mostly empty space where content is expected |
| 6 | no template leftovers | leak check clean (above) |

Anything failing → fix that row, re-shoot, re-read. Do not add a seventh row "because it looks off":
that road rebuilt the old machine.
