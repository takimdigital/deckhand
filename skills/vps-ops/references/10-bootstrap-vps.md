# 10 — Bootstrap: SSH key → key attach → firewall → Coolify → token → hardening → snapshot

Load when: the user's VPS + access method (+ provider API token) are known — i.e. after
`00-user-checklist.md` §1–§3. Next refs: `20-domain-dns-ssl.md` → `30-deploy-app.md`.

> **Oracle Cloud (free-preview track):** do `11-oracle-free-tier.md` FIRST (root login + in-VM
> firewall + cloud-init), then run Steps 0 → 2 → 4 → 5 → 6 here; **skip Step 3** (firewall = OCI
> Security List + ref 11) and **Step 7** (Hostinger-only). **Never run UFW on Oracle images.**
Runs from the agent machine (git-bash on Windows; `py` = Python launcher). `scripts/hostinger_api.py`
and `scripts/coolify_api.py` are stdlib-only — the contract; raw curl equivalents shown for every
step. Secrets live only in `~/.vps-ops/secrets/env.sh` (chmod 600).

Hard rules: firewall BEFORE the Coolify install · hardening only AFTER key auth is proven (Step 2) ·
never close port 22 (Coolify manages over SSH) · never touch Coolify's installer-created keys.

## Step 0 — keygen on the agent machine

```bash
mkdir -p ~/.vps-ops/ssh ~/.vps-ops/secrets && chmod 700 ~/.vps-ops ~/.vps-ops/ssh ~/.vps-ops/secrets
[ -f ~/.vps-ops/ssh/id_ed25519 ] || ssh-keygen -t ed25519 -N "" -C "vps-ops" -f ~/.vps-ops/ssh/id_ed25519
chmod 600 ~/.vps-ops/ssh/id_ed25519
```

Expected: `~/.vps-ops/ssh/id_ed25519` (+ `.pub`) exists; re-running never overwrites (idempotent).
Passphrase-less **by design** (agent is non-interactive; Coolify requires passphrase-less keys). Windows
note: on perms errors (`UNPROTECTED PRIVATE KEY`), `chmod 600`, use git-bash's `/usr/bin/ssh`, and/or `-o IdentitiesOnly=yes`.

## Step 1a — Hostinger: register + attach the key via API

Store the provider token once: `printf 'export HOSTINGER_API_TOKEN=%s\n' '<token>' >> ~/.vps-ops/secrets/env.sh && chmod 600 ~/.vps-ops/secrets/env.sh && . ~/.vps-ops/secrets/env.sh`

```bash
PUB="$(cat ~/.vps-ops/ssh/id_ed25519.pub)"

# 1) register the key → response carries the key id
curl -sS -X POST https://developers.hostinger.com/api/vps/v1/public-keys \
  -H "Authorization: Bearer $HOSTINGER_API_TOKEN" -H "Content-Type: application/json" \
  -d "{\"name\":\"vps-ops\",\"key\":\"$PUB\"}"
# → {"id": <keyId>, ...}        ← capture <keyId>

# 2) attach it to the VM
curl -sS -X POST https://developers.hostinger.com/api/vps/v1/public-keys/attach/<vmId> \
  -H "Authorization: Bearer $HOSTINGER_API_TOKEN" -H "Content-Type: application/json" \
  -d '{"ids":[<keyId>]}'
# → ActionResource {"id": <actionId>, ...}   (async — track via GET .../actions/<actionId>)

# 3) verify
curl -sS https://developers.hostinger.com/api/vps/v1/virtual-machines/<vmId>/public-keys \
  -H "Authorization: Bearer $HOSTINGER_API_TOKEN"
```

Expected: step 3 lists `vps-ops` with our pubkey material.
Script equivalent (idempotent — reuses an existing key by material, then attaches):
`py scripts/hostinger_api.py sshkey ensure --vm <vmId> --name vps-ops --key-file ~/.vps-ops/ssh/id_ed25519.pub`

## Step 1b — generic: one-paste key install

Hand the user the §3 one-liner from `00-user-checklist.md` with `<AGENT_PUBKEY>` replaced by
`cat ~/.vps-ops/ssh/id_ed25519.pub` (single command into their provider's browser console). Then Step 2.

## Step 2 — verify SSH (gate: do not continue until this passes)

```bash
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i ~/.vps-ops/ssh/id_ed25519 root@$VPS_IP 'uname -srm; id -u'
```

Expected:
```text
Linux 6.8.0-xx-generic x86_64
0
```
`BatchMode=yes` makes a password prompt impossible — success proves key auth. `Linux …` + `0` = root.

## Step 3 — firewall BEFORE install

### Hostinger (preferred — provider-level, installs nothing on the box)

```bash
# 3.1 create the firewall
curl -sS -X POST https://developers.hostinger.com/api/vps/v1/firewall \
  -H "Authorization: Bearer $HOSTINGER_API_TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"vps-ops"}'
# → {"id": <fwId>, ...}

# 3.2 one accept rule per port — ALL fields required; port is a STRING
for P in 22 80 443 8000 6001 6002; do
  curl -sS -X POST "https://developers.hostinger.com/api/vps/v1/firewall/<fwId>/rules" \
    -H "Authorization: Bearer $HOSTINGER_API_TOKEN" -H "Content-Type: application/json" \
    -d "{\"protocol\":\"TCP\",\"port\":\"$P\",\"source\":\"any\",\"source_detail\":\"any\"}"
done

# 3.3 activate the firewall on the VM
curl -sS -X POST "https://developers.hostinger.com/api/vps/v1/firewall/<fwId>/activate/<vmId>" \
  -H "Authorization: Bearer $HOSTINGER_API_TOKEN"
# → ActionResource

# 3.4 sync — activated VMs lose sync after rule changes; pushes the current rules
curl -sS -X POST "https://developers.hostinger.com/api/vps/v1/firewall/<fwId>/sync" \
  -H "Authorization: Bearer $HOSTINGER_API_TOKEN"
```

⚠️ A Hostinger firewall **drops all incoming by default** — the accept rules for 22, 80, 443, 8000,
6001, 6002 are mandatory, and every later rule change needs another `…/sync`.
Protocol enum: `TCP|UDP|ICMP|GRE|any|ESP|AH|ICMPv6|SSH|HTTP|HTTPS|MySQL|PostgreSQL`; port range form `"1024:2048"`.
Script equivalent (idempotent: find-or-create → ensure rules → activate → sync): `py scripts/hostinger_api.py firewall ensure --vm <vmId> --ports 22,80,443,8000,6001,6002 --name vps-ops`

### Generic (ufw — non-Hostinger providers only)

```bash
ssh -o BatchMode=yes -i ~/.vps-ops/ssh/id_ed25519 root@$VPS_IP \
  'ufw allow OpenSSH && ufw allow 80,443,8000,6001,6002/tcp && ufw --force enable && ufw status'
```

Expected: `Status: active` + rules for 22/tcp (OpenSSH), 80, 443, 8000, 6001, 6002.
Never remove the port-22 rule — Coolify manages the server over SSH.

## Step 4 — install Coolify + verify

```bash
ssh -o BatchMode=yes -i ~/.vps-ops/ssh/id_ed25519 root@$VPS_IP \
  'curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash'
curl -s -o /dev/null -w '%{http_code}\n' http://$VPS_IP:8000/api/health
ssh -o BatchMode=yes -i ~/.vps-ops/ssh/id_ed25519 root@$VPS_IP 'docker ps --format "{{.Names}}"'
```

Expected: install finishes (several minutes); health → `200`; container list = `coolify`, `coolify-db`,
`coolify-redis`, `coolify-realtime`, `coolify-proxy`, `coolify-sentinel` (validated live: Ubuntu 24.04 + Coolify 4.3.21).

> Rehearsal note (WSL2 only): Docker's own install script refuses WSL ("we recommend Docker Desktop") and
> the Coolify installer aborts along with it. Pre-install Docker first:
> `apt-get install -y docker.io docker-compose-v2` → the installer then detects Docker and skips its step.
> On a real VPS (non-WSL kernel) the standard path works untouched.

## Step 5 — token handoff + storage

Guide the user through `00-user-checklist.md` §4A (one browser session). Then:

```bash
printf 'export COOLIFY_URL=%s\nexport COOLIFY_TOKEN=%s\n' "http://$VPS_IP:8000" "<token>" > ~/.vps-ops/secrets/env.sh
chmod 600 ~/.vps-ops/secrets/env.sh
. ~/.vps-ops/secrets/env.sh
curl -sS -H "Authorization: Bearer $COOLIFY_TOKEN" "$COOLIFY_URL/api/v1/applications"
```

Expected: `[]` (fresh install) or a JSON array. `401` → API access still disabled or token wrong (§4A).
Script check: `py scripts/coolify_api.py health` → `coolify health: 200`. Never echo the token into
chat, logs, or a repo file. `coolify_api.py` reads `$COOLIFY_URL`/`$COOLIFY_TOKEN`, then `~/.vps-ops/config.json` / `secrets/env.sh`.

## Step 6 — harden (only after Step 2 proved key auth)

```bash
ssh -o BatchMode=yes -i ~/.vps-ops/ssh/id_ed25519 root@$VPS_IP '
  printf "%s\n" "PermitRootLogin prohibit-password" "PasswordAuthentication no" \
    > /etc/ssh/sshd_config.d/99-vps-ops.conf && sshd -t && systemctl restart ssh && echo HARDENED'
ssh -o BatchMode=yes -o PreferredAuthentications=password -o PubkeyAuthentication=no root@$VPS_IP
```

Expected: first command prints `HARDENED`; re-running Step 2 still succeeds; the password attempt fails
with `Permission denied (publickey)`. Keep Coolify's localhost keys untouched; recover via hPanel if Step 2 breaks.

## Step 7 — golden snapshot (Hostinger)

```bash
curl -sS -X POST "https://developers.hostinger.com/api/vps/v1/virtual-machines/<vmId>/snapshot" \
  -H "Authorization: Bearer $HOSTINGER_API_TOKEN"        # no body → ActionResource
curl -sS "https://developers.hostinger.com/api/vps/v1/virtual-machines/<vmId>/actions/<actionId>" \
  -H "Authorization: Bearer $HOSTINGER_API_TOKEN"
# → "state": "success"    (states: success | error | delayed | sent | created)
```

Script equivalents: `py scripts/hostinger_api.py snapshot create <vmId>` · `py scripts/hostinger_api.py actions <vmId> <actionId>`.
Record the timestamp — the known-good baseline for restores. Generic providers: their snapshot UI/API, or skip.

## Step 8 — Coolify instance domain (recommended: unlocks HTTPS + MCP)

1. Add `coolify A <IP>` DNS (`20-domain-dns-ssl.md`).
2. Coolify Settings → set the **instance domain** (`https://coolify.<domain>`) → wait for the cert.
3. Verify: `curl -s -o /dev/null -w '%{http_code}\n' https://coolify.<domain>/api/health` → `200`.
Until this step MCP is unusable (it needs a public HTTPS URL); REST over `http://<ip>:8000` remains the working contract.

## Harness MCP wiring (optional convenience layer)

Hermes — `~/.hermes/config.yaml`:
```yaml
mcp_servers:
  coolify:
    url: "https://coolify.<domain>/mcp"
    headers:
      Authorization: "Bearer <token>"
```
Claude Code:
```bash
claude mcp add --transport http coolify https://coolify.<domain>/mcp --header "Authorization: Bearer <token>"
```
Hostinger's remote MCP (`https://mcp.hostinger.com`) is OAuth-based — fine in Claude Code/Cursor; for Hermes use `scripts/hostinger_api.py` with `$HOSTINGER_API_TOKEN`.

## Failure remedies

| Symptom | Likely cause | Fix |
|---|---|---|
| `Permission denied (publickey)` Step 2 (Hostinger) | key not attached / wrong id | re-run attach with the right `<keyId>`; re-check `GET …/{vmId}/public-keys` |
| `Permission denied (publickey)` Step 2 (generic) | paste never landed | re-paste the §3 one-liner in the provider console; check file perms 600 |
| `UNPROTECTED PRIVATE KEY` / bad permissions | Windows perms on the key file | `chmod 600`; use git-bash `/usr/bin/ssh`; add `-o IdentitiesOnly=yes` |
| `Host key verification failed` | stale known_hosts (rebuilt VPS) | `ssh-keygen -R $VPS_IP`, retry Step 2 |
| `:8000/api/health` not 200, or unreachable | install still running, port 8000 blocked, or rules not synced | wait 2–3 min; `docker ps`; add rule 8000, re-activate, `…/sync` |
| Token curl → `401` | API access off / token scopes wrong | `00-user-checklist.md` §4A, recreate the token |
| `config error: …` from a script | env not loaded | `. ~/.vps-ops/secrets/env.sh` |
| SSH lost after firewall change | rule for 22 missing | add TCP/22 + `…/sync`; recover via provider console |
