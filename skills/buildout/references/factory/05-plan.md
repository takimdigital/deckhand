# 05 — Plan (phase 1: knowing the business before touching anything)

Phased mode's first gate. The deliverable is **one page** the owner reads and approves. Nothing is
matched, cloned or built before that approval — a wrong plan wastes every phase after it.

## What must be clear first

From intake: the business in one line · who it serves · languages · the must-have features · the money
model · the mode (`autonomous` | `phased`). Missing → ask; that is what intake was for. Never invent a
fact to fill a gap — an invented feature becomes a wrong build.

## Research — offer it, most owners want it (exactly two agents)

Two subagents in parallel, writing **evidence, not opinions**. Both work remotely (public web pages
and search results): never contact anyone, never sign up, never copy a competitor's copy.

- **A — competitors** → `.factory/research/competitors.json`: 5–8 real competitors serving this
  owner's audience and market. Per competitor: URL, what they sell, the features visible on their
  site, pricing shape, positioning, and what they *don't* do. Then the point of the exercise: **the
  moves the top 10% make that the rest don't** — the owner's own example is cleaning businesses:
  90% publish a contact form, the best ones win with an instant quote generator. Every claim carries
  its URL.
- **B — demand, conversion, discovery** → `.factory/research/demand.json`: who the audience is, in
  which language they search, the terms that matter, what must be visible in the first screen, the
  conversion patterns and psychology that fit THIS trade, and the current baseline (speed, mobile,
  local discovery, trust signals). URL or nothing.

If the market is local and obscure, **say what could not be found** rather than inventing it; the
plan marks those as unproven.

## The plan (one page, the owner's language)

```
# <business> — plan
## What it is            2 sentences, in the owner's words
## Who it serves         audience · languages · where they are
## Must have             ≤7 features, each with the phase it lands in
## Nice to have          parked, said out loud
## The conversion play   1–3 moves that make THIS business win (from the research)
## Discovery             the terms/pages that matter; what we wire now (titles, sitemap, speed)
## Not doing             what we deliberately won't build, and why
## Evidence              links into .factory/research/*.json
```

Rules: **≤7 must-haves**, and each one must plausibly exist in a full-app template — the pool is
built of real apps, not of promises. A plan needing everything invented is a **pool gap**: say so
plainly instead of writing fiction. Owner-only facts (domain, legal, photos) go to `PENDING.md`.

## Gate G1

Present the plan — the file, not a summary — and ask exactly one question: **approve, or what do you
want changed?**

- Approved → `10-match.md`.
- Changes → fold them in and re-present once. Two rounds is the budget; past that the difference is a
  parked "nice to have", not a blocker. Never argue with the owner about their own business.
