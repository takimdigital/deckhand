# Community workflows

Proven paths shared by Deckhand users. `dh workflow query` reads `index.json` (one row per workflow — the pool can grow
without costing any AI context) and fetches a file only when someone uses it; its hash must match the index.

## Share yours

1. Run it on a real project until a run is complete and green (`dh autopsy --workflow` shows it).
2. `dh workflow publish mine:<id>` — lints it strictly and writes a bundle to `~/.deckhand/workflows/outbox/`.
3. Fork this repo, copy the bundle to `workflows/community/<id>.json`, run `python3 scripts/workflows_index.py`.
4. Open a pull request: what it builds, the runs that prove it (harness, system, minutes, errors).

The maintainer reviews every workflow before it is merged (`proof.reviewed`). CI refuses a workflow whose commands are
not allow-listed (dh, package managers, tsc/tests, git, `curl -s`), that calls private functions, carries a user's
absolute path or a credential-shaped value, or whose `dh` commands do not exist.

Your own workflows stay in `~/.deckhand/workflows/` on your machine until you choose to publish one.
