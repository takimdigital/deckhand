---
name: deckhand-profile
description: "Use when creating or reading the portable user profile."
version: 0.1.0
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

1. Draft every field you can already infer from the session/context — do not re-ask what you know.
2. Ask ONLY the missing fields: one batch, ≤ 8 questions, each with a proposed default.
3. Write `~/.deckhand/profile.md` from `templates/profile.md` — ≤ 60 lines, only fields that change agent behavior.
4. Show it to the user. Tell them: it is theirs — editable by hand, copyable to any harness or machine.
5. No secrets, ever: account references (emails, handles, provider names) yes — tokens, passwords, keys NO.

## Update flow

- "Add X / change Y in my profile" → edit that field only; show a one-line diff.
- When a session produces a durable user-level decision (provider chosen, DNS moved, default set):
  offer to record it — one line, yes/no. Never silently.
- Project facts do NOT go here: ids, access, per-app secrets belong to the app's `OPS.md` (vps-ops ref 30 §9).

## Boundaries

- Harness profiles/memory (Hermes USER.md, editor settings) are local to one harness; this file is portable
  and user-owned — the source of truth for pipeline facts.
- Keep it small: only fields that change behavior. Garbage in = tokens burned forever.
- Field table + example: ref `10-format.md`. Template to copy: `templates/profile.md`.
