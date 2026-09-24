# Changelog

## 2026-09-23 — the pool doubles: 6 repos in, through the batch tool itself (pack v0.17.1)

The pool's first real owner batch. Six repos went in through the new batch tool — three agents sharing the list, remote measurement only, one JSON per repo, gate-checked before import — and four came out measured: a FastAPI+Next AI-agent generator, two Expo mobile apps and a Laravel multi-vendor commerce platform. The pool now holds **14 templates, 12 with measured detail files**. Two of the six ship no MIT/Apache licence and are refused by the pool's rule, recorded with that reason and never ranked.

The batch immediately paid for itself in fixes. `plan` no longer spends an agent on an already-refused repo; `check` no longer counts a refused repo as `MISSING` (which would have kept a batch from ever going green); and the registry stopped calling whole families of repos "react-vite" — a PHP/Laravel platform that ships `package.json` + `vite.config` for its asset build, and Expo/React-Native apps that are not web SPAs at all. Both now measure truthfully, so a mobile template can never pass as a web one.

buildout: **0.9.1 · 64 offline tests · 115 for the pack.**

## 2026-09-23 — pool batches: the owner sends repos, the pool learns (pack v0.17.0): the owner sends repos, the pool learns (pack v0.17.0)

Anyone can now hand the pool a list of GitHub repos and have them measured into it — remotely, and by **at most three agents carrying slices of the list**, never one agent per repo. `pool_batch.py plan` validates the pasted list (URLs, `owner/name`, `git@` remotes; notes ignored; duplicates collapsed), marks what the registry already knows, slices the work across three agents and prints the delegations ready to paste — each carrying its repos, its output paths and the measuring rules. `check` then gates the batch per repo (`MISSING` / `INVALID` / `NO ROW`, exit 3 while anything is off) and `import` folds it in through the same validating importer as everything else, so a repo outside the registry can never receive details.

Proven on a real list: 4 repos + one off-GitHub line → the line refused, 3 agents planned 2/1/1, the gate correctly demanded the missing files, and a deliberately broken file was caught as `INVALID` rather than silently counted as missing. Rule recorded in `references/pool-batch.md`.

buildout: **0.9.0 · 59 offline tests · 110 for the pack.**

## 2026-09-23 — the interview starts from the profile (pack v0.16.3)

The phase reference that runs a business intake said nothing about the portable profile, so a session that loaded only that file could ask an owner for facts `~/.deckhand/profile.md` already answers — hosting, stack, DNS/SSL, currency, accounts, brand tone. The intake now opens by reading the profile and treating those items as taken defaults (`assumed: true`) rather than questions, and when no profile exists it creates one first, once, for every future business. The profile step itself was never removed — it is wired into the router and the pack ships the `deckhand-profile` skill; this closes the gap where the ref could contradict it.

buildout: **0.8.3 · 48 offline tests.**

## 2026-09-23 — a stale measurement cannot roll the pool back (pack v0.16.2)

Two pool-measuring runs on the same registry were observed racing: both measured the same eight templates and the slower one finished last, silently overwriting newer rows with older measurements. The registry now refuses it — a run carries the stamp of the moment it started and skips any row that was updated after it (printed as `SKIPPED`, not silently), with the rule written into the intake reference: never run two measurements at once. Proven against the live registry: a deliberately stale write was refused and the template's real star count stayed intact.

buildout: **0.8.2 · 48 offline tests.**

## 2026-09-23 — the pool gets a memory (pack v0.16.1)

Every template in the factory pool now carries a **measured detail file** — not what its README claims, but what its code does: the real routes, the features that exist, the locales it actually ships, the environment names it demands at build time, the deploy story, the files that carry someone else's brand, and the traps that would cost an hour. One subagent per repository measures it through the GitHub API (no clone, no execution, env vars **by name only**); one command validates and imports it; the blobs ship in the pack and load on demand, while a compact digest rides the pool export.

The first honest ranking came out of it: for a French + Arabic invoicing ask, the previous top pick drops to third once its own detail file proves it has **no database** — the factory now prices that in (−25) and says so in the reasons. Two repositories are also named as **blocked** rather than quietly ranked: one ships ~20 KB of obfuscated JavaScript welded onto `postcss.config.mjs` (verified by reading the file back), one depends on an npm package that does not exist (verified against the registry: 404 where a sibling returns 200). Blockers are structured and evidence-quoted — a regex over an agent's prose once flagged two healthy templates, and that mistake is now a regression test.

The measure step also got honest about itself: a pool-wide before/after diff caught a phantom vendor (`ably`, recorded because a README said "pro**bably**"), proved that vendors must come from dependencies and config files rather than prose, and then caught a second bug in the first fix — env-var names stopped matching, so real vendor dependencies silently vanished. Both are fixed, with the diff as the evidence.

buildout: **0.8.1 · 47 offline tests** (was 36) · older registries migrate in place instead of crashing.

## 2026-09-23 — buildout becomes a Template Factory (pack v0.16.0)

buildout no longer *generates* applications: it **matches, clones, swaps and rebrands** vetted MIT/Apache full-app templates. A ≤10-question intake feeds a registry of templates **measured through the GitHub API** (license, stack, vendor dependencies, contributor concentration, risk flags, rebrand surface — never README claims), scored deterministically (shape · features · RTL · canonical stack · boot · stars · swap cost) with hard blockers on license, archived repos and build failures. The chosen match is cloned into a fresh project folder with its own git history and a small factory record (license, upstream commit, swap map, mandatory-facts list); proprietary services (Clerk, Neon, Resend, Sendgrid, Sentry, S3, Plausible, hosted Postgres…) are replaced by open-source targets and **proved gone by `swap_check`** (per-entry verdict, exit 1 on any leftover reference); the owner's brand replaces the template's — including the leak check that kills template names, demo copy and leftover logos; then a 6-row verify tail (fresh-clone boot with a build-id proof, swap check, leak check, core-flow write-path, mobile probe, PENDING) and the Coolify deploy. Cloning and booting third-party code is **consent-gated** (`--deep --yes`); intake itself never clones.

**Deleted, not deprecated:** the map/spec contract, the direction competition, the vendored 10 MB reference library, the component registry pool, the design-assembly layer and the design-audit kit — five subsystems that existed to generate design, which is where the drift, the token burn and the "impressive but crappy" outcomes lived. What survives is what verifies: the hard-won rules (freshness, write-path, occlusion, text floor, leak check) compressed into one gate, the QA instruments, and the knowledge refs. buildout: **12 MB → 0.4 MB, 92 tests → 36**.

**Two field findings baked back in:** a build that fails naming vendor keys (`CLERK_SECRET_KEY`, …) is a *swap input*, not a pool rejection — the order is clone → swap → build; and a repo nobody uses is not production-ready — the scorer carries star tiers (≥1000★ +5 · ≥200★ +2 · <10★ −10).

**Validated end-to-end on a real template, not only on fixtures:** the factory cloned a live MIT template, installed and built it, served it, and proved freshness by matching the build id in the served page — while both gates correctly went red on the unswapped artifact: the swap check on leftover vendor references (file-and-line evidence, exit 1) and the leak check on the template's own name, author and demo domain appearing in the served page.

**Then the gates were audited against that real clone — and seven of them were lying.** A zero-context read found what fixtures cannot: the swap check counted its own map file as leftover vendor code (exit 0 was structurally unreachable), an empty swap map passed with no work done, prose "targets" in the vendor table could never be matched, a lint config counted as an installed adapter, short vendor names matched inside ordinary words, the licence gate was bypassable on the one path that skips the registry, and a commit could not actually be pinned. All seven are fixed, each with its own regression test, and re-measured on the real clone: three honest `INCOMPLETE` verdicts pointing at real files, no ghosts, no false greens.

The defects that run surfaced are fixed in this release: package-manager shims not resolving on Windows, an install running outside the project folder, a swap map written in the wrong shape, and a commit that is now cut before any install can land in it.

Skill versions: buildout 0.9.1 · vps-ops 0.9.9 · deckhand-profile 0.3.3 · component-library 0.1.3. **115 stdlib tests green.**

## 2026-09-22 — map before build, two directions compete, and the freeze gate that refuses (pack v0.15.0)

The build pipeline now writes down what it is building before it builds, and locks the look only after two directions fight it out. **The map:** every feature, user flow and edge state becomes a small document set — charters, flows, an edge-state registry — frozen before assembly, with a mechanical freeze gate that REFUSES the freeze on blank cells, dead-end states, unfilled placeholders or merged flows (depth-aware: a lean six-category map or the full eleven; graceful skip when you just want a build). **The direction competition:** two independent takes on the look — same brief, different mandates, blind drafts (B starts only after A is finished, no revision chain) — where every disagreement becomes a named fork with its deciding criterion committed before the other side is read (capped ~5 forks, 2–3 rounds), unevidenced claims are downgraded and cannot decide a fork, and the merge is per-fork against a pre-agreed rubric, never one author editing the other. The output is exactly ONE direction: a locked design token set, a decision record with a minority report, and a cost + vindication log that says plainly when the merge did not beat the best single draft. After the merge one leader runs the build and one runs the independent verification lane. Both stages are additive — without them, builds behave exactly as before.

**The silent-failure classes, closed:** backup verification can now actually go red (an empty schedule list and a failed backup run both passed silently before); first deploys and every change prove they are YOUR app answering, not any HTTP 200 (`smoke --contains`); the component library's `copy` refuses to overwrite existing files without `--force`, pre-flights before writing anything (no partial installs, no raw tracebacks), and gained `verify` (index vs store vs disk) and `where`; the Coolify upgrade path re-locks the dashboard after every upgrade; the DNS pre-change snapshot never overwrites itself (timestamped); strict mode catches hardcoded fonts alongside hardcoded colors. **The ledger rules got teeth:** the checkbox — not the heading — is the state of record, decision items are first-class (`decide:` + `DECISION NEEDED`), future agent actions ride their trigger item, ages are whole days, and `## Decided, not built` is a real section.

**Across all four skills:** an end-to-end first-user trial of the pipeline surfaced 54 friction points — all closed, with each fix's gate carrying its own known-bad fixture; then a zero-context cold-read audit re-walked every skill exactly as a first-time reader meets it (46 findings, every one verified against the files and fixed — including three gates whose documented commands could not actually run, and two checks that could never fail). 132 stdlib tests green. Skill versions: buildout 0.6.0 · vps-ops 0.9.9 · deckhand-profile 0.3.3 · component-library 0.1.3.

## 2026-09-22 — silent-failure classes closed; install docs verified (pack v0.14.10)

Three classes of silent failure, gone. (1) **Backup naming trap:** the VPS backup script and the
vault tools disagreed on env names (host scheme, `B2_APP_KEY_ID` vs short forms, `TIGRIS_*` vs
`TG_*`) — the first real backup died on it; the shipped script now accepts either form and the
template maps vault → server 1:1. (2) **Gates that could never go red:** two backup scripts always
exited 0 — they now exit non-zero when a leg fails or a bucket listing is empty. (3) **Windows
line endings:** checkouts could materialize `*.sh` as CRLF and break on the server — the repo now
pins `*.sh` to LF. Plus: install-truth fixes on the landing page (harness paths incl. Cursor,
`mkdir -p` before the copy example, zip instructions), `app.<domain>` removed from every runbook
(the DNS plan defines @ / www / coolify only), and the release gate now checks the top changelog
entry, the prose test-count line, and fails outright when pytest is missing.

## 2026-09-21 — release claims are machine-checked (pack v0.14.9)

Version and test-count claims can no longer drift from the repo. A new consistency check
(`scripts/version_check.py`) cross-checks the README version badge, the README tests badge against
the actual skill suites, every skill's frontmatter against its own changelog, and — at ship time —
the release tag itself; any mismatch exits non-zero. It runs as a hard stop in the release
procedure before push and again after tagging, so a release can't ship while a claim disagrees with
machine state. (It caught its first drift on arrival: the version badge was one release behind.)

## 2026-09-21 — no bare-ssh example left anywhere (vps-ops v0.9.7 / pack v0.14.9)

The unattended-ssh fix's rule — every ssh from the agent machine carries the durable known-hosts
location — is now exhaustive in the EXAMPLES, references and templates alike: firewall setup, the
dashboard loopback lock, Coolify install, hardening, Oracle (iptables verify + fallback, access
gate, tunnel), first-run data steps (migrate, seed, owner create/delete), restore drills, the
migration dump/scp/restore, Coolify/OS upgrades, and the OPS-handoff template all show the full
canonical form. 40 ssh lines carry the flags, and an exhaustive grep classifier (prose and
anti-examples excluded) confirms zero bare runnable forms remain — no copy-paste path back to the
failure.

## 2026-09-21 — unattended runs stop dying on Windows SSH quirks (vps-ops v0.9.6 / pack v0.14.8)

Scheduled and background checks run with nobody at the keyboard — any step that stalls on an
unanswerable prompt is a silent, recurring failure. Two such traps are now closed:

- **Host keys are found again:** MSYS ssh reads a different home directory than the shell does, so a
  background ssh could die on `Host key verification failed` even with everything set up correctly.
  Every ssh the pipeline runs now carries the durable known-hosts location explicitly, and the
  bootstrap gate stores the server's key there from first contact; the failure-table entry for this
  error now names both real causes with the exact fix for each.
- **Agent-run schedules call scripts directly:** the Task-Scheduler wrapper form (`bash -lc "…"`)
  is refused by the harness when no human can approve it — backup/watchdog recipes now invoke
  scripts directly, keeping the wrapper only where it belongs (Windows Task Scheduler).

## 2026-09-21 — project pendings stay with the project (buildout v0.4.7 / deckhand-profile v0.3.1 / pack v0.14.7)

- **A build's human tasks now live in the build.** Greenfield projects keep a `PENDING.md` in the
  project folder — created at kickoff, same strict parseable format as the portable ledger — and
  every human-blocker the work discovers (an account, a key, client-supplied data, a policy
  decision) is recorded there as it appears and surfaced in reports. The portable
  `~/.deckhand/pending.md` is now explicitly for cross-project / user-infrastructure items:
  project sessions read it, but never write project chores into it.

## 2026-09-21 — the component pool proves its install paths live (buildout v0.4.6 / pack v0.14.6)

The buildout engine's registry pool now verifies itself against the live web, and seven new
MIT-verified registries join it:

- **`onboard` samples real install URLs before writing a catalog.** A five-point spread check runs
  across the rendered catalog first; if the registry's URL shape no longer resolves, the run
  aborts with the exact failing URLs and writes nothing — a dead template can no longer reach a
  catalog silently. Only MIT-allowlisted registries can be onboarded at all.
- **New `registry_sync.py verify`** re-checks every allowlisted registry's install path (index +
  spread-sampled items) and fails on 404 templates and plan-gated registries — pool upkeep is a
  checked step now. A single item can be checked before install (`verify --item @ns/<name>`), and
  `verify` refuses an unsynced allowlist (sync first).
- **Seven new MIT-verified registries** — calendar, kanban, gantt, data-grid, drag-and-drop and
  chart families — each with verified license evidence and a live-tested item endpoint; snapshot
  refreshed against the live directory (382 listed → 300 kept).
- **Fixed — install targets that had died upstream:** the `{style}` default is now each registry's
  served default (`base-nova`) instead of a value no longer served; the curated URL, homepage and
  catalog URL now override the public directory's template (one directory entry advertised a shape
  its own site 404s — a dead style segment plus a moved item path; one homepage host served a dead
  TLS certificate, pinned to the working host); the pool's largest catalog (1,773 items) was
  regenerated end-to-end on the served shape.
- **One newly-added registry was dropped after live testing** — its headline blocks are
  plan-gated; every allowlisted registry installs keyless today.
- **Rules + tests:** the allowlist now requires dated, live-checked endpoint evidence per entry;
  the suite covers sampling, classification, URL-override semantics and bare-name installs (pack
  total: 58 tests across all suites, all green).

## 2026-09-21 — audit claims verified against the code; zip parity is now byte-level (buildout v0.4.5 / pack v0.14.5)

A line-by-line audit of the design gate's claims against its implementation found gaps between what
the kit said and what the gate actually ran. All are closed at the code level:

- **axe's `target-size` never ran** — the WCAG 2.5.8 rule ships disabled in axe-core, so the existing
  tag list surfaced nothing about touch targets; it is now enabled explicitly (`wcag22a` tag added
  too — a no-op today, future-proof). Touch targets below 24×24 CSS px now FAIL the run instead of
  being merely recorded, with inline text links exempted per the standard's own exception.
- **"Exactly one `<main>`" was documented, not checked** — now a per-route assertion in the gate.
- **forced-colors / reduced-motion support was claimed without an implementation** — now real:
  per-route media emulation (restored before the baseline screenshot), with forced-colors overflow
  asserted and the running-animation count recorded.
- **Two silent-input traps closed:** `registry_sync.py list|onboard` now print
  `no snapshot - run: py scripts/registry_sync.py sync` instead of tracebacking, and
  `assemble_pick.py` fails loudly on an `--items` glob that matches nothing (was a silent empty pool).
- **The zip-vs-repo invariant is now BYTE-level.** Entry-count parity had passed a distributable
  whose nine files sat two versions old — the new `scripts/zip_parity.py <zip>` compares every
  entry's bytes (and flags missing/extra files), and the release checklist runs it before anything
  ships.

## 2026-09-21 — one origin, one truth (buildout v0.4.4 / pack v0.14.4)

The design gate's app address now resolves in exactly ONE place — the Playwright config — everywhere
it is used:

- **The Lighthouse pass** derives its origin from the config instead of carrying its own copy of the
  URL logic (the copy that once sent a containerized run at a dead localhost); a config missing
  `use.baseURL` now fails with a named error instead of silently guessing.
- **The link check** resolves the same chain (`AUDIT_BASE_URL` → `AUDIT_PORT` → :3000) inside node,
  so retargeting the gate can no longer leave it silently pointed at the default port.
- **The container round-trip copies the fresh baselines out BEFORE the determinism pass** — a
  failing second pass keeps both the set and the failure instead of everything dying with the
  container; the recipe also puts Docker's credential helper on PATH up front and documents the
  `docker ps --format '{{…}}'` brace trap (`must specify at least one container source`).

## 2026-09-21 — the container baseline path, verified (buildout v0.4.3 / pack v0.14.3)

The design-audit kit's one documented-only path — generating pixel baselines in the pinned
Playwright container — is now exercised end-to-end on a real machine:

- **Verified round-trip ships in the kit README:** image pulled from the registry, the container's
  browsers rendering a host-run app (`AUDIT_BASE_URL` + `AUDIT_NO_SERVER=1` through
  `host.docker.internal`), baselines written under a platform key, determinism confirmed by a second
  comparing pass, and a copy-back step — all with the repo copied INSIDE the container so the host's
  `node_modules` is never touched.
- **Real defect fixed — baselines are now actually platform-keyed:** the snapshot path gained
  `{platform}` (`win32` / `linux` / `darwin`); container and native sets coexist and can never be
  compared across environments. Before this, the docs claimed platform keying while the config had
  no platform key — the first Docker user would have hit silent cross-environment diffs.
- **New `AUDIT_BASE_URL` knob:** the gate can target any already-running server (that is what makes
  the container-to-host mode possible) — including the Lighthouse pass, which had kept its own copy
  of the base URL until the container run exposed it. The same run documented a lasting rule:
  Lighthouse budgets are environment-scoped (a container reaching the host is not a localhost
  origin to Lighthouse — `is-on-https` fails by construction), so the container round-trip runs the
  visual projects, and the spec now warns when its origin isn't localhost.
- **Two pitfalls captured:** launching Docker Desktop from a harness shell (background-process form;
  the `cmd //c start` form silently opens a stray interactive cmd), and the docker-credential-desktop
  PATH failure that breaks pulls.

## 2026-09-21 — sharper checks, quieter failures (buildout v0.4.2 / vps-ops v0.9.5 / pack v0.14.2)

Follow-up hardening from the same live validation run — three more wrong paths made unenterable:

- **Committed-CSS presence is its own check now:** any route that loads with zero reachable stylesheet rules fails loudly (`no committed CSS reached <route>`) — with the sheets/rules counts recorded in the audit attachment — instead of surfacing as a wall of giant screenshot diffs that reads like a rendering mystery. Born from an auto-fix that let a build "succeed" while shipping an empty stylesheet.
- **Pre-push lockfile pre-flight** (vps-ops ref 40 §3): when `package.json` or the lockfile changed, `CI=true pnpm install --frozen-lockfile` must exit 0 BEFORE the push — deploys install frozen and `ERR_PNPM_OUTDATED_LOCKFILE` kills them there, never locally. The repair command (and why the flag is required) ships inline.
- **Publisher fix:** the release-asset verification step now pins `gh release download -R <owner>/<repo>` — unpinned from a non-repo directory it silently downloads nothing and the follow-up read fails.

## 2026-09-21 — every trap becomes a fix (buildout v0.4.1 / vps-ops v0.9.4 / pack v0.14.1)

The design-audit kit's first full contact with a production app turned each surprise into a
designed-out trap — the configs, the prompts, and the runbook now carry the remedies:

- **Configs ship validated:** html-validate `elements` overrides are documented as forbidden (they
  replace the built-in element metadata and flood the report with thousands of bogus findings —
  turn the single rule off instead); stylelint `import-notation` is pinned to `"string"` (auto-fix
  otherwise rewrites Tailwind v4's imports into a form the build silently resolves to an EMPTY
  stylesheet, failing every visual baseline with a giant diff); "red gate + empty report" is
  called out as its own class — a rejected rule option exits 2 with zero warnings.
- **New pitfalls section** (kit README + buildout ref 30): artifact run-order (the audit wipes its
  dump dir per run — audit first, validate HTML second, same session), raw-server-response dumps
  vs hydrated-DOM artifacts, lockfile discipline (`CI=true` installs are frozen; repair with
  `--no-frozen-lockfile`; a drifted lockfile fails the DEPLOY, not the build), and the
  pipe-masks-exit trap.
- **AUTO-FIX-PROMPT** names the known finding classes up front — fill-token-as-text dark-mode
  contrast, duplicate `<main>` landmarks, 320px header rows, and what deserves a reasoned
  allowlist instead of a fix — plus a one-`<main>`-per-page budget.
- **vps-ops `dlogs`:** one command prints the newest deployment's build log, tailed and greppable
  (`--grep`/`--deployment`/`--tail`) — build failures no longer need a bespoke script.
- **Release checkpoint (new hard rule 11):** the tags are the source of truth for the next
  version — read `gh release list` first, fix package.json/README drift in the release commit, and
  know the exact delete-and-re-cut path for a wrong tag.
- **Failure table:** `ERR_PNPM_OUTDATED_LOCKFILE` gets its own row with the exact repair sequence.

## 2026-09-21 — the front-end gate (buildout v0.4.0 / vps-ops v0.9.3 / pack v0.14.0)

Design QA was the last eyeball pass left in the pipeline. It is now a one-command gate that turns
"looks fine" into evidence the agent can act on:

- **New design-audit kit** (`buildout/templates/design-audit/`): 16 checks in one run — visual
  baselines per device (desktop / mobile / dark / WebKit + a Firefox smoke), WCAG 2.2 A/AA, console
  and page errors, failed & 4xx/5xx requests, horizontal overflow including a 320px reflow probe,
  touch targets, title/description/OG, Lighthouse perf/SEO/best-practices, broken links, HTML
  validity, CSS + jsx-a11y lint — all emitting ONE machine-readable report the agent reads via a
  one-line filter.
- **Assembled, not re-invented:** everything is a maintained OSS package wired together by two thin
  spec files; the research culled the traps (an abandoned Lighthouse plugin, a Lighthouse-12 pin, a
  visual tool asking for a new maintainer, cloud-only baseline stores, a paid parallel path, an
  unlicensed boilerplate) so the gate ships only what still works.
- **Deterministic baselines:** generated only in the pinned Playwright container, changed only by
  explicit update commits; a missing baseline fails instead of passing silently, and a no-Docker
  degraded mode is documented instead of pretended away.
- **The fix loop ships as data:** a packaged prompt that forbids the classic cheats (edit the
  snapshot, loosen the threshold, skip the failing test) and re-runs only the failed scope.
- **Change-pipeline hook:** user-facing changes on apps that ship the kit run the fast gate before
  release; the 5-line ship receipt gains one `Design:` line.
- Verified before shipping: fixture run 6/6 green + a Lighthouse pass; every dependency pin
  registry-checked the same day.
- **Fresh-eyes validated before release:** a zero-context agent followed the docs and installed the
  kit into a production Next.js app — 28 tests ran, baselines proved deterministic across repeated
  runs, and the run caught three kit blockers + a batch of traps *before* tagging (a quiet
  link-check that self-passed on zero links, an HTML-validator config/flag mismatch, the non-TTY
  install abort, ambient-config inheritance, lint reports drowned in build noise) — all fixed and
  re-verified in this release. It also surfaced four
  real issues in that app on its first run — the gate doing its job.

## 2026-09-21 — the build that was never running (buildout v0.3.3 / pack v0.13.3)

A local server kept answering **200** while the assets it pointed at no longer existed on disk. A
rebuild under a still-running process rewrites the chunk files, but the old in-memory manifest keeps
being served: the route renders its shell, the client-rendered part silently never appears, and nothing
is logged — so it reads as a defect in code that is fine. The restart that should have prevented it had
failed with `EADDRINUSE: address already in use`, in output nobody was reading.

- **New pre-flight rule** (buildout Hard Rules): before measuring anything on a local server, prove it
  is serving the build on disk — kill by PID → confirm 0 listeners → restart → freshness check.
  **200 is not evidence.**
- **`verify-ladder.md` gains a Freshness section**: the both-states observation (stale → 1 of 19 assets
  missing; after restart → all 200), the exact command block, and the note that a missing asset can
  surface as **500** as well as 404 — count any non-200 as stale.
- **Windows note**: `taskkill /F /PID <pid>` takes single slashes; `//F` is passed through
  literally and rejected (`Invalid argument/option - '//F'`).

## 2026-09-21 — verified means the schedule ran (vps-ops v0.9.2 / pack v0.13.2)

The first *scheduled* nightly failed while every manual drill passed. The deeper lesson is now a
pipeline rule, not a platform-scoped trap:

- **"A schedule is verified only by its own trigger"** — ref 55 §3 requires every scheduled leg
  (systemd unit · Windows task · cronjob · Coolify schedule) to fire once through the mechanism that
  will run it and leave a fresh artifact from THAT run before "backups live" may be claimed. Manual
  runs prove the script — never the schedule.
- **First-fire proof became an install step** in the backup template README: fire both units by hand,
  require `rc=0` + `status ok` + a fresh snapshot on each repo + the verify PASS email.
- Carried from the same incident (v0.9.1): `RESTIC_CACHE_DIR` pinned in the script (systemd carries no
  `$HOME`), all restic steps tee to the log, and every run opens with a `=== run start ===` marker so
  failure emails show the failing run.
**Why:** "verified live" that only exercises the convenient invocation path is a false green — both
backup legs had now failed exactly this way once.

## 2026-09-21 — the backup that never ran (vps-ops v0.9.1 / pack v0.13.1)

The first *scheduled* nightly failed with a clean "FAILED" email whose body showed the last drill's
output, not the error. Two stacked traps, both designed out:

- **systemd units carry no `$HOME`** → restic 0.19 hard-fails (`unable to locate cache directory:
  neither $XDG_CACHE_HOME nor $HOME are defined`); every manual test passed because interactive
  shells set HOME. The backup script now pins `RESTIC_CACHE_DIR=/var/cache/restic` itself.
- **`die()` tails the append-only log** → steps that didn't tee their output made the failure email
  show the PREVIOUS run. All restic steps now append to the log; each run opens with a
  `=== run start ===` marker.
Proven by re-running the exact failing unit end-to-end: status ok, fresh snapshots on both offsite
repos. Template, templates README and ref 55 carry both traps.

## 2026-09-20 — access before asks (vps-ops v0.9.0 · deckhand-profile v0.3.0 / pack v0.13.0)

Learning loop from a real deployment phase — fixed at the instruction level so it cannot recur:

- **Upfront scopes + capability probes:** Cloudflare tokens are created with the full pipeline scope
  set in one go (Zone read + DNS edit + Email Routing edit), and Cloudflare-touching phases open with
  cheap probe reads. The Email-Routing wall that bounced back to the user mid-task — because the
  token predated the need — is designed out; a later gap is a one-click token EDIT, never a new
  secret. A wall found in planning is one batched ask; found mid-wiring it is a stall.
- **Brand mailboxes end-to-end:** `support@`-style addresses are set up start-to-finish by the agent
  (probe → routing → destination → rule → DNS confirm); the flow's single unavoidable user click is
  batched + ledgered; contact-route smoke item added — a founder's personal inbox never appears on a
  live product.
- **deckhand-profile: access before asks + labeled asks.** Inventory existing access before ANY
  request; do it yourself when a token/API covers it; missing access = one batched ask with exact
  scope + click path. Every ask is `DECISION NEEDED` / `ACTION NEEDED` / `FYI` — no more "are you
  asking me a question?". Deferrals are recorded decisions, never re-asked.
- **New hard rule (ref 40):** reads mask credential-looking strings — a masked `Bearer …` retyped
  into an edit fails at runtime; edit around secret lines and grep for `***` after. Ship receipts
  (the 5-line deploy block) go in every shipped-pass report — they answer "did it deploy?".

## 2026-09-20 — release hygiene: the leak gate (pack v0.12.2)

- **New gate — `scripts/leak_sweep.py`:** one command scans the repo tree, the commit history and
  every installed skill copy for terms that must never appear in a public repo (the term list lives
  outside the repo — never committed), and `--file` gates a release-notes draft too. Non-zero exit on any hit.
- **New — `RELEASING.md`:** the release checklist at the repo root where the work happens — load
  `skill-pack-publishing` → run the gate → parity → zip → tag → release with product-only notes
  (improvements + fixes).
- **Fixed:** the public-record rule now explicitly covers release notes and commit messages, and it
  is enforced mechanically instead of depending on which skill was loaded when the notes were
  written.

## 2026-09-20 — shipped means released (vps-ops v0.8.0 / pack v0.12.0)

A live app's repo shipped with **no releases, no real README, and a stray starter LICENSE** — the
user had to ask. Fixed in the pipeline so nobody ever asks again:

- **The release rule (ref 40 §6b):** a deployed runtime change now ends *tag + GitHub Release* once
  smoke is green — SemVer, ≤8 user-facing bullets, no internal narration, no fluff. Docs-only commits
  deploy nothing and release nothing. First release in an app's life = **v1.0.0**, and it triggers the
  one-time repo-presence pass.
- **The repo-presence kit:** `templates/repo-presence/` + `scripts/repo_presence.py` — fill ONE JSON
  (content only); the script renders README (empty sections dropped, placeholder drift fails loudly),
  LICENSE (proprietary; upstream MIT retained when derived), `package.json` metadata, and sets the gh
  description + topics. Fill content — never rebuild structure. 7 new tests (51 pack-wide).
- **Corrected reality in ref 40:** "deploy: automatic via GitHub App" was false for a loopback-locked
  dashboard (verified live: zero webhooks, every deploy explicitly triggered). The loop, hard rule #8,
  and the SKILL invariant now say what actually happens.
- **v0.12.1:** the `gh`-target trap documented (a repo with an `upstream` remote makes gh aim at
  upstream — `gh repo set-default` or `-R`; live-verified).

## 2026-09-20 — the fresh-eyes audit (audit fixes across all five skills / pack v0.11.0)

Five **zero-context sub-agent audits** read every skill exactly as a first-time consumer would — then
every finding was fixed: buildout's dangling `library.py` path + working-directory/`python3` clarity;
vps-ops ref 10's Step-3b ordering trap (now ⏩ run-after-Step-4) and the env.sh clobber (`>` → `>>`,
plus `VPS_SSH_HOST/KEY` written); **`wait --expect-commit`** so a deploy can never be green-lit on the
previous build; backup docs aligned with reality (both-modes claim, `status.json` contract,
B2 region de-hardcoded + `B2_HOST/B2_REGION` emitted, `fix-clock.cmd` shipped, scoped-key 403
wording); session-autopsy's ref-budget conflict + a missing CHANGELOG; deckhand-profile's `asked`
field made required + read-first widened to "before starting any work"; component-library's store
renamed (`~/deckhand-library`, legacy honored) + `store-format.md` linked; pack "36 tests" → 44.
**44 tests green.**

## 2026-09-20 — the tunnel that heals itself (vps-ops v0.7.6 / pack v0.10.6)

The dashboard tunnel had to be remembered after every reboot — now it doesn't: `coolify_api.py
tunnel` health-checks and starts it as a detached background ssh (given `VPS_SSH_HOST`/`VPS_SSH_KEY`,
a one-time vault setting), and `deploy` preflights it automatically. **Proven:** after a reboot,
tunnel down → one command → `tunnel OK`. Deploys self-heal; nobody has to remember the tunnel.

## 2026-09-20 — the pull that never was (vps-ops v0.7.5 / pack v0.10.5)

A stale-backup alert traced to three independent faults stacked into one: (1) the Windows Task
Scheduler leg **never actually fired** (the wrapper pointed at a bash.exe that doesn't exist, and
battery conditions blocked the catch-up — an unverified schedule is not a backup); (2) the home pull
looked like "tigris hangs" but tigris answered in 0.3 s — the real time-eater was the local-S3
reachability probe retrying for minutes while Docker Desktop was off, killing the run inside its
time budget; (3) start-only log lines made a kill indistinguishable from a hang. All three are
fixed and verified: probe fails in 0.17 s, pull completes in ~2 s with per-step timings, the
scheduled task fires with `Last Result: 0`. The server side was green through all of it.

## 2026-09-20 — the dead-tunnel trap (vps-ops v0.7.4 / pack v0.10.4)

A deploy failed with `10061 connection refused` on `127.0.0.1:8000` — the SSH tunnel had died
silently (on Windows/git-bash, ssh resolves `$HOME` to `/home/<user>`, so a tunnel started
without a durable `known_hosts` exits on "Host key verification failed"). Fixed durably: verified
`known_hosts` in the vault, canonical tunnel command carries `UserKnownHostsFile` +
`StrictHostKeyChecking=yes`, `coolify_api.py` now prints the restart command when it sees a refused
connection, and ref 10 documents the symptom → cause mapping.

## 2026-09-20 — the checkpoint rule (buildout v0.3.1 / vps-ops v0.7.3 / pack v0.10.3)

One field failure is why this rule exists: the pipeline triggered correctly (loaded the
skills, read `OPS.md` + the pending ledger), implemented for an hour across 27 files — and never
committed once, so when the model stream was cut mid-turn, nothing was shippable. The fix is a hard
rule, not advice: **milestone → verify early → commit → continue**; wide requests ship in **passes**,
each deployed end-to-end; an interrupted run must leave committed, shippable work. Plus the
**deployed-app rule** in buildout: a project directory with `OPS.md`/`.vps-ops.json` is a live app —
local-only is never done.

## 2026-09-20 — the autopsy trigger, spoken plainly (session-autopsy v0.1.1 / pack v0.10.2)

The question every user asks: "can I just ASK it to learn?" — yes, and now the skill says so in the
exact words to use: **"run session-autopsy"**, said in the session that went wrong (it greps its own
transcript — nothing else needed). From another session: pass the session ID or paste the key errors
+ what finally worked. Evidence required, whole log not.

## 2026-09-20 — the WHERE field (deckhand-profile v0.2.1 / vps-ops v0.7.2 / pack v0.10.1)

Pending items now say **where** — not just what and how. Every item carries `WHERE:` with the exact
place a non-tech user can find the thing: a full file path, a URL, or a menu chain. Because "escrow
your restic passwords" is useless to someone who doesn't know what a restic is or where the files
live — and knowing where to look was the last excuse.

## 2026-09-20 — the pending ledger (deckhand-profile v0.2.0 / vps-ops v0.7.1 / pack v0.10.0)

Users don't lose track anymore. A second portable file joins the profile: **`~/.deckhand/pending.md`** —
the ledger of things only the human can do, with status (`open` / `waiting-confirm`), asked-dates,
"WHY it matters" and one-line HOWs. The skills now record items the moment they ask, surface the open
list in every report, close items with a date when done — and the scheduled watchdog nags until each
item is closed. Conditional items (`when: paid launch`) don't nag before their trigger. The profile
template now also carries the standing card-free rule and the backup/automation stack.

## 2026-09-20 — the home S3 option (vps-ops v0.7.0 / pack v0.9.0)

The backup destination question gains another flavour: put the home copy behind a **local S3 with a
real UI** — RustFS in Docker (Docker Desktop), one compose file, browseable console at
`localhost:9001`, and the pipeline's pull mirrors every provider into it automatically (with a
graceful skip when Docker isn't running). Plus a **clock-skew preflight** in the home pull, so a
clock-skew failure can't recur silently.

## 2026-09-20 — the backup drill, proven end-to-end (vps-ops v0.6.0 / pack v0.8.0)

The backup pipeline went through a full production drill on a live deployment — every layer is now
proven, and every trap it surfaced is baked into the skill so nobody re-discovers them: a Tigris bucket
that listed objects but served 0-byte reads (wrong storage class — agents now create buckets via API
and prove readability with a 512 KB round-trip), Coolify's per-container DB users, empty executions
endpoints (the bucket listing is the proof), restic's lack of per-repo credentials, CRLF env files
that hang restic, and Windows clock skew breaking SigV4. The deep layer (restic → B2 + Tigris,
nightly timers + a weekly restore drill that really restores and emails PASS/FAIL) and the home copy
(rclone sync to the owner's PC; Windows Task Scheduler **or** an agent cronjob watchdog) are
template-fresh and verified.

## 2026-09-20 — backups are a choice (vps-ops v0.5.2 / pack v0.7.2)

Every user gets the same deploy-time question the tracks get: **where should the backups live?** —
cloud dual (smart default), cloud + a home copy, or home only (no cloud accounts at all). The home
copy is a **pull** model, so it works behind NAT and nothing ever reaches into the user's network:
mirror the cloud buckets with rclone, or SSH-pull dumps straight off the VPS into a local restic repo
with the exact same tooling the cloud path uses. Scheduling is the user's pick too — plain cron,
Task Scheduler, or an **agent cronjob ("the bot")** that also runs the freshness check and emails on
failure. One script covers both modes: `templates/vps-backup/local-pull.sh`.

## 2026-09-20 — the card-free rule (vps-ops v0.5.1 / pack v0.7.1)

Two card walls confirmed in practice: R2 won't activate without one, and B2's caps UI is gated too.
The pipeline rule is now explicit — **the free path never asks for a card** — and the provider list was
re-researched to match: the second backup target defaults to **Tigris** (5 GB free, zero egress,
official MCP, no card), with Filebase and Koofr as verified fallbacks; R2 stays as an optional
card-holders' upgrade. Verified live: card-less Backblaze hard-caps accounts at the free-tier boundary
(refused with 403 `cap_exceeded` — never billed), so the primary target is safe without a card, with
loud `cap_exceeded` alerting as the guardrail.

"A backup never stays on the same VPS" is now the pipeline's default: dual offsite targets — Backblaze
B2 primary (hard spend caps, fully API-driven after signup) + Cloudflare R2 secondary (free egress) —
with 3-copy retention so usage stays flat inside the free tiers. Agents configure everything through
Coolify's API (S3 storages, per-target schedules, volume backups with S3-only streaming, backup alerts
into the app's mail chain), verify by listing buckets and running real restore drills, and there's a
deep restic layer for full-VPS disaster recovery. Apps that need uploads get RustFS 1.0 (Apache-2.0;
MinIO CE is dead) with its own two-layer offsite copy. Human steps stay at ONE batched ask.

The chain's coverage is now complete and proven: Brevo's corner closed via its API (domain created,
records added, `authenticate` → verified — plus the new-IP dance: a one-click email to the owner,
both the setup machine and the server authorised). And the alerts got a plain-language pass:
owner alerts now say what happened, that nothing is broken, and that no action is
needed. Drilled end-to-end: every provider has carried real mail, and every restore returned the primary.

A full password-reset cycle ran on a live deployment, failover drill included — the run's findings,
folded back: Resend's onboarding key can't manage domains
(a Full-access key is needed for setup), Brevo needs the server's IP authorised before it will
answer at all, Resend's DNS record set corrected to the API's actual output, Mailgun verified with
SPF+DKIM alone, and two field rules for Next.js/Coolify deployments (read env lazily or the CI
build breaks; env changes need a redeploy). The mail-router template carries the fixes. Verified: full reset cycle + "drain primary → next provider carried → restore" drill.

## 2026-09-19 — key handover, spelled out (vps-ops v0.4.1 / pack v0.6.1)

From real walkthroughs: users have no idea *which* key to create, and "add them to
the Coolify env" means nothing outside of dev circles. Ref 70 now walks it provider by provider —
Resend (key prompted at signup; testing address caveat), Mailgun (Settings → API security → Create key,
**Developer** role), Brevo (**API key**, NOT the MCP server key) — and the hand-over ask has a clear
default: paste to the agent (vaulted chmod 600, never echoed) or take the click-by-click Coolify guide.

## 2026-09-19 — auth + login email: the free failover chain (vps-ops v0.4.0 / pack v0.6.0)

"No email, no business." Four research agents verified the September-2026 landscape, and the pack now
ships the missing piece — **login email that actually arrives, at $0**:

- **Auth verdict:** Better Auth (MIT) — verification/reset/magic-link built in, Drizzle `pg`, env-only
  config; Auth.js v5 is still beta + security-patches-only; Lucia is deprecated. The new ref carries
  the Coolify/Traefik/Next-16 gotchas with their exact error strings.
- **Free email chain:** Resend → Mailgun → Brevo (SMTP2GO as the no-branding substitute) behind a
  drop-in `send.ts` router: silent failover, Postgres quota accounting, never retries a bad recipient,
  alerts the owner through the next healthy provider when one throttles — plus the deliverability
  design (one sending subdomain per provider, single SPF include each, DMARC on the root) that makes
  multi-provider sending safe.
- **MCP catalog (modular):** DNS/registrar (Cloudflare, Porkbun, NameSilo official servers) and email
  servers — agent-vs-human autonomy table, never-install-globally policy; extend by appending a section.
- Human steps stay at a single batched ask: create the free provider accounts. DNS records, env wiring
  and the router are agent work.

## 2026-09-19 — deckhand-profile v0.1.1: cold start first-class (pack v0.5.1)

The user-profile create flow now treats the ~90% case as the main path: **cold start** says plainly that nothing is on file yet, then runs the initial interview in one batch (defaults offered; the answers ARE the profile). Context-rich sessions keep the draft-and-ask-only-gaps branch. New **source rule** (SKILL + ref 10): the profile is built ONLY from this workspace and the user's answers — never imported from harness profiles or memory files, so it cannot drift. Updates follow real work as one-line offers; unknowns are omitted, never guessed.

## 2026-09-19 — deckhand-profile: the user, once (pack v0.5.0)

Fifth skill: **`deckhand-profile`** — one portable file, `~/.deckhand/profile.md`, that holds what the pipeline needs to know about the USER: accounts, providers, defaults, preferences. Harness-independent and user-owned (copy it anywhere, edit by hand); no secrets, references only, ≤60 lines, no garbage. Agents read it before asking anything — the read-first rule is wired into vps-ops (SKILL + ref 00) and buildout. Create flow: "create my deckhand profile" drafts from what the agent already knows and asks only what's missing (one batch). Update flow: one-line diffs, offers rather than silent edits. Ships ref 10 (field format) + a fill-in template. Complements `OPS.md` (project cold-start) with the user-level cold-start.

## 2026-09-19 — session-autopsy: failures become instructions (pack v0.4.0)

New fourth skill: **`session-autopsy`** — the learning loop the pack was missing. Call it after any red → green run ("learn from this session", "why did it fail"): it collects evidence cheaply (grep the errors and the fix commit — never full transcripts), walks the cause-chain to the instruction that allowed the wrong path, and fixes it on a strength ladder — **eliminate → pre-flight → reorder → gate → pitfall** — with pitfall entries counted as debt. Ships refs 10/20/30 (evidence routing · the ladder with live cases · how to write the fix) and a ≤40-line report template; hands off to the publishing procedure. Validated against the day's own failures: version-pin CI traps land as rung-2 pre-flights, action order as rung-3 reorder, a dev-seed credential leak as a first-run step, the Windows folder lock as the one legitimate pitfall.

## 2026-09-19 — CI-safe package-manager pin (vps-ops v0.3.1 / pack v0.3.2)

The `packageManager` pin that makes deploys reproducible can break a repo's own CI in two ways — both now pre-listed in the deploy runbook's repo-traps: a workflow that also pins pnpm dies with `Multiple versions of pnpm specified` (ERR_PNPM_BAD_PM_VERSION); and on the Node-24-era action majors, `pnpm/action-setup` must run before `setup-node` (v5 auto-caches the pnpm store and needs pnpm on PATH). One source of truth, canonical step order — verified red → green on a real repo.

## 2026-09-19 — cold-start handoff (vps-ops v0.3.0 / pack v0.3.1)

Every deployment now finishes by writing **`OPS.md`** into the app repo — the single file a future session (human or agent, zero context) reads first: live URL + health checks, server + SSH, Coolify ids, dashboard access, a **secrets inventory by location only**, domain/DNS, and the copy-paste commands for the everyday loop (deploy a change, migrate, logs, owner re-key, smoke) plus the app-specific landmines. New `templates/OPS-handoff-template.md`; the deploy runbook gains §9. No re-discovery, no wasted tokens — the door into any deployed app is one committed file.

## 2026-09-19 — rebrand: Deckhand (pack v0.3.0)

The pack has a name now: **Deckhand** — *bring a $5 server and a $10 domain; your agent turns them into a live business while you go find the clients.* The name carries the insight: the barrier was never the money — it's the overwhelm. That pile of unfamiliar tech is the deckhand's job.

- Repository renamed `expert-build-pack` → `deckhand` (GitHub redirects old links automatically).
- Skill `expert-build-pack` renamed **`buildout`** ("idea → codebase"); cross-references in `vps-ops` and `component-library` updated. Invocation: `/buildout`.
- README rewritten around the cost reality (~$5/month server + ~$10/year domain = the whole door) and the human's job (finding clients). Social-preview + logo assets carry the new name.
- No functional changes to the runbooks; 36 tests green; zip == repo.

## 2026-09-19 — paid track validated live (vps-ops v0.2.2)

A real Next.js + Postgres SaaS was taken from a private repo to a live HTTPS domain on a rented VPS
(Coolify → Cloudflare DNS-only → Let's Encrypt; migrations, seed data, production owner). Every error
the deployment surfaced is now a pre-listed step — that is the whole point of v0.2.2:

- ref 10: new **Step 3b** — host firewall rules do NOT stop Docker-published ports (live-tested:
  0 packets, still reachable); lock the dashboard by loopback-binding 8000/6001/6002 in Coolify's
  compose and re-apply after Coolify upgrades. Plus: `1|…` tokens must be single-quoted; on Windows
  forward 8000 only (6001/6002 can be reserved ports and kill the tunnel).
- ref 12: provider notes — order-to-key flow, no cloud firewall, SSH key install, 4 vCPU / 8 GB
  sizing confirmed for the full stack.
- ref 30: pre-flight repo traps (`packageManager` pin + valid `pnpm-workspace.yaml` — the first
  build died on `packages field missing or empty`); Postgres `start` recovery; new §6b —
  container-side migrate → seed → production-owner flow (and removing dev seed credentials).
- 36 tests green; zip == repo.

## 2026-09-18 — provider price sheet (vps-ops v0.2.1)

- `vps-ops` v0.2.1: new `references/12-provider-price-sheet.md` — Oracle free tier, Contabo Core
  4/6/8/12, Hostinger KVM 1–8, Hetzner CAX11/CX22/CX42 with USD/CAD guidance and sizing rules, so
  provider choice never needs re-research. Suggested order: Oracle → Contabo → Hostinger (Hetzner
  with a price caveat). Ref 11 points at it.

## 2026-09-18 — free-preview track (vps-ops v0.2.0)

- `vps-ops` v0.2.0: new **free preview** track — Oracle Cloud Always Free (2 OCPU / 12 GB Arm) + free `.pp.ua` domain (nic.ua) + Cloudflare DNS-only + Coolify Let's Encrypt, plus a migration runbook to a paid host. New refs `11-oracle-free-tier`, `21-free-domain-cloudflare`, `60-migrate-to-paid`; new `assets/oci-cloud-init.yaml`; SKILL.md two-track routing; user-checklist §3b.
- `expert-build-pack` v0.2.2: cross-links to the free-preview track (buildout step 5 + routing row); frontmatter version corrected (was stale at 0.2.0).
- Research: 5 parallel agents, primary-source-verified — Oracle A1 Always Free halved to 2 OCPU/12 GB (Jun 2026); nic.ua free-order card gate + Telegram activation; Cloudflare accepts `.pp.ua` (PSL); Coolify v4.3.23. First live run pending. 36 tests green.

## 2026-09-17 — live validation pass

- `vps-ops` v0.1.0: full live drill on a real Coolify instance — deploy (image / public repo / private repo), change pipeline, rollback, Postgres provision + query, backups + restore, Dockerfile build pack. 23 tests.
- Fixed from the live drill: deployments API response shape + `finished` status, `envset` HTTP 201, rollback requires the full 40-char image tag, database `initdb` false-unhealthy window, custom-format dumps, database container naming.
- `expert-build-pack` v0.2.1: Buildout Engine hardened. Registry pool 372 → 282 healthy; catalogs velora 64 / reui 1,773 / cult-ui 157. 9 tests.
- `component-library` v0.1.0: save / load components. 4 tests.

## 0.2.0

- Buildout Engine: living MIT registry pool, coherent-random design assembly, design token locking, `component-library` companion skill.

## 0.1.0

- Initial release: expert references, execution-first loops, machine-first handoffs.
