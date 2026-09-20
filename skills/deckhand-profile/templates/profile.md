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
