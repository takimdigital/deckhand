# Changelog

## [2.2.1] — 2026-09-25 — try-on: the owner's page never stays broken

Three errors an owner hit in try-on on a Next 16 app (Turbopack), each replayed in Chromium against a Next 16 dev
server and fixed with a regression test (`tryon/test/field.test.mjs`, a fake dev server that lags like a real one).

### Footer swap: `Unexpected token '`', "`tel:${c.p"... is not valid JSON`
- Link lists are now built as JS source, not JSON: an href like `` `tel:${c.phone}` `` and a label like `{c.phone}`
  travel as code, so the phone and email show their real values in the design.
- A name bound inside the picked element (a `.map` item) never leaks into the usage, where it would not exist.
- The owner's titled link columns (Contact · Company) flatten into a design's single link list: the footers that
  were all skipped as POOR_FIT now carry the owner's links.

### Discard, then pick again: `ELEMENT_NOT_FOUND … blocks.tsx:64:7`
- The overlay now sends what was clicked (tag + start of its text) with the stamp. The engine checks that the element
  at the stamp is that one, else finds it again nearest the old line (`pickElement`). A stamp that lands on another
  element is never swapped by mistake. If it cannot be sure: `ELEMENT_NOT_FOUND` with `reload`, and a **Reload the
  page and pick again** button; nothing is written.
- After Keep or Discard the file has moved under the page, so the next pick reloads the page first.
- Swap, Tune and the AI draft request share the same lookup.

### A design needing `@radix-ui/react-toggle` broke the app, and it stayed broken
- **The import check** loads every import a staged design makes, from the project, before wiring it:
  - named imports must exist, and so must `NS.Part` / `<NS.Part>` reads of a namespace import;
  - a package the import itself needs must be installed (`radix-ui/toggle` → `@radix-ui/react-toggle`).
  A design that fails is skipped as `BROKEN_IMPORT` (lucide 1.x has no `Github`, for example), and the next
  candidate takes its place.
- **Install-free designs first.** A running dev server may not see a newly installed package, so designs that need
  an install are offered only when too few others exist. A project with the `radix-ui` umbrella gets
  `radix-ui/<part>` imports instead of an install.
- **The page still builds, or nothing stays** (`openVerified`: the helper's open and More, and `tryon try` with a dev
  URL):
  - The page is reloaded until the dev server shows the new variants or an error. A file watcher lags the write, so
    the first answer can be the old page.
  - An error restores the file at once, drops the variants it points at (their folder in the trace, else the module
    they cannot load) and reopens the rest. The bar says how many were removed.
  - If nothing can be kept, `BUILD_BROKE` with the file restored.
- A package installed for a try stays in package.json and is now named (`installedKept`, on Discard too).

## [2.2.0] — 2026-09-25 — proven paths, and runs that improve them

A real run on Hermes (Windows, git-bash: a cleaning-company boilerplate sold as a product) was dissected to the tool
call. Each of its 20 problems is fixed in code with a regression test (`tests/test_field.py`), and the path it took
became the first workflow.

### Workflows — the path any AI follows, step by step
- **`dh workflow query`** returns the 3 workflows that fit the project best, from three pools: yours
  (`~/.deckhand/workflows/`, never shared), the base set shipped with Deckhand, and the community pool
  (`workflows/community/`, read through its index — thousands of workflows cost 3 rows of context). Scores explain
  themselves; trades match through families (`data/industries.json`: a plumbing kit finds the cleaning one).
- A workflow is one JSON file: what it fits, its proof (levels computed from runs: draft → proven → trusted), the
  questions to ask up front (including those past runs learned too late), and phases → steps with the exact command,
  what it must print and what to do when it does not; `creative` names what it leaves to the AI.
- **`dh workflow use REF`** pins it; `dh next` then prints its open steps, and every `dh` command ticks the step it
  completes. A state-changing command no step names is recorded as a deviation. `dh workflow todo` exports the
  checklist for any harness's todo list; RESUME and `dh next` carry a `WORKFLOW …` status line.
- **Lint** refuses what an AI must not run: private calls, one user's absolute paths, credential-shaped values, `dh`
  commands that do not exist (checked against the real parser) and, for base/community, anything off the allow-list.
  Non-dh commands in your own workflows are shown to the owner before a first run (`--accept`). A community file must
  match its index hash. Rendered text never holds `{x}` or `<x>` (Hermes' `delegate_task` refuses a batch that does).
- `dh workflow new --from-run` turns a run into a draft; `dh workflow publish` writes a strict bundle for a community
  pull request (nothing is sent). `scripts/workflows_index.py` builds and checks the community index (CI).
- Base workflow **home-services-saas-product** (draft), from that run and its review.

### The workflow autopsy — runnable at any moment
- **`dh autopsy --workflow`**: the timeline (active time, pauses, every gate and whether it passed on the owner's
  words), every question put to the owner with the answer and what it changed — LATE (asked after define),
  DIRECTION-CHANGE (it re-opened work), PARAPHRASED (a gate passed on an agent's note), LOST (the harness dropped the
  message) —, deviations from the workflow, what each failure cost (minutes, attempts, the step it hit), the
  sub-agent batches, counts on how the AI talked to the owner, then **proposals with their reason and evidence**.
  `--part` hands one section to a sub-agent. A separate report collects Deckhand's own issues for its maintainer.
- **`dh workflow save --from-autopsy W --proposals P1,P3 [--public]`** applies the accepted ones (a learned question
  asked in the define round from now on, an added or optional step, a pitfall), adds the run as proof, bumps the
  version and records why. The skill itself is never edited.
- **The autopsy reads Hermes**: its `state.db` (read-only; the current session inside Hermes, its compression lineage,
  its sub-agent batches), `hermes sessions export` files, and any chat JSONL — the plain `dh autopsy` too.

### Fixes from the field run
- **Gates pass on the owner's words**: `dh gate pass Gx --quote "…"` in phased mode; a change request ("make it like a
  real business") is refused and points to `dh reopen` (the run passed G1 on the agent's paraphrase).
- **A base lands in the planning folder**: clone and scaffold accept a folder holding only Deckhand's files (they step
  aside and come back); `dh base record` states a base built another way (the run imported a private function).
- **Services**: `dh dev add db --cmd … --port N` — started before the app, restarted when dead, stopped together,
  shown DOWN in RESUME (the run kept its database alive by hand for hours, then lost it in a pause).
- **Ports**: bind-tested, Windows reserved ranges skipped (`verify`'s fixed 4100 sat inside one on the owner's
  machine), `HOSTNAME=127.0.0.1` for servers Deckhand starts (git-bash exports the machine name), a port the dev script
  pins is kept; `dh dev port --from N`.
- **`dh plan split --agents N`** writes exactly N `AGENT-n.md` packages grouped by the routes each owns — never two
  agents in one folder — plus `CONVENTIONS.md` (frozen files, the dev server is the orchestrator's, no production
  build, scratch and test-data rules, reporting). `dh bb flag|wait` hand off between builders (the run got 22 packages
  for 4 builders and wrote its own conventions by hand).
- **`brief.deliverable` own | client | product**: a product's fictional demo company is allowed in its seed, the SEO
  facts are the buyer's (not PENDING), and `dh verify` checks the buyer's kit (README, LICENSE, CUSTOMIZE.md, seed and
  reset scripts).
- `dh run -- dh …` resolves `dh`; research notes must carry a fact; research queries use a short `category`;
  `dh pool add D:/project --mine` measures the owner's own folders and `pool list --mine` filters.
- Windows and PGlite lessons seeded (HOSTNAME, EBUSY under `.next/standalone`, reserved ports, `/tmp`, MSYS paths,
  one-connection PGlite): `dh run` prints the fix the moment one reappears.

### Any harness, its own syntax
- `dh next` returns `harness`: the detected harness's syntax for what the phase needs (`data/harness.json`).
  `references/harness.md`: Hermes in full (background terminals + `process_manage`, the 180/600 s limits,
  `execute_code` state loss, `delegate_task` rules, `browser_navigate` and localhost, `write_file` refusals, where
  sessions live), Claude Code, Codex, Cursor and the rest. The installers update a Hermes copy filed under a category
  folder instead of adding a second one.
- `references/team.md`: parallel builders on Deckhand's rails (foundation first, one batch, packages sized to finish,
  re-cut at the artifact seam, trust only what you re-ran, panels on demand). `docs/FIELD-TESTS.md`: how to test the
  skill itself with a team of agents.

### What to do next — suggested, never guessed
- **`dh suggest`**: after the pending list, every report ends with a few optional suggestions ranked NOW · SOON · LATER,
  each with its reason and the exact command. Twenty rules read the project's files: unsaved work, the owner's turn at a
  gate, a deferred item now due, a service down, the same command failing again, research changed after its verify, the
  plan edited after approval, code changed since verify, failures worth an autopsy, a checkpoint to review, workflow
  proposals waiting for a choice, a finished run to keep (as a workflow, a base, a handoff), old pending items, a fresh
  session that is safe, monthly SEO, bots, the maintainer report. The autopsy command is the right one for the harness
  (`--latest` inside Hermes and Claude Code). `dh next` never suggests what it already says; `dh suggest dismiss ID`
  quiets one for a week; the same files give the same list. RESUME shows them after "Waiting on the owner".

### Audit fixes (edge cases found walking a full run)
- Deckhand's own guard refusals (a gate refused on a change request, a missing quote, a secret in a pending item…) are
  decisions, not failures: they no longer block "safe to start fresh", never become autopsy episodes or proposals.
- A skipped phase is one recorded fact, not a list of not-run steps; a gate step is ticked by `dh gate pass`, never
  marked not-run when its phase ends; brief changes, gates and re-opens are not path deviations.
- A re-opened phase becomes a proposal for a question to ask up front, even without a chat transcript.
- Workflow ask steps carry their questions and defaults (they survive a compaction); pinning the same workflow again keeps
  its progress.
- Moving Deckhand's files aside rolls back when a file is locked (Windows), and never overwrites an interrupted hold.
- A community index row must carry a safe id, an integer version, a plain file name and a sha — anything else is ignored.
- A key pasted in chat is masked in every autopsy report; a pending item refuses a secret (it names where the secret goes);
  a hand-closed SEO pending line explains how it closes itself; a CRLF ledger edited by hand still reads and writes.
- Hermes compaction summaries are not counted as the owner's messages.

### The owner's own files (the v1 `deckhand-profile` skill, fully absorbed)
- **`dh pending add|decide|done|drop|wait|list`**: this project's `PENDING.md` or the owner's cross-project
  `~/.deckhand/pending.md` (`--machine`), same line format as before; HOW and WHERE required; `when:` deferrals are not
  re-asked; `dh next` and RESUME list both ledgers with ages.
- `dh profile show|doctor` read `~/.deckhand/profile.md` (`notes_md`): what it answers is never asked again.
- SKILL.md: access before asks (do what access allows, prove a wall with a probe), a secret pasted in chat is vaulted
  and the owner told it sits in the history, an unclear ask is re-issued as one labelled line.

## [2.1.0] — 2026-09-25 — research you can check, not trust

- **Claims with proof.** Research facts live in `research.json → claims[]`, each with a label (VERIFIED ·
  SECONDARY · INFERRED · NOT_FOUND), the page's url and a verbatim quote. INFERRED names the claims it is derived
  from; NOT_FOUND says what was tried.
- **`dh research verify`** fetches every cited page and checks each quote is really on it (visible text only:
  a sentence hidden in a script does not count; curly quotes, non-breaking spaces and `…` joins are handled).
  Pages that block robots or draw themselves with JavaScript are reported as unchecked, never as failed. Page text
  is cached (gitignored), so `--offline` re-checks without the network.
- **Vocabulary harvested, never invented.** `vocabulary[]` holds terms copied from real pages (kind customer,
  trade or search) with a quote that contains the term. Guessed terms hurt search exactly on unfamiliar niches
  (Abe et al., SIGIR 2025), so the plan, the copy and the SEO use harvested ones.
- **A research card** (`references/research-card.md`, ~40 lines) is the only search guidance an agent reads:
  query → read snippets → diagnose → one change; never reword a failed query; stop at DONE_WHEN.
- **`dh research brief --focus F --agent ID`** pre-fills each agent's questions (target, primary source, when
  to stop, whether it goes stale) from `data/research.json` and the owner's brief.
- **One shared source list** (`dh research add` / `dh research seen`): parallel agents never read the same page
  twice; each writes only its own `research/agents/ID.json`, and `dh research merge` is the single writer.
- **`dh research score`** measures a research run from its session log (Claude Code, including sub-agents, or
  any one-JSON-per-search trace): searches, page reads, duplicate reads, repeated queries (one word added or
  removed counts as the same query), zero-gain streaks, tokens, and searches or tokens per proven claim.
  `--baseline` compares two runs.
- **The research phase** is done only with claims, ≥ 3 harvested terms and a `dh research verify` run after the
  last edit.

## [2.0.0] — 2026-09-25 — Deckhand v2 (full rework)

One skill (`skills/deckhand`), one control plane (`dh`), one try-on engine. The five v1 skills
(buildout, vps-ops, component-library, session-autopsy, deckhand-profile) are merged; their proven parts
were ported, not rewritten (the Coolify/Hostinger/backup clients and their 40 tests, the ops runbooks,
the measured template pool).

### Why v1 try-on never worked — and what replaced it
| v1 defect (measured) | v2 |
|---|---|
| every click needed the LLM in a polling loop (`wait --follow` + `handle` per pick) — harness-dependent, token-costly, stalls when the agent is busy | the helper does every write itself; the agent is not in the click loop (0 model calls per swap) |
| whole sections were refused ("blocks are never swapped in v1") — the one thing owners wanted | sections are the main case: hero, features, pricing, cta, faq, testimonials, footer, logos, stats, team, contact, login/signup |
| only the item's FIRST file was staged; registry dependencies ignored → broken imports | every file fetched; imports followed recursively; the site's own ui primitives reused |
| a swap flipped a file-wide import (every `<Button>` in the file changed) | element-precise wrapper at the clicked JSX node |
| the owner's words were lost (demo copy shown) | content transplant: headings, text, prices, CTAs+links, images, inputs, `.map()` list data, card-by-card |
| colours were the registry's | palette classes → the site's tokens; missing tokens derived from the site's own colours |
| the Tailark source was the paywalled `tailark.com/r` (401) → 8 free heroes | the MIT OSS source (GitHub) → 300 free blocks; catalog 738 items |
| the parser was the project's `typescript` → TypeScript 7 (no JS API) broke it | vendored `@babel/parser` (MIT) |
| Turbopack rule `as: '*.tsx'` renamed modules → every `'use client'` import broke | no `as`; verified on Next 16.3.6 |
| proxy-less overlay depended on patching the root layout | reverse proxy injects the overlay (any framework); Host/Origin rewritten to `localhost` so Next's dev guard allows HMR |
| demo stock photos / fake "trusted by" logos / "Get a Demo" buttons shipped | replaced by a placeholder / hidden / removed on keep; `dh verify` blocks what remains |

### Found on Google and in AI answers (`dh seo`)
- **One policy, `data/seo.json`.** It holds 53 rules (51 checked automatically, 2 on the manual checklist) across crawl, titles, content, structured data, local,
  social, languages, speed, trust and AI answers, each with a why, a fix and a note on whether a script can fix
  it. It also lists 15 owner facts, 5 owner-only actions, and the AI crawler lists. Checked against 2026 guidance:
  - FAQ rich results were removed on 2026-05-07;
  - Google ignores llms.txt;
  - ChatGPT search and Copilot draw on Bing;
  - Core Web Vitals thresholds;
  - local ranking factors.
- **`dh seo apply`** (AST engine `tryon/lib/seo.mjs`, journaled, `dh seo undo` byte-exact) adds or improves and
  never overwrites the owner's words:
  - Next.js App Router: robots, a sitemap from the plan, a root-layout title template, metadataBase,
    description, Open Graph, Twitter card, and a noindex switch for previews (`DH_NOINDEX=1`);
  - per-page canonicals; the inherited root-layout canonical is removed;
  - `<html lang>`, JSON-LD built only from confirmed facts, a 1200×630 share image, a manifest, a real 404,
    llms.txt and an IndexNow key;
  - Vite and static sites get the same through `index.html` plus static files.
  A real `next build` of the output was proven on Next 16.3.6, both in production and in preview mode.
- **`dh seo audit`** checks the source, the rendered pages and the live host. It writes `.deckhand/SEO.md`, and
  launch-breakers block the `seo` row of `dh verify`.
- **By path:** SEO goes in by default for new and existing sites; for bases it is a DECISION NEEDED, repeated at G4.
- **PENDING.md** gets a "Detected by dh seo" block with every missing owner fact and action, with WHY/HOW and the
  first-asked date. `dh next` returns the open items on every call.
- **Deploy:** `dh deploy ship` pings IndexNow on production, and `dh deploy target` gives the preview noindex
  instruction.

### Resume from any session, any AI (`dh resume`)
Long chats lose quality, and starting a fresh one used to mean losing where things stood. Now the project
itself says where it stands.
- **`.deckhand/RESUME.md`** is regenerated after every `dh` command, success or failure, from the project's
  files: stage, the exact next command, what is done with its proof, passed gates, try-on sessions still open,
  the last unexplained failure, uncommitted files, the owner's decisions, what waits on the owner, recent
  events. It stays under ~1,500 tokens, it is not a model recap, and it is local only (gitignored).
- **`dh note decision|doing|next "…"`** records what would otherwise live only in the chat (redacted).
- **A computed switch verdict**: "SAFE TO START A FRESH SESSION: YES/NO (why)". It says NO when files changed
  after the last note or a failure was never explained. `dh next` offers a fresh session right after a gate
  passes when nothing lives only in the chat.
- **`dh resume --check`** re-proves the claims: phase checks re-run, `dh verify` against HEAD and later edits
  (verify now records its commit), the brief or plan edited after G1, the dev server, the live commit, open
  try-on sessions. Drift exits 1 (`DRIFT`).
- **Cold start everywhere**: `dh init` writes a marked block in the project's `AGENTS.md` (and `@AGENTS.md` in
  `CLAUDE.md`) telling any AI to run `dh resume` first. `dh resume --install-hook claude` (or
  `install.sh --claude-hook`) adds a Claude Code SessionStart hook: new, resumed, cleared and compacted sessions
  in a deckhand project start from the RESUME; elsewhere it prints nothing.
- **Per-project profile and vault** (`.deckhand/profile.json`, `.deckhand/vault.env`, gitignored, never pushed):
  a project's layer overrides the machine's. `dh init --for client` keeps that client's settings and secrets in
  its own project by default (the app folder made by clone, adopt or scaffold inherits it), so client A's keys
  are never visible in client B. `--here` / `--machine` choose
  the layer explicitly. Older projects get the new gitignore lines added to their existing block.
- **`HANDOFF.md`** lists `dh resume` among the everyday commands and says where the Coolify token really lives
  (the client's project vault when it is there).
- **Releases** are published by `.github/workflows/release.yml` from `docs/releases/<tag>.md` after the version
  check (RELEASING.md).

### Security (final audit)
- **One secret policy** (`data/secrets.json`) for every scanner: verify, harvest, vet, tryon save. Now also
  catches Coolify, Anthropic, OpenAI, GitLab, npm, SendGrid and Telegram tokens, Stripe webhooks, and
  Slack/Discord webhooks.
- **Run logs can no longer leak.**
  - `.deckhand/runs.jsonl`, `failures.jsonl`, `dh run` output, autopsy reports, lessons and playbooks are redacted:
    known patterns, credential-shaped assignments/headers/URL passwords, and every value in the vault.
  - `dh init` and every build path gitignore deckhand's run logs.
  - `dh verify` scans `.deckhand/` too and blocks when the logs are not ignored (row `logs-ignored`).
- **One vault.** The server runbooks store tokens with `dh vault set` instead of v1's `~/.vps-ops/secrets/env.sh`.
  - Values are single-quoted, so sourcing the vault is safe; Coolify tokens contain `|`.
  - The Coolify and Hostinger clients read the vault.
  - v1's keyring is still read as a fallback; SSH keys stay in `~/.vps-ops/ssh/`.
  - `CF_API_TOKEN` became `CLOUDFLARE_API_TOKEN`; the old name is still accepted.
- **Input validation.** Site knobs, Tune dials and session/draft ids from the helper API or the CLI are validated
  (`BAD_THEME`, `BAD_DIAL`, `BAD_ID`). A crafted theme value can no longer break out of the stylesheet comment.
  Tune refuses generated files, and a closed tune session stays closed.

### Fixed (final audit)
- `dh run -- <cmd>` crashed with a Python TypeError whenever the command failed, the exact moment it should print
  the known fix. `DhError` now takes code/message positional-only, and the CLI output always keeps its own
  ok/code/message.
- Dangling references now point at real commands:
  - `tryon theme --undo` exists now;
  - `dh deploy logs` → `dh deploy raw dlogs <app-uuid>`;
  - `dh verify --scope` is gone from the work-package template.
- v1 paths in the ported ops scripts and templates (`references/10-…`, `scripts/…`, `templates/repo-presence/…`)
  now point at their v2 locations. The installers end with the v2 first sentence.
- `scripts/test_repo_coherence.py` makes this permanent. It fails CI when:
  - a doc or hint names a dh/tryon command, action, flag or skill path that doesn't exist;
  - a command is undocumented;
  - a markdown link is dead;
  - the README's test counts are wrong.

### Added
- `dh` control plane (stdlib Python): phase state machine with gates, `dh next` (one instruction + one
  reference + the relevant lessons), brief, profile + vault + capability doctor, pool query/add (remote
  measuring), plan init/lint/render/split (interaction-graph lint: dead ends, unreachable pages, forms
  without success/error, un-owned APIs, protected pages without login), blackboard for parallel agents,
  clone/adopt/scaffold/compose, swap scan/check, dev runner, rebrand scan/apply/check, verify (12 rows),
  deploy target/ship/smoke over the Coolify client, handoff, ops bots (watchdog, link audit + app-bot
  specs), learn (dh run, from-failure, preflight, promote) with 20 seed lessons, harvest.
- Try-on engine (zero-dependency Node): AST stamp loader (Next Turbopack/webpack, Vite), proxy + overlay,
  catalog ranking (personal library first, base-safe, diverse), fetch with GitHub-source follower +
  cache + fixture replay, materialize, theme normalization, transplant, keep/bake/prune, byte-exact
  discard, save to library, headless CLI, `compose` (a page from blocks + copy).
- Multi-harness installer (`install.sh`, `install.ps1`), `AGENTS.md`, offline CI.
- Compose/try-on content fidelity: CTA-vs-link pairing, copyright line → `© <year> <brand>`, compound
  component roles (`AccordionTrigger`…), lead/body paragraph split, twin card rows as one list, two-tone
  headings, footer/navbar menus from the plan (`lib/sitelinks.mjs`), social rows filtered to the owner's
  networks, design forms hidden unless wired, one `<h1>` per page, design-family coherence, and a
  demo-copy ledger (`.deckhand/demo-copy.json`) that `dh rebrand check` enforces.
- **AI draft fallback for try-on** (`lib/draft.mjs`): when no licensed design fits, or on request from the
  variant bar, the owner asks for an AI-written variant; the agent writes it once from a brief (the owner's
  exact content, note, primitives, packages, rules); gates check content, links, token colours, imports,
  images, side effects; it is labelled AI-generated in the bar, session, file header and keep result; no
  third-party notice is written for it; its own words are recorded `ai: true` (rebrand warns, never blocks).
  `tryon draft / drafts [--wait] / draft-check / draft-done`; serve prints one `draft_request` line.
- **Autopsy v2 — deterministic** (`dh autopsy [transcript | --latest] [--apply]`): reads a Claude Code
  transcript or deckhand's own run log (every `dh` call and `dh run` is logged — any harness); finds failures
  including those a pipe hid, groups retries and recurrences, extracts the recipe that actually fixed each,
  assigns an owner and a fix-ladder rung from evidence; `--apply` writes lessons with recipes (`dh run --fix`
  replays auto-safe ones), skill-fix proposals with repro + regression-test check, and playbooks (`dh next`
  shows twice-confirmed ones as `worked_before`). Never edits the skill; same session → same bytes.
- **Vetting gate** (`data/licenses.json`, one policy): `dh pool vet|add` and `tryon registry vet|add|list|remove`
  refuse copyleft, custom or missing licences, paywalls, paid packages, committed secrets, dead or
  non-runnable repos — with the reasons and what would be accepted. Permissive family accepted (MIT,
  Apache-2.0, BSD-2/3, ISC, 0BSD, Unlicense).
- **Personal boilerplate library on the owner's GitHub**: `dh harvest --push` (secret scan first, private
  repo, `deckhand-library` index + README, "verified + live" badge), `dh pool sync`, `dh clone` from private bases.
- **Tune it + Site** (try-on): deterministic knobs for any element (spacing, headlines, weight, corners,
  depth, contrast, width; presets quieter/bolder/airy/compact/clarity/softer/sharper) and the whole look
  (accent, neutrals, radius, density, headline scale, next/font body + heading fonts) — previewed with the
  exact values applied, reversible byte-exact.
- **`LLM_CONTEXT.md` — the cold-start map for any AI** (`scripts/llm_context.py`, stdlib).
  - One file holds the whole repo for a model with no memory:
    - curated: architecture, every state file, invariants and what enforces them, the flows step by step,
      "to change X edit Y, prove in Z", traps already paid for;
    - generated from the code: every file, dh/tryon command, helper API route with its handler, function with
      its exact line, error code, env var, data shape, doc outline, test and CI step.
  - Curated text points at code through anchors (`[[path#symbol]]`, `[[dh:cmd]]`, `[[!CODE]]`), resolved to
    `symbol@path:line`. A renamed or removed symbol fails the build, so neither half can go stale silently.
  - Kept current automatically: the `.githooks/pre-commit` hook (from the index); CI `--check` on branches and
    PRs; `.github/workflows/llm-context.yml` regenerating `main`.
- **Tune and Site from chat** (`tryon tune`, `tryon theme [--undo]`): the owner says "make the hero airier" or
  "warmer greys, rounder corners" and the agent applies it without a browser. It's the same deterministic,
  byte-exact reversible engine as the overlay.
- `docs/USE-CASES.md`: ten scenarios, each with the sentence to say, what happens, and what you do.
- `dh verify` proves routes on the production build it just made (served on a free port, stopped after).
- Kokonut UI items fall back to the project's GitHub mirror when kokonutui.com is unreachable.
- No-domain preview: `dh deploy smoke` warns on plain http / generated `sslip.io` URLs; HANDOFF.md is
  labelled PREVIEW with the no-logins-over-http rule.

### Verified
- Chromium end-to-end on a real Next 16.3.6 app: pick → 3 hero variants with the owner's copy (4/4) →
  cycle → keep (baked, pruned, licence recorded) → save to library; CTA try → discard byte-exact.
- Scratch compose of a 6-section landing page from live Tailark OSS blocks (~6 s): 34/34 owner words
  placed, footer menu from the plan, typecheck clean; `dh rebrand check` blocked the one leftover demo
  sentence and passed after it was rewritten.
- `next build` after keep: type-check passes; 0 stamped files in the production output.
- AI draft end to end in Chromium: request from the variant bar (with a note) → agent `drafts --wait` →
  draft written → gates passed (4/4, one AI line flagged) → the page switched to the labelled variant beside
  4 licensed ones → keep → type-check clean.
- Tune + Site in Chromium on Next 16: airy 96→144px, bolder 48→60px / 700→800, reset exact; accent, radius,
  Manrope body and Fraunces headings applied after a reload, undo restored both files.
- Autopsy on this project's own 369-command development session: 23 pipe-hidden failures, one trap that
  recurred 3×, the README badge edit that fixed the version check.
- Suites: 38 node (try-on) · 35 unittest (dh) · 40 pytest (ops clients) — green on Ubuntu and Windows CI.

v1 history (the five-skill pack, last release v0.19.0 "try-on grows up"): see the git log up to d079a14.
