# Releasing this repo (it is PUBLIC)

Load the `skill-pack-publishing` skill and follow it — this file is only the checklist at the point
of action; it exists because release text is written mid-context, which is exactly when private
names slip in.

1. **Gate first (hard stop).** `py scripts/leak_sweep.py` → must exit 0. It scans the repo tree,
   the commit history and every harness copy for the private terms listed in
   `~/.deckhand/private-terms.txt` (that list itself is never stored here).
2. **Tests.** Every skill suite green; totals match the README badge.
3. **Sync.** Working install (hermes) → repo `skills/` → `~/.claude`, `~/.agents`, `~/.codex`;
   diff each for parity; strip `__pycache__` / `.pytest_cache`; bump versions together
   (frontmatter, CHANGELOG top entry, README badge) — then PROVE it mechanically:
   `py scripts/version_check.py` → must print `VERSIONS OK`. The README badge is the one version
   location nothing else touches; it has silently lagged a release (live-hit 2026-09-21).
4. **Zip == repo — byte-level.** Rebuild the distributable zip from the repo root (publishing
   skill's builder) and verify EVERY entry is byte-identical, not just present:
   `py scripts/zip_parity.py "C:/Users/Takim/deckhand.zip"` → must print `PARITY OK`.
   Count parity is not parity — it passed a stale-content zip for two releases.
5. **Notes.** Write release notes to a file — improvements + fixes only, ≤ 8 user-facing bullets,
   no internal narration, no project provenance — then gate the draft:
   `py scripts/leak_sweep.py --file <notes.md>` → must exit 0.
6. **Ship.** `git add -A && git commit`; push `main`; `git tag vX.Y.Z && git push origin vX.Y.Z`;
   `gh release create vX.Y.Z <zip> --notes-file <notes.md>`; verify the newest release is flagged
   **Latest** with the zip attached; then re-run `py scripts/version_check.py --tag vX.Y.Z` (must
   print `VERSIONS OK` — catches a badge that lagged the tag).

If a leak ever ships anyway: fix the text, rewrite history messages, force-push `main` + tags,
`gh release edit` each affected release, re-scan every attached zip — full recipe in the
`skill-pack-publishing` skill's "Public docs" section.
