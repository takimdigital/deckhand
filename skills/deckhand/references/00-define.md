# 00 — DEFINE (the only interview)

**Objective:** a complete `.deckhand/brief.json` + the run's mode and path, in ONE owner round-trip.
**Inputs:** `~/.deckhand/profile.json` (`dh profile show`), `dh profile doctor`, whatever the owner already said.
**Output:** `dh phase done define` green.

## Procedure
1. `dh profile doctor` — record what access exists. Profile fields are answers: never ask them again.
   No profile → create it in the same batch (only fields that change behaviour; no secrets).
2. Draft every brief field you can infer from the conversation; mark inferred ones in `assumed[]`.
3. Ask the rest in ONE message, each question with a proposed default:

| # | field | ask (plain words) | default |
|---|---|---|---|
| Q0 | mode | "Step by step (I stop at 4 checkpoints) or end-to-end?" | `phased` |
| Q1 | path | "Start from a proven open-source app, from your own saved base, from your existing site/repo, or from scratch?" | `pool` (or `mine` if the personal pool has a fit) |
| Q2 | business | "What does it do, in one line?" | — |
| Q3 | shape | saas · marketplace · booking · catalogue · leadgen · internal (suggest one) | inferred |
| Q4 | audience + market + languages | "Who buys, where, in which languages?" (ar/he/fa/ur ⇒ RTL) | profile languages |
| Q5 | features (day one) | accounts · payments · booking · admin · i18n · search · notifications · files · blog | from shape |
| Q6 | brand | name, tagline, colour, logo (or "derive it") | derive |
| Q7 | money | subscription · one-off · commission · invoice · not yet | — |
| Q8 | content | "Do you have real copy/photos, or should I draft and you correct?" | draft-then-correct |
| Q9 | hosting | own VPS + domain · free preview ($0: Oracle + free domain, or no domain: Coolify's generated URL) · undecided | profile |

4. Write it: `dh brief set business="…" shape=… languages=fr,en audience="…" features=… brand.name="…"`.
   `dh init` first if there is no run (`--mode`, `--path` from Q0/Q1).
5. Read back a 5-line summary, then `dh phase done define` and continue (no gate here).

## Rules
- MUST NOT ask for a fact the profile, the brief, the repo or a token can answer.
- "You decide" ⇒ take the default, add the field to `assumed[]`, say so in the read-back.
- Hosting on an existing VPS: capture RAM/vCPU now (Coolify floor: 2 vCPU / 2 GB; 4 GB comfortable).
- `path=existing`: `dh adopt <path|url>` is allowed during define (read-only analysis of their code
  answers half the brief); nothing is modified before G2.
- Lead-gen (plumber, lawyer, bakery site): fully supported — `path=scratch` + `dh compose` builds it from
  licensed marketing blocks; the pool is for software-shaped apps.
