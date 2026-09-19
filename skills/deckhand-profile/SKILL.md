---
name: deckhand-profile
description: "Use when creating or reading the portable user profile."
version: 0.1.1
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [profile, user, portability, defaults, accounts, preferences]
    related_skills: [vps-ops, buildout, session-autopsy]
---

# deckhand-profile — one portable file that IS the user

`~/.deckhand/profile.md` holds what the pipeline needs to know about the USER — accounts, providers,
defaults, preferences. Harness-independent, user-owned, human-editable. Copy this one file to any
machine or any agent and the user never re-answers these questions.

## Read-first rule (every skill, every session)

Before asking the user anything about accounts, providers, domains, defaults or preferences: read
`~/.deckhand/profile.md`. Fields present there are DONE — never re-ask them.
If it does not exist: continue normally and offer to create it once (never mid-task).

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
- **Living file:** after real work (a deploy, a provider chosen, a repo created, a preference stated) offer the
  one-line update — a yes/no, never silent. An answer the user gave becomes a line; a guess never does.
- Project facts do NOT go here: ids, access, per-app secrets belong to the app's `OPS.md` (vps-ops ref 30 §9).

## Boundaries

- Harness profiles/memory (Hermes USER.md, editor settings) are local to one harness and are NEVER a source
  for this file; this file is portable and user-owned — the source of truth for pipeline facts.
- Keep it small: only fields that change behavior. Garbage in = tokens burned forever.
- Field table + example: ref `10-format.md`. Template to copy: `templates/profile.md`.
