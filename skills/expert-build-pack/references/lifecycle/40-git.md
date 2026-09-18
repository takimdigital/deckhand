# 40 — Git: history as evidence

Load when: setting branch/commit conventions, opening PRs, cutting releases, or running parallel agents on one repo.

## Constraints (hard)

- `main` is always deployable (protected; CI gates before merge).
- Branches are short-lived (≤ ~2 days); long work ships behind flags instead.
- No secrets in history — ever (scan before first push; rotate if it ever happened).
- No force-push to shared branches.
- Every change reviewed (or solo: self-review against a checklist) before merge.

## Procedure

1. Branch off `main` with a descriptive name (`feat/email-rotation`, `fix/lock-wait`).
2. Commits: small, atomic, imperative mood ("add concurrent index for users.email"); conventional prefix optional but consistent.
3. PR body answers: why (not just what), how it was verified (command + result), what could break + rollback note. UI changes: before/after.
4. CI gates: lint + typecheck + tests. No bypass.
5. Merge: squash by default; delete branch after.
6. Release: tag semver + changelog entry; tag = the deployable artifact reference.
7. Hotfix path: smallest possible branch off the release tag, fast-track review, backport to main.
8. **Parallel agents:** one worktree + one writer per branch; never two writers on one branch; partition by file ownership.

## Anti-patterns

- Long-lived feature branches (merge pain + stale state).
- Giant PRs mixing refactor + feature + formatting.
- Force-pushing shared branches; rewriting published history.
- Committing `.env`, keys, dumps; "fix tests later" merges.
- Parallel agents stepping on each other's files (unmerged-writes failure mode).

## Jargon

trunk-based development · conventional commits · PR/MR · squash vs rebase · semver · release tag · changelog · hotfix · backport · worktree · protected branch · artifact.

## Verify

- Branch protection + CI gates active (screenshot/config as evidence).
- Recent PRs within size/time heuristics.
- `git log` reads as atomic, meaningful history.
- Secret scan clean.
