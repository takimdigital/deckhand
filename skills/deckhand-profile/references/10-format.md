# 10 — Profile format (v1)

Header line: `format: deckhand-profile v1` (future-proofing). Then plain `key: value` lines under
plain headings — human-editable, grep-able, ≤ 60 lines. Omit any field that does not apply; never invent.

## Fields

| Field | Write | Example |
|---|---|---|
| address as | name/handle | `Takim` |
| reports | style prefs for agent output | `short, evidence-first, simple English` |
| github | account + default visibility | `takimdigital · private` |
| email (accounts) | which inbox owns the accounts | `me@example.com` |
| domains | registrar · DNS host · owned (optional) | `NameSilo · Cloudflare` |
| providers | VPS/cloud panels + preference/region | `Contabo (preferred), Oracle (free tier)` |
| services in use | names only — keys live elsewhere | `Coolify, Cloudflare, Stripe (not yet)` |
| stack | framework + DB + package manager | `Next.js + Postgres · pnpm pinned` |
| deploy | platform + dashboard policy | `Coolify · dashboard loopback+tunnel` |
| repo style | per-project conventions | `one private repo per project` |
| track choice | when paid vs free preview | `paid for businesses · free for tests` |
| DNS/SSL | the chain used | `Cloudflare DNS-only → Let's Encrypt` |
| currency | for prices/reports | `CAD (show USD/EUR)` |
| constraints | never-do list, tone, honesty rules | `no secrets in files · preview≠production` |
| host | OS + shell quirks that affect commands | `Windows 11 + git-bash` |

## Rules

- Locations, never values: "Cloudflare token in `~/.vps-ops/secrets/env.sh`" belongs in the app's OPS.md, not here.
- One line per fact. If a field needs a paragraph, it is not a profile field.
- The user may hand-edit at any time — read the file fresh each session, never a cached copy.

## Compact example

```md
format: deckhand-profile v1
## Identity
- address as: Sam · reports: short, evidence-first
## Accounts
- github: samdev (private) · domains: NameSilo · DNS: Cloudflare
- providers: Contabo (default) · region: EU
## Defaults
- stack: Next.js + Postgres · deploy: Coolify (dashboard loopback+tunnel)
- track: paid for real clients · free preview for tests only
## Constraints
- no secrets in files · optional paths never forced
```
