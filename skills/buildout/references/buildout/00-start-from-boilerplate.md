# 00 — Start From a Boilerplate

Load when: starting a new project, or the user says "build me a SaaS".

Principle: **never start from zero when a verified starter exists.** Clone, strip, rebrand, then hand off to design assembly. Smallest sufficient change — do not rewrite the boilerplate.

**Path arbiter:** a surviving match in `data/boilerplates.json` → this doc (clone/strip/rebrand, then `10` for the UI). No starter matches (or the project is a static site from a bare scaffold) → scaffold minimally (`create-next-app` + one green baseline build), then go straight to `10-design-assembly.md`. When in doubt the boilerplate path wins — it deletes more work than it adds; a starter match that dies the freshness check falls back here too. **Conflict clause:** when a surviving starter contradicts frozen decisions — it ships its own animation, palette, or component chrome that the lock/bans exclude — **the lock wins**: the starter supplies scaffolding only; strip or reject what conflicts and log the deviations. Never re-open a frozen design for a starter's sake.

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
Run immediately BEFORE cloning. If it does not print `MIT` → do not clone; pick another starter. Never delete the `LICENSE` file from the derived project (MIT requires keeping the notice when copying substantial parts). No `gh` / offline? Fallback: fetch the license text directly — `curl -s https://raw.githubusercontent.com/<owner>/<repo>/HEAD/LICENSE | head -3` (or `git clone --depth 1` and read `LICENSE`) — and record the check + date in the project's `DECISIONS.md`.

## Clone + strip checklist

1. `git clone <repo> my-app && cd my-app` — fresh clone, own history (`rm -rf .git && git init` or start a new branch).
2. Rename: project name, package name, site title/meta, logo, favicon, social handles, email sender, domain constants.
3. Env: copy `.env.example` → `.env.local`; fill ONLY the services actually used; park the rest.
4. Remove unused integrations (payments provider you didn't pick, analytics you don't use) — delete code, not just config.
5. Brand tokens: find the token/CSS-variable block (e.g. `src/app/globals.css`) — this is the hook for the design-assembly phase.
6. Demo data/content: delete sample rows, placeholder pricing tables, demo testimonials. Replace with real copy or clearly marked TODO placeholders — never ship lorem ipsum. **A placeholder's visible COPY is client-facing text**: mark placeholders for the builder in markup (comments, `data-*`, empty states) — never as instructions a client will read (a field test shipped "Swap in the real photo when it is ready" onto a live page).

## Kickoff ledger — the project's `PENDING.md`

Create `PENDING.md` in the **project root — the root of what the humans actually receive** (the repo/delivered folder they first open; when the app lives in a subfolder like `site/` inside a team workspace, use the workspace root the humans were handed, and state the resolved path in the handoff so nobody guesses). Create it **the moment that directory exists** (greenfield: right after the scaffold; a pre-scaffold "kickoff" has no directory to put it in — until then the kickoff brief's human items stay in the session report). It is the project-scoped twin of the portable ledger (skill `deckhand-profile`), same strict parseable format:

`- [ ] P-0NN · <what> · WHY: <consequence if skipped> · HOW: <one-line action> · WHERE: <exact place / click path> · asked YYYY-MM-DD · status: open|waiting-confirm · nag: yes|no`

Rules: seed it from the kickoff brief + discovery questions; record every human task the build uncovers (accounts, keys, client-supplied data, policy decisions) in the same message you ask for it; agent work NEVER goes here (that is the session todo list); close with `· done YYYY-MM-DD`; surface open items in every report. It lives in the repo — the project's humans see it without any agent.

## Verification

- Fresh-clone run-through from the README works (target ≤10 min).
- `PENDING.md` seeded in the project root; every discovered human-blocker is on it.
- App boots; tests (if shipped) pass; database migrates.
- `LICENSE` intact; strip checklist items each checked off.
- Record: repo, commit SHA, license evidence, date — in the project's `AGENTS.md` or a `DECISIONS.md` line.

## Anti-patterns

- Cloning a non-MIT or unverified starter ("it says open source").
- Rewriting the boilerplate's architecture to taste before shipping anything.
- Leaving two auth systems / two payment providers half-wired.
- Skipping the strip — shipping demo branding, fake logos, or demo data.
