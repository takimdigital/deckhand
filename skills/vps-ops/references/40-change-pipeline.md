# 40 — The change pipeline (implement → push → deploy → wait → smoke → report)

**Purpose:** the canonical loop for every change after the first deploy. This is where the project will actually live.
**Use when:** the user asks for any change to an already-deployed app ("add X", "fix Y", "ship this", "make the button green").
**Prerequisites:** `30-deploy-app.md` completed; `<project>/.vps-ops.json` exists in the repo.
**Companion refs:** `30-deploy-app.md` (app/env/domain setup) · `50-ops-monitoring.md` (logs, status, incidents) · `20-domain-dns-ssl.md` (DNS/SSL failures).

## The loop

```
1. read  <project>/.vps-ops.json           → server/project/app/db uuids + domain
2. implement the change                    (buildout-pack protocols: inspect → change → test)
3. commit + push to main
4. deploy: automatic via GitHub App   |   fallback: coolify deploy uuid <APP_UUID>
5. py scripts/coolify_api.py wait <APP_UUID> --timeout 900
6. py scripts/coolify_api.py smoke https://<domain> --expect 200
7. report — 5-line template below
   └─ failure at 5 or 6 → logs → classify → fix-forward (max 2) or rollback
```

## Step by step

**1 — Anchor.** Every session starts here; never re-derive UUIDs by hand.

```bash
cat .vps-ops.json        # {"server_uuid","project_uuid","app_uuid","db_uuid","domain","coolify_url"} — no secrets
```

**2 — Implement.** Buildout-pack protocols (inspect → change → test). The change must be green locally before any push: red tree never gets deployed.

**3 — Commit + push.**

```bash
git add -A && git commit -m "<message>" && git push origin main
git rev-parse --short HEAD        # record the short sha for the report
```

**4 — Deploy.**

```bash
# GitHub App route: the push above already queued it — confirm:
py scripts/coolify_api.py deployments <APP_UUID> --limit 3

# Other routes — explicit trigger:
coolify deploy uuid <APP_UUID>
# REST — query params only, no body:
curl -sS -X POST "$COOLIFY_URL/api/v1/deploy?uuid=<APP_UUID>&force=false" \
  -H "Authorization: Bearer $COOLIFY_TOKEN"
```

**5 — Wait for a terminal status.**

```bash
py scripts/coolify_api.py wait <APP_UUID> --timeout 900      # polls /deployments/applications/{uuid}
#   live-verified (Coolify 4.3.21): response wrapper {"count":N,"deployments":[...]}; terminal OK status = "finished".
#   deploy trigger returns {"deployments":[{ "message", "resource_uuid", "deployment_uuid" }]} — grab the uuid for logs/tracking.
```

| exit | meaning |
|---|---|
| 0 | `SUCCESS (<Ns>, deployment <id>)` — terminal OK |
| 3 | `DEPLOY FAILED (<status>)` — build failed → classification table |
| 5 | `TIMEOUT` — still running or stuck; check logs, do not assume success |

Deployment statuses are tolerant by design: `{"success","finished"}` = OK · `{"failed","cancelled"}` = FAIL · **anything else = still running**. Deployment objects carry `deployment_uuid`, `status`, `created_at`, `commit`, `commit_message`, `rollback`, `logs` — list them with `py scripts/coolify_api.py deployments <APP_UUID> --limit 5`.

**6 — Smoke test the live URL.**

```bash
py scripts/coolify_api.py smoke https://<domain> --expect 200
py scripts/coolify_api.py smoke https://<domain> --expect 200 --contains "<marker from this change>"
```

Exit `0` = pass, `4` = fail (wrong status, missing marker, or connection error). A passing smoke is the only proof the change is live.

**7 — Report — exactly these 5 lines:**

```
Change:     <short-sha> <commit subject>
Deployment: <deployment_uuid> (<duration, e.g. 1m32s>)
URL:        https://<domain>
Status:     SUCCESS
Smoke:      OK 200 https://<domain>
```

## Hard rules

1. Never deploy a red tree — local tests pass first.
2. Never report "deployed" without a terminal deployment status (`wait` exit 0).
3. Never report "deployed" without a passing smoke check.
4. Max **2** fix-forward attempts, then roll back. No unbounded retry loops.
5. Secrets live only in Coolify envs (`30-deploy-app.md` §3) — never echoed, never on a command line, never committed.
6. A change that needs a new env var: sync first (`coolify app env sync <APP_UUID> --file .env.production`), then deploy.

## Failure classification

| Symptom | Where to look | Command / action |
|---|---|---|
| Build error (nixpacks/docker step fails) | deployment logs | `py scripts/coolify_api.py deployments <APP_UUID> --limit 5` → the deployment's `logs` field; `GET /deployments/applications/{uuid}` |
| Deploy OK but the app exits/crashes at runtime | application logs | `py scripts/coolify_api.py logs <APP_UUID> --lines 200 --timestamps` · `coolify app logs <APP_UUID> --lines 200 --show-timestamps` · `GET /applications/{uuid}/logs?lines=200&show_timestamps=false` |
| `wait` OK but smoke 404 / 502 / connection refused | crash-looping container (check app logs), or port/domain misconfig | `ports_exposes` must be `"3000"` (string), `domains` correct (`30-deploy-app.md` §2/§5); restart the app |
| Smoke cannot resolve the name | DNS not propagated | `20-domain-dns-ssl.md` checks; `nslookup <domain> 1.1.1.1` must equal the VPS IP |
| TLS/cert error in smoke | Let's Encrypt pending or port 80 blocked | wait 2–3 min, redeploy; then `20-domain-dns-ssl.md` |
| Missing/blank env var at runtime | envs | `py scripts/coolify_api.py envs <APP_UUID>` (key names only) → re-sync from `.env.production` |

## Rollback (exact)

```bash
coolify app rollback images <APP_UUID>              # list rollback candidates (previous images/commits)
coolify app rollback run <APP_UUID> --commit <last-good-sha>
```

REST equivalent (pinned body):

```bash
curl -sS -X POST "$COOLIFY_URL/api/v1/applications/<APP_UUID>/rollback" \
  -H "Authorization: Bearer $COOLIFY_TOKEN" -H "Content-Type: application/json" \
  -d '{"commit": "<last-good-sha>"}'
# candidates: GET /applications/{uuid}/rollback-images → copy the `tag` verbatim (FULL 40-char sha)
# ⚠ short shas FAIL here (the rollback deployment dies in the clone stage) — use the full tag; rollback
#   reuses the existing image, so it completes in seconds (live-verified 2026-09-17). Git-native alternative
#   that always works and keeps repo HEAD == deployed artifact: `git revert <bad-sha> && git push && redeploy`.
```

Then **always** re-run wait + smoke and report the rollback:

```bash
py scripts/coolify_api.py wait <APP_UUID> --timeout 900
py scripts/coolify_api.py smoke https://<domain> --expect 200
```

```
Change:     <bad short-sha> <commit subject> — reverted
Deployment: <deployment_uuid> (<duration>)
URL:        https://<domain>
Status:     ROLLED BACK to <last-good-sha>
Smoke:      OK 200 https://<domain>
```

Find `<last-good-sha>`: newest entry from `py scripts/coolify_api.py deployments <APP_UUID> --limit 10` whose status is in `{success, finished}` (its `commit` field), or `git log --oneline`.

## Decision rule: fix-forward vs rollback

| Situation | Do |
|---|---|
| Clear one-line cause (typo, missing env var, config) | fix-forward once, re-run the loop from step 3 |
| Second failure with an unclear cause | roll back, then diagnose with logs in a follow-up change |
| Failure only in prod (works locally) | capture logs first, then roll back — do not iterate blind on prod |
