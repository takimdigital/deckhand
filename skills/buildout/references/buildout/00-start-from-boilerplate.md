# 00 — Start From a Boilerplate

Load when: starting a new project, or the user says "build me a SaaS".

Principle: **never start from zero when a verified starter exists.** Clone, strip, rebrand, then hand off to design assembly. Smallest sufficient change — do not rewrite the boilerplate.

## Decision procedure

1. **Feature checklist** (ask in one batched round, options + skip): auth? (email / social / SSO) · payments? (one-off / subscriptions) · teams/roles? · admin panel? · blog/docs? · email sending? · background jobs? · file uploads? · i18n/RTL? · analytics?
2. **Match against `data/boilerplates.json`** (`bestFor` + `features` + `stack`). Read the file fresh — it is updated by the pack's update loop.
3. **Stack-fit gate.** Wasp (open-saas) vs Next.js-native (next-saas-starter) vs landing-only (velora-ui). If the user's target stack is Next.js and they'd refuse Wasp, pick accordingly — record the choice.
4. **Freshness check.** If `lastPush` in the catalog is >6 months old, verify the repo is still healthy before choosing.

## License gate (hard)

```bash
gh api repos/<owner>/<repo> --jq .license.spdx_id
# MUST print: MIT
```
Run immediately BEFORE cloning. If it does not print `MIT` → do not clone; pick another starter. Never delete the `LICENSE` file from the derived project (MIT requires keeping the notice when copying substantial parts).

## Clone + strip checklist

1. `git clone <repo> my-app && cd my-app` — fresh clone, own history (`rm -rf .git && git init` or start a new branch).
2. Rename: project name, package name, site title/meta, logo, favicon, social handles, email sender, domain constants.
3. Env: copy `.env.example` → `.env.local`; fill ONLY the services actually used; park the rest.
4. Remove unused integrations (payments provider you didn't pick, analytics you don't use) — delete code, not just config.
5. Brand tokens: find the token/CSS-variable block (e.g. `src/app/globals.css`) — this is the hook for the design-assembly phase.
6. Demo data/content: delete sample rows, placeholder pricing tables, demo testimonials. Replace with real copy or clearly marked TODO placeholders — never ship lorem ipsum.

## Verification

- Fresh-clone run-through from the README works (target ≤10 min).
- App boots; tests (if shipped) pass; database migrates.
- `LICENSE` intact; strip checklist items each checked off.
- Record: repo, commit SHA, license evidence, date — in the project's `AGENTS.md` or a `DECISIONS.md` line.

## Anti-patterns

- Cloning a non-MIT or unverified starter ("it says open source").
- Rewriting the boilerplate's architecture to taste before shipping anything.
- Leaving two auth systems / two payment providers half-wired.
- Skipping the strip — shipping demo branding, fake logos, or demo data.
