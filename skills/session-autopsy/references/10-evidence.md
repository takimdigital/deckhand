# 10 — Evidence collection (cheap) + routing

**Purpose:** assemble the failure record with minimal tokens, in any harness.
**Truth tag:** Hermes transcript access live-verified; other-harness paths marked [verify].

## 1. Collection order (stop as soon as the chain is provable)

1. The fix — `git log` window + the fixing commit's diff. Shortest path to "what was wrong".
2. The verbatim errors — grep, never full reads.
3. The attempts — the user's own words (interview mode §4) if available.
4. Only if 1–3 are ambiguous: the raw transcript.

## 2. Artifact commands

```bash
git log --oneline -15                        # red→green window; the fix is near the tip
git show <fix-sha> --stat                    # what actually changed
gh run list --repo <o>/<r> --limit 8         # CI: first red → last green
gh run view <run-id> --log-failed | tail -40
ssh <host> "docker logs --tail 100 <container>"
```

Transcript stores, when needed: Hermes `session_search`; Claude Code `~/.claude/projects/*.jsonl`;
Codex `~/.codex/sessions/` [verify per harness].

## 3. Transcript extraction (grep, not read)

Grep the JSONL for the strings that matter, then read ±5 lines around each hit:

```
error|failed|ERR_|refus|denied|not found|timeout
```

Collect exactly: first error line verbatim · the command that produced it · the command that fixed it.

## 4. Interview mode (no transcript)

One batch, ≤ 6 questions:
1. What did you expect, and what happened?
2. Paste the exact error line(s).
3. What fixed it?
4. What did you try first that didn't work?
5. Which skill/tool was running?
6. What would you tell the next person?

## 5. Classification — route before fixing

| Finding | Route |
|---|---|
| Our instruction / default / order led the agent wrong | fix the skill (ref 20 ladder) |
| Environment quirk, not designable away | pitfall + automate if possible; counts as debt |
| The app itself is broken | `systematic-debugging` + the app repo |
| One-off action with no pipeline step involved | the app's status doc; no skill change |
