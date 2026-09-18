# 30 — Design: tokens, states, a11y, i18n/RTL

Load when: building any user-facing surface, defining visual language, or shipping to multiple locales.

## Constraints (hard)

- **No hardcoded colors/spacing/radii** — design tokens only (single source of truth in CSS variables/theme file).
- Text contrast ≥ 4.5:1 (3:1 for large text/UI components); never communicate by color alone.
- Every interactive element has: default / hover / focus-visible / active / disabled / error / loading states; keyboard reachable.
- Performance budgets on the critical page: LCP ≤ 2.5s (p75), CLS ≤ 0.1, INP ≤ 200ms.
- Strings are externalized from day one; never concatenate sentence fragments (breaks in every non-English language).
- Layout uses **logical CSS properties** (`margin-inline`, `inset-inline-*`, `text-align: start`) so RTL works without a fork.

## Procedure

1. **Tokens first.** Color scale (semantic names: bg, surface, ink, accent), type scale, spacing scale, radius. Dark mode via tokens, not overrides.
2. **Component inventory** before building new ones (extend, don't fork).
3. **States pass.** Empty, loading, error, long-content — designed, not discovered in prod.
4. **Responsive strategy.** Breakpoints + content priority per size; test the awkward widths (320px, 375px, tablet landscape).
5. **a11y pass.** Semantics (real buttons/headings), labels, focus order, `prefers-reduced-motion`, alt text.
6. **i18n/RTL pass.** `dir="rtl"` walkthrough (not just mirrored screenshots); check icons that must mirror (arrows, chevrons) vs must not (logos, clocks); locale formats for dates/numbers/currency; pluralization rules (ICU-style, not "add s").
7. **Performance check** against budgets on the critical page.

## Anti-patterns

- Pixel-pushing before tokens; one-off hex values.
- Placeholder-as-label; div-buttons; focus outlines removed.
- Fixed pixel widths that break RTL; absolute positioning for core layout.
- Testing only LTR/English; hardcoded date formats.
- "We'll do a11y/i18n later."

## Jargon

design tokens · design system · WCAG AA · focus-visible · Core Web Vitals (LCP/CLS/INP) · reduced motion · logical properties · RTL · i18n/l10n · pluralization · empty state.

## Verify

- Token audit: zero raw hex values in component styles (grep-able).
- Keyboard walkthrough of the main flow logged.
- RTL pass done on the critical flow; strings all externalized.
- CWV within budgets on the critical page (measured, not assumed).
