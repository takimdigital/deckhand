# 00 — Intake (the only interview)

Goal: capture the business in **≤10 answers**, one pass, then stop asking.
Output: `intake.json`. This file is the matchmaker's only input — keep it thin.

## Questions (ask in this order, all in one message)

1. **What the business does** — one line, in the owner's words.
2. **Shape** (the matchmaker's key). Read the options aloud; the owner picks, you may suggest one:
   - `saas` — accounts + a subscription or paid plan; the software *is* the product
   - `marketplace` — two sides (supply and demand) meet, listings + requests/orders
   - `booking` — services with time slots / appointments / reservations
   - `catalogue` — products or a menu, browse + order or enquire
   - `leadgen` — a presence site whose job is phone calls, forms, credibility (**Lane B** — see below)
   - `internal` — a tool for the owner's own team
3. **Market + languages** — country/city, and the languages the business must speak (list). Languages `ar`, `he`, `fa`, `ur` mean RTL.
4. **Brand** — name, tagline, and whether a logo/palette/fonts already exist; otherwise "derive it".
5. **Must-have features** — pick from: `accounts`, `payments`, `admin`, `i18n`, `jobs`, `search`, `notifications`, `files`, `booking`, `map`. Anything not picked is out of scope.
6. **Who operates it** — solo or team; who needs admin access.
7. **Hosting** — `vps-coolify` (default recommendation), `free-preview`, or `undecided`.
   If the owner names an existing server, capture its **RAM/vCPU** in the same answer: Coolify's floor
   is ≥2 vCPU / 2 GB (4 GB+ comfortable) and a "$5 VPS" is often below it — better surfaced now than
   at deploy.
8. **Money** — subscription, one-off, commission, invoice-by-hand, or "not yet".
9. **Content** — does the owner have real copy/photos, or must they be drafted (and then corrected)?
10. **Deadline** — a date or "no rush".

## Rules

- **One pass.** Never ask twice for the same fact. If the owner says "you decide", take the default,
  set `assumed: true` on that field, and disclose the assumption in the read-back.
- **Never invent facts** (licence numbers, testimonials, addresses). Unknown → `PENDING.md`.
- **≤10 answers, ≤2k tokens.** No essay prompts, no discovery workshop. The factory is a matchmaker, not a consultant.
- **Lane check first.** If shape = `leadgen`, say so plainly: the template pool is software-shaped today;
  a lead-gen site is Lane B and is **not** served by this pool yet. Do not force a SaaS template onto it.
- After the answers: read back a **5-line summary** and move to `10-match.md` in the same turn.

## Measuring the pool (only when the pool itself must grow)

`template_intake.py --seed …` or `--repo <owner/name>`. Two rules learned from real runs:

- **Remote only, and never two runs at once on one registry.** A run refuses to overwrite a row that
  was updated after it started (`not_before`), because two concurrent intakes were observed racing —
  the slower one finished last and rolled rows back to older measurements.
- A build that fails naming vendor keys is a **swap input**, not a pool rejection: the order is
  clone → swap → build (`--deep --yes` is the consent-gated boot test).

## intake.json

```json
{
  "business": "one line",
  "shape": "saas|marketplace|booking|catalogue|leadgen|internal",
  "niche": "field-service scheduling",
  "languages": ["fr", "ar"],
  "rtl": true,
  "brand": {"name": "…", "tagline": "…", "has_logo": false, "palette": null, "fonts": null},
  "features": ["accounts", "payments", "i18n"],
  "operators": {"count": 1, "admin_roles": ["owner"]},
  "hosting": "vps-coolify",
  "money": "subscription",
  "content": {"copy": "draft-then-correct", "photos": "none"},
  "deadline": null,
  "assumed": ["fonts", "hosting"]
}
```
