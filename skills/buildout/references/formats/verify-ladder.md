# Verify Ladder — how much a piece of evidence is worth

Load when: claiming something works, accepting someone else's claim, or designing checks for a step/subagent.

The reliability of a check depends on how close it sits to real state. Verification accelerates reasoning; only reality establishes truth.

## Ladder (strongest first)

| Level | Source | Example | Weight |
|---|---|---|---|
| 1 | Authoritative system of record | DB query, API read-back, `pg_indexes`, provider dashboard | Evidence |
| 2 | External operation identifier | webhook id, deployment id, CI run number, payment intent id | Strong |
| 3 | Durable artifact | file on disk, build artifact, test report, git commit | Medium |
| 4 | Transient feedback | success toast/banner, spinner gone, agent's own summary | Weak — never sole proof |

Rule: verify at the strongest level the task can afford, and read back *your own* effect (not just "no error"). "Do not treat done as proof: a button click is not proof a form was accepted."

## Freshness — 200 is not proof the server is serving YOUR build

Rebuilding while a local server runs replaces the chunk files under the old in-memory manifest. The
trap is silent: the port still answers **200**, the route still renders its shell, the client-rendered
part never appears and nothing is logged anywhere — so it reads as a defect in code that is fine. A
failed restart does say so (`EADDRINUSE: address already in use`), but only in the process you are not
reading. Before trusting any local measurement (verified in both states 2026-09-20):

```bash
# 1. free the port and CONFIRM it — a restart that failed leaves the old process serving happily
netstat -ano | grep ':<port>' | grep -i listen | awk '{print $NF}' | sort -u   # empty = free
# 2. after starting, check the HTML being served against the files on disk
stale=$(curl -s http://127.0.0.1:<port>/<route> | grep -o '/_next/static/[^"]*\.js' | sort -u \
  | while read -r u; do curl -s -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:<port>$u"; done | grep -vc '^200$')
[ "$stale" -gt 0 ] && echo "STALE: $stale chunk(s) in the served HTML are not on disk" || echo "OK"
# 3. then assert one marker only the NEW build renders (client-rendered content, not HTTP 200)
```

Observed in a real run: rebuild-under-running-server → `STALE: 1 chunk(s) in the served HTML are not
on disk`; after kill + restart → every referenced chunk 200. A route can also answer **500** for the
missing chunk instead of 404 — count any non-200 as stale. Windows/MSYS: `taskkill /F /PID <pid>`
takes SINGLE slashes — `//F` is passed through literally and rejected (`Invalid argument/option - '//F'`).

## Verdicts (three-state, no silent defaults)

- `CONFIRMED` — the check ran and passed (record the exact command + result).
- `REFUTED` — the check ran and failed (record evidence; do not re-claim).
- `ABSTAINED` — the check could not run (crash, timeout, missing access). An abstention is NOT a pass and NOT a fail: retry or escalate; never count it as either.

## Ambiguity

If the outcome of an action is unknown (timeout on a side effect), record `UNKNOWN_EFFECT`, re-observe real state first, then decide. Idempotency keys exist exactly for this: check, don't blind-retry.

## Self-verification rules (measured failure modes)

- A maker cannot certify its own work: self-written tests can *lower* outcomes (weak tests dragged resolved rate from 61.2% to 57.3% in one study); independent tests from a separate role raised it to 65.3%.
- Do not trust self-assessed progress: in a pre-registered test, 56% of self-reported "improvements" measured ≤0, and the strongest in-band judge still accepted 44% regressions.
- Beware packaging: polished evidence panels (even fabricated) lift over-commitment on unknowable questions from 6.5% to 54%. Strip authority cues; demand provenance.
- Soundness beats effort: an unsound verifier gets WORSE as you scale attempts. Never scale retries past the point where the verifier is trustworthy.

## Tag survival

Truth tags must survive every handoff and every compaction. After any summarization/compression step, re-check: if a caveat detached from its claim, restore it as structured state (a tag field), not prose — prose caveats measurably fail to restore caution.
