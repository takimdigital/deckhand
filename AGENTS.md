# AGENTS.md — Deckhand

This repository is an agent skill. If your harness does not load `SKILL.md` folders automatically:

1. Read `skills/deckhand/SKILL.md` (the operating specification, ~150 lines).
2. Run `python3 skills/deckhand/dh.py next` (`py` on Windows) and do what it prints — it names the single
   reference file to load for the current phase.

Working ON this repository (not with it):
- Tests: `python3 -m unittest discover -s skills/deckhand/tests` · `python3 -m pytest skills/deckhand/ops/tests -q`
  · `node --test skills/deckhand/tryon/test/*.test.mjs` (offline; registry responses are fixtures).
- Stdlib-only Python, zero-dependency Node (the only vendored code is `tryon/vendor/babel-parser.cjs`, MIT).
- Every behaviour change ships with a test; a fix that lives only in prose is not a fix.
- `python3 scripts/version_check.py` before tagging; `python3 scripts/leak_sweep.py` before publishing.
