# Changelog — deckhand-profile

## 0.3.3 — 2026-09-22

- First-run clarifications from a first-user field test: the read-first rule now says WHEN the create offer happens (next natural pause, never mid-task, never twice in one session — and neither file existing is the normal first-run state); a Windows `~` note (`C:\Users\<you>`) sits next to the paths; the project-ledger bullet now seeds **the moment the project directory exists** (a pre-scaffold "kickoff" has no directory yet) and links the field table (`10-format.md`).

- Cold-read audit fixes (pre-release, same batch): on READ, an item missing `WHY:`/`HOW:` is tolerated (never dropped or mis-filed) while writes stay strict; `status` + `nag` declared required (a missing `nag:` reads as `yes`); **the checkbox, not the heading, is the state of record** (misfiled closed items get moved when touched; `## Done` pruning always keeps the newest line so IDs can't be reused); decision-items legalized (`decide: <question> (rec:)` + `DECISION NEEDED` re-surface); a future agent action rides its trigger item as a `→ then:` note — never a standalone item; `## Decided, not built` defined in SKILL.md and added to the template; IDs are per-file across ledgers; ages are whole days from `asked` to today's local date; a declined create-offer with no ledger yet is re-offered at most once per NEW session; `private-terms.txt` documented; ref 10's field table declared a STARTER set (never delete a field you don't recognize).

## 0.3.2 — 2026-09-22

- Ledger IDs pinned: `P-001`, zero-padded, next = highest existing + 1, never reused.
- Report ages defined: whole days open from `asked` (`open 6d`).
- Onboarding's write-up steps became a checklist (they collided with the Branch B step numbering).

## 0.3.1 — 2026-09-21

- **Project-scoped tasks find their own home:** human tasks discovered by work inside ONE project (its accounts, keys, client-supplied data, policy decisions) now go in a `PENDING.md` at that project's root — created at kickoff by the buildout flow, same strict format as this ledger. This portable ledger keeps cross-project items and the user's own infrastructure/accounts; both-roles items keep `· project: <name>` here.

## 0.3.0 — 2026-09-20

- **Access before asks (new section):** inventory profile §Access map + project `OPS.md` + vault + Coolify envs before asking anything; if existing access can do it — DO IT; missing access = ONE batched ask (exact scope + click path + where to save), ledgered in the same message; capability walls are proven with a probe, never assumed.
- **Labeled asks:** every ask is `DECISION NEEDED —` / `ACTION NEEDED —` / `FYI —`; questions are never ledger items (the ledger holds only tasks the human performs); an unclear ask is a defect (re-issue it labeled, with steps + WHERE).
- **Deferrals are decisions:** "later / not now" → recorded with `when: <trigger>`, never re-asked in the same or later sessions.
- `profile.md` gains an **Access map** section (locations + scopes, never values) — template + live file.

## 0.2.2 — 2026-09-20

- Fresh-eyes audit fixes: read-first scope widened to **“before starting any work”** (was “before asking”); **`asked` declared REQUIRED on every open item** (conditional included) — rules + template aligned; profile guidance sharpened: run session-autopsy after *pipeline* failures (a retry, red run, or missed step — not every app bug).

## 0.2.1 — 2026-09-20

- **`WHERE:` joins the item format** (after HOW): the exact place to find the thing — a full file path,
  a URL, or a menu chain (“Coolify → app → Environment variables”). Non-tech users don't know where to
  look; this field removes the last excuse. HOW = what to do · WHERE = where to find it. Template +
  rules updated.

## 0.2.0 — 2026-09-20

**The pending ledger** — the skill now owns a second portable file besides the profile:
`~/.deckhand/pending.md`, the ledger of things ONLY the human can do. Strict machine-parsable format
(`id · what · WHY · HOW · asked date · status: open|waiting-confirm · nag: yes|no`, optional
`project:` and `when:`), lifecycle open → waiting-confirm → done/dropped, close with a date, verify
when verifiable. Read-first now covers BOTH files and every report ends with the open list while items
exist; the never-drop-because-the-conversation-moved-on rule is the core invariant. Template added at
`templates/pending.md`. Born from the first live deploy: ~10 human tasks (escrow, rotate, keys) were
scattered across chat — no more.

## 0.1.1 — 2026-09-19

Cold start made first-class (the ~90% case). The create flow now has two explicit branches:
**A — context exists** (draft from the session, ask only the gaps) and **B — cold start** (say plainly
that nothing is on file yet, then run the initial interview in one batch, defaults offered, answers
are the initial profile). New **source rule**, stated once in both the SKILL and ref 10: the profile is
built ONLY from this workspace/session + the user's answers — never imported from harness profiles or
memory files, so it cannot drift. Update flow clarified as a **living file**: one-line offers after
real work (deploy, provider chosen, preference stated); unknowns are omitted, never guessed.

## 0.1.0 — 2026-09-19

Initial release: portable user profile at `~/.deckhand/profile.md` (read-first rule, create/update
flows, format ref, fill-in template).
