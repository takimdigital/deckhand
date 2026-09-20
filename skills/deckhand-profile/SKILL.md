---
name: deckhand-profile
description: "Use when reading or writing the portable user files. Covers profile.md + pending.md (the human-task ledger)."
version: 0.2.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [profile, user, portability, defaults, accounts, preferences, pending, reminders]
    related_skills: [vps-ops, buildout, session-autopsy]
---

# deckhand-profile — the user's portable files: profile + pending

Two small files, both harness-independent, user-owned, human-editable — copy them to any machine or agent:
- `~/.deckhand/profile.md` — what the pipeline needs to know about the USER (accounts, providers, defaults).
- `~/.deckhand/pending.md` — the ledger of things ONLY the human can do, with states and dates; agents nag until closed.

## Read-first rule (every skill, every session)

Before asking the user anything about accounts, providers, domains, defaults or preferences: read
`~/.deckhand/profile.md`. Fields present there are DONE — never re-ask them.
Also read `~/.deckhand/pending.md`: while open items exist, every report back to the user ends with the
open list (short, with ages). If a file does not exist: continue normally and offer to create it once (never mid-task).

## The pending ledger — `~/.deckhand/pending.md`

When to write: the moment a human action appears — a key to paste, a click/consent only they can give,
a password to escrow or rotate, an account only they can create. Record it in the same message where
you ask; NEVER keep human tasks only in chat history.

Format (strict — agents parse it):
`- [ ] P-0NN · <what> · WHY: <consequence if skipped> · HOW: <one line / link> · asked YYYY-MM-DD · status: open|waiting-confirm · nag: yes|no`
(optional `· project: <name>`, `· when: <trigger>` for conditional items)

Rules:
- `status: open` = user hasn't done it; `waiting-confirm` = likely done but not confirmed; both nag — unless `nag: no` or a `when:` trigger hasn't fired yet.
- `when:` items never nag before their trigger — no noise.
- Close = `- [x] … · done YYYY-MM-DD`, moved to `## Done` (keep only the last few; the ledger stays short).
- Dropped = `- [x] … · dropped YYYY-MM-DD · reason` — never silently delete.
- Nagging: surface open items in every deploy/ops report (short) and in scheduled runs; when the user
  says "done", verify when verifiable (re-check the env var, the object, the key) — otherwise confirm on their word.
- **Never drop an item because the conversation moved on.** That is the one failure this file exists to prevent.

Template to copy: `templates/pending.md`.

## Create flow — user says "create my deckhand profile"

**Source rule (both branches):** build the profile ONLY from (a) this workspace/session — the actual work and
chat — and (b) the user's answers. Never import from harness profiles, memory files, or other tools' data:
this file must not inherit another system's guesses. Unknown field → omit it, never invent.

**Branch A — context exists** (work or chat in this session/workspace):
1. Draft every field you can infer from it; list what you inferred for a quick yes/no.
2. Ask ONLY the missing fields — one batch, each with a proposed default.
→ then write (below).

**Branch B — cold start, nothing known (the common case, ~90%):**
1. Say it plainly: "there's nothing about you on file yet — you haven't worked in this workspace, so I'll ask."
2. Run the **initial interview**: one batch, the starter set in `references/10-format.md` order
   (identity → accounts → defaults → constraints), every question with a proposed default so answers are fast.
3. The answers ARE the initial profile. Skipped = omitted. No placeholders, no guesses.

**Write (both branches):**
3. Write `~/.deckhand/profile.md` from `templates/profile.md` — ≤ 60 lines, only fields that change agent behavior.
4. Show it to the user. Tell them: it is theirs — editable by hand, copyable to any harness or machine.
5. No secrets, ever: account references (emails, handles, provider names) yes — tokens, passwords, keys NO.

## Update flow

- "Add X / change Y in my profile" → edit that field only; show a one-line diff.
- "Remember that I still need to …" / "done with P-00N" → write or close the item in `~/.deckhand/pending.md` immediately; show the one-line change.
- **Living file:** after real work (a deploy, a provider chosen, a repo created, a preference stated) offer the
  one-line update — a yes/no, never silent. An answer the user gave becomes a line; a guess never does.
- Project facts do NOT go here: ids, access, per-app secrets belong to the app's `OPS.md` (vps-ops ref 30 §9).

## Boundaries

- Harness profiles/memory (Hermes USER.md, editor settings) are local to one harness and are NEVER a source
  for this file; this file is portable and user-owned — the source of truth for pipeline facts.
- `pending.md` is NOT an agent todo list — agent work stays in the session/kanban; only things the HUMAN must do belong here.
- Keep it small: only fields that change behavior. Garbage in = tokens burned forever.
- Field table + example: ref `10-format.md`. Template to copy: `templates/profile.md`.
