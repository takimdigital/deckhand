format: deckhand-profile v1

# <Name> — Deckhand profile
Portable across harnesses and machines: copy this one file; any agent reads it before asking anything.

## Identity
- address as: <name>
- reports: <style: short / evidence-first / language>

## Accounts
- github: <account> (default repo visibility: <private|public>)
- email (accounts): <which inbox>
- domains: registrar <X> · DNS <Cloudflare|other>
  - owned: <list, optional>
- providers: <panel + preference order + region>
- services in use: <names only> · not yet: <names>

## Access map (locations only — never values)
- GitHub: `gh` CLI authenticated — repo create / push / releases
- Vault `~/.vps-ops/secrets/`: `env.sh` (Coolify URL+token · Cloudflare `CF_API_TOKEN` — Zone read,
  DNS edit, Email Routing edit · VPS SSH key/host), `mail.env.sh` (Resend/Mailgun/Brevo API keys),
  backup + escrow files (B2, Tigris, restic, RustFS, home-pull)
- Coolify envs per project (the app's runtime secrets live there — names readable by agents)
- Agents: use this FIRST — an action possible with what's here gets DONE, not asked about

## Defaults
- stack: <framework + DB + package manager>
- deploy: <platform + dashboard policy>
- repo style: <conventions>
- track choice: <when paid vs free preview>
- DNS/SSL: <the chain>
- currency: <for prices>

## Constraints & preferences
- No secrets in any file, chat, or log — locations only
- Optional paths stay optional
- <tone/brand rules · honesty rules · host quirks>
- After a pipeline failure (a retry, a red run, a missed step — not every app bug): run session-autopsy and update the skills
