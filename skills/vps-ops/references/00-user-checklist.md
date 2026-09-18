# 00 — User checklist: the only things we ask the user for

Load when: a deployment engagement starts ("host my app", "I have a VPS", "deploy this project").
This file is the complete ask-list. Collect items 1–4 once (plus any §5 keys the app needs), then run
`10-bootstrap-vps.md` → `20-domain-dns-ssl.md` → `30-deploy-app.md`. After that, every request flows
through `40-change-pipeline.md` and `50-ops-monitoring.md`.

Prerequisites: none — this is the entry point.

## 1. What we ask for (and nothing else)

- [ ] **VPS host + IP** — or the access needed to create one (§2/§3)
- [ ] **SSH access method** — ONE of the two paths below
- [ ] **Domain name + registrar** — Hostinger / Namecheap / GoDaddy / Cloudflare / OVH / Google
- [ ] **GitHub account** — where the repo lives; private or public both fine
- [ ] *(optional but recommended)* **provider API token** — unlocks DNS / firewall / snapshot automation
- [ ] **Business keys** — only the §5 rows the app actually needs (agent asks per use case)

VPS minimum: **Ubuntu 24.04 LTS**, KVM / full-virtualised, root SSH allowed. Coolify's floor is
2 vCPU / 2 GB RAM / 30 GB disk — order **2 vCPU / 4 GB** to leave build headroom.

## 2. Hostinger path (preferred — near-zero user work)

1. Create the VPS in hPanel: **KVM**, **Ubuntu 24.04 LTS**, ≥ 2 vCPU / 4 GB RAM.
2. hPanel → **Account → API** → create an API token (read/write for VPS + DNS) → paste it to the agent once.
3. Give the agent the **VPS id** (from hPanel → VPS) and the **IP**.

The agent does the rest via `https://developers.hostinger.com`: SSH-key register + attach, firewall
create/rules/activate/sync, DNS records, snapshots, metrics, restarts — see `10-bootstrap-vps.md`
Steps 1a/3/7 and `20-domain-dns-ssl.md`. The token is stored in `~/.vps-ops/secrets/env.sh`
(chmod 600), never in a repo.

## 3. Generic path (any other provider)

1. Create a VPS: **Ubuntu 24.04 LTS**, ≥ 2 vCPU / 4 GB RAM, root SSH enabled.
2. The agent prints ONE line with its real public key substituted for `<AGENT_PUBKEY>`:
   open the provider's **browser console** (VNC / web terminal) and paste it once, as a single command:

   ```bash
   mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo "<AGENT_PUBKEY>" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
   ```

3. Nothing else. The agent verifies key auth (`10-bootstrap-vps.md` Step 2) and proceeds.

## 4. Two one-time browser approvals (agent guides, click-by-click)

**A. Coolify admin account + API access** — right after the agent installs Coolify (`10-bootstrap-vps.md` Step 5):

1. Open `http://<ip>:8000` → registration page → create the first **admin account**.
2. **Settings → Configuration → Advanced** → enable **API access** (and **MCP** if you want the
   optional MCP convenience layer).
3. **Keys & Tokens → API Tokens** → create a token named `vps-ops` with scopes
   `read`, `read:sensitive`, `write`, `deploy` → copy it and paste it to the agent once.
   (`write` is required to create projects/apps/databases — without it, Coolify answers
   `Missing required permissions: write`.)
4. *(optional, recommended)* enable **2FA** on this account.

**B. GitHub App install** — only for **private repos**, prompted during `30-deploy-app.md`: the
agent creates the GitHub App in Coolify, you click **Install** on GitHub and pick the repo. One click.

That is the entire set — no other browser visits are ever required.

## 5. Business keys matrix — the agent asks only for the rows your app needs

| Service | What to create | Where the key is | Used for |
|---|---|---|---|
| Stripe | Secret key + webhook signing secret | dashboard.stripe.com → Developers → API keys / Webhooks | payments, webhook verification |
| Transactional email (Resend / Postmark / SES) | API key (verify sending domain) | provider dashboard → API keys | signup mail, receipts, resets |
| SMTP | host, port, user, pass | your mail provider's SMTP settings | apps that only speak SMTP |
| OAuth (GitHub / Google) | OAuth app → client id + secret (redirect URI = app domain) | provider developer console | social login |
| Analytics (Plausible / Umami / PostHog) | site id / project API key | provider dashboard | product analytics |
| Anything else | whatever the app's `.env.example` declares | — | the app's own config |

Rule: the agent reads `.env.example` in the repo and asks for exactly those values — nothing more.
Secrets go only into `~/.vps-ops/secrets/` and Coolify env vars, never into a repo, commit, or chat echo.

## 6. What the user will NEVER have to do

- Open an SSH session or run a single server command.
- Operate the Coolify dashboard (beyond the two approvals above).
- Deploy, redeploy, restart, or roll back by hand.
- Edit DNS records by hand or manage TLS certificates.
- Do routine ops: logs, metrics, backups, updates, disk cleanup — all agent-driven.

## 7. DNS records (non-Hostinger registrar) — copy-paste block

```text
@        A   <IP>      # apex / root
www      A   <IP>      # www alias
coolify  A   <IP>      # Coolify instance → HTTPS + MCP
*        A   <IP>      # optional — Coolify PR previews
```

| Registrar | One-line path to add an A record |
|---|---|
| Namecheap | Domain List → Manage → **Advanced DNS** → Add New Record → **A Record**, Host `@`/`www`, Value `<IP>` |
| GoDaddy | My Products → Domains → **DNS** → Add → **A**, Name `@`/`www`, Value `<IP>` |
| Cloudflare | DNS → Records → Add record → **A**, Name `@`/`www` (or `coolify`), IPv4 `<IP>`; keep **DNS only** (grey cloud) while certs are issued |
| OVH | Web Cloud → Domains → your domain → **DNS zone** → Add an entry → **A**, sub-domain `@`/`www`, target `<IP>` |
| Google / Squarespace Domains | DNS → Custom records → **A**, host `@`/`www`, data `<IP>` |

Ask the agent for the block with your real IP substituted. TTL 14400 is fine. Cloudflare proxying
(orange cloud) can interfere with Let's Encrypt's HTTP-01 challenge — stay DNS-only during bootstrap.
[verify at live drill]

## 8. One-paste hand-off

```text
VPS:      <IP>   (provider: Hostinger, vmId <id>  |  or: <provider>, key installed per §3)
Domain:   <domain>   (registrar: <name>)
GitHub:   <user>/<repo>  (private | public)
Keys:     none yet  |  attached .env values for the services in §5
```

Next: `10-bootstrap-vps.md` → `20-domain-dns-ssl.md` → `30-deploy-app.md`.
