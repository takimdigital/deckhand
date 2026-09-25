# 10 — RESEARCH (evidence, not opinions)

**Objective:** know what wins in THIS niche before a page is planned. **Output:** `.deckhand/research.json`
(template: `templates/research.json`), `dh phase done research` green. Owner declined → `dh phase skip research --reason "…"`.

## Specification
- **competitors (≥3, target 3–5):** real businesses serving the same audience in the same market/language.
  Per competitor: `name, url, positioning` (their one-line promise), `pricing` (shape + anchor price),
  `strengths[]` (what converts: e.g. instant quote, same-day slots, trust badges), `gaps[]` (what they miss —
  the owner's opening). Every entry has a URL you actually opened.
- **audience:** `primary` segment, `pains[]`, `jobs_to_be_done[]`, the `language` they search in.
- **conversion.plays[]:** the 1–3 moves the top performers make that the median does not (the pattern:
  90% of cleaners publish a contact form; the winners ship an instant quote calculator). `first_screen[]`:
  what must be visible without scrolling. `trust[]`: proof types that fit (reviews, guarantees, certifications —
  the OWNER must supply real ones → PENDING). `objections[]` + the answer each needs on the page.
- **discovery:** keywords in the audience's language, local-SEO relevance, the page types that rank.
- **features:** `now[]` (day one, ≤7), `later[]`, `not[]` (deliberately excluded, with reason).
- **unproven[]:** what could not be verified. Say it; never fill it.

## Procedure
1. Search in the audience's language and market (not the agent's). Open each competitor's site.
2. Budget: one pass, ≤ ~25 fetched pages. Parallel agents: at most two (A = competitors, B = audience/
   conversion/discovery), each returns JSON conforming to the template — never prose.
3. Merge into `research.json`; `dh phase done research` validates the shape.

## Rules
- MUST NOT copy competitor copy, contact them, sign up, or scrape behind logins.
- A claim without a URL is deleted, not softened.
- The research feeds the plan: every `conversion.plays[]` item becomes a section or feature in the sitemap,
  or is listed under `features.later` with a reason.
