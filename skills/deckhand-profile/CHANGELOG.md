# Changelog — deckhand-profile

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
