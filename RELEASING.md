# Releasing

1. Tests green: `python3 -m unittest discover -s skills/deckhand/tests` · `python3 -m pytest skills/deckhand/ops/tests -q` · `node --test skills/deckhand/tryon/test/*.test.mjs`
2. Bump the version in `skills/deckhand/SKILL.md`, the README badge and a new top entry in `CHANGELOG.md`.
3. `python3 scripts/version_check.py --tag vX.Y.Z` → VERSIONS OK.
4. `python3 scripts/leak_sweep.py` (private terms in `~/.deckhand/private-terms.txt`) → clean.
5. Rebuild the component catalog when registries changed: `node skills/deckhand/tryon/catalog-build.mjs` (network).
6. Tag + GitHub release with ≤ 8 user-facing bullets.
