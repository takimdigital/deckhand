# Changelog — deckhand-profile

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
