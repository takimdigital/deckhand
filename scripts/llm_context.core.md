You are a model with no memory of this repo. This file is the map. Open a source file only to change it, or when a
table here points you at one. Lookup tables are grep-friendly: `^#### tryon/lib/engine.mjs`, `^- NO_CANDIDATES`,
`^- dh pool`. `sym@path:line` means symbol `sym` is defined at that line. Line numbers are exact for the fingerprint
above. After editing code, run `python3 scripts/llm_context.py` again.

## BOOT
WHAT  Deckhand v2 is an agent skill (MIT, repo takimdigital/deckhand-skill; one skill folder [[skills/deckhand/SKILL.md]]).
      It lets an AI agent in any harness (Claude Code, Codex, Cursor, Hermes, OpenCode, Gemini CLI) take a non-technical owner
      from an idea to a live, owned web business: define → research → plan → build → brand → try-on → review → deploy →
      operate. It runs on their own $5 VPS with Coolify, or on a $0 Oracle track.
WHY   Cheap in tokens and verifiable. Scripts do every deterministic step. The model writes only words (copy,
      research, plans) and app-specific logic. Every "done" is a command's output.
HOW   Two engines plus data plus docs:
      - dh — Python 3.9+ stdlib, [[dhlib]] via [[dh.py]]. The control plane: phase state machine, gates, checks,
        build, brand, verify, deploy, learning, reuse. Entry: `python3 skills/deckhand/dh.py <cmd>` (`py` on Windows).
      - tryon — Node 18+, zero deps, [[tryon]]. Live component swap/tune/theme on the owner's running dev site, and
        `compose` for scratch pages. Entry: `node skills/deckhand/tryon/cli.mjs <cmd>`, or `dh tryon <cmd>`.
      - [[data]]: policy and catalogs. [[references]]: one short page per phase, loaded one at a time.
        [[templates]]: files copied into projects. [[ops/scripts]]: Coolify/Hostinger/backup clients, ported from v1 and
        live-proven.
PATHS A path starting with dhlib/ tryon/ data/ references/ templates/ ops/ tests/ dh.py SKILL.md is under skills/deckhand/.
      Every other path is from the repo root (scripts/ docs/ .github/ README.md AGENTS.md …).
      "<project>" = the owner's app folder; "~/.deckhand" = the owner's home state (DECKHAND_HOME overrides).
YOU ARE EITHER
  (a) USING the skill for an owner → run `dh next` and do exactly what it prints: one instruction, one reference to read,
      the lessons that apply. The owner-facing rules are [[skills/deckhand/SKILL.md]] (register, invariants,
      command surface).
  (b) WORKING ON this repo → the DEV section. Tests are offline. Every behaviour change ships with a test. Regenerate this file
      (a stale file fails CI).

## ARCHITECTURE
```
owner ⇄ agent (any harness) ──shell──▶ dh (dhlib/*.py)                        one JSON object per call, exit 0|1|2
                                        │ run state  <project>/.deckhand/run.json   (state machine: phases + gates G1-G4)
                                        │ checks     dhlib/checks.py (a phase is done only when its script passes)
                                        │ subprocess ─▶ node tryon/compose.mjs (dh compose) · node tryon/cli.mjs (dh tryon)
                                        │ subprocess ─▶ git · npm/pnpm/bun/yarn · ops/scripts/coolify_api.py (dh deploy)
                                        ▼
owner's browser ─▶ tryon serve (tryon/server.mjs, 127.0.0.1:3999) ─ reverse proxy + injected overlay.js ─▶ dev server
                    /__dh/api/* (token) ─▶ tryon/lib/engine|draft|tune|sitetheme ─▶ writes the project's source
                    dev server HMR re-renders; the agent is NOT in this loop (0 model calls per click)
registries (https, cached in ~/.deckhand/cache/tryon) ─▶ materialize ─▶ <components>/dh-tryon/<slug>/ (staging)
```
- Contract. dh: [[dhlib/util.py#emit]] prints one JSON object. Failures raise [[dhlib/util.py#DhError]](code, message,
  **extra), and [[dhlib/cli.py#main]] prints {ok:false, code, message, …} with exit 1. Exit 2 = argparse usage.
  tryon: `out()` in [[tryon/cli.mjs]]; failures throw [[tryon/lib/engine.mjs#TryonError]](code, message, extra).
- Project detection. dh: [[dhlib/util.py#project_root]] (--project, else the nearest .deckhand/run.json, else
  package.json). tryon: [[tryon/lib/project.mjs#detectProject]] measures framework (next|vite), aliases, ui/lib dirs,
  package manager, deps, Tailwind major, globals.css, semantic tokens, and the primitive base (radix|base|any).
- Source edits (tryon). Parse with vendored @babel/parser ([[tryon/lib/ast.cjs#parse]]). Every node carries exact offsets,
  so every edit is a string splice on the original bytes. The result is re-parsed before it is written. Every open
  session has a backup, so discard is byte-exact.
- DOM → source. [[tryon/lib/stamp.cjs#stamp]] adds `data-dh="file:line:col"` to every JSX element. This happens only in
  dev, through [[tryon/loader.cjs]] (webpack/Turbopack), [[tryon/vite.mjs]], and the next-config wrapper written by
  [[tryon/lib/setup.mjs#setup]].
- Learning. `dh …` and `dh run -- …` append to <project>/.deckhand/runs.jsonl ([[dhlib/learn.py#log_run]]).
  [[dhlib/autopsy.py#autopsy]] turns that log, or a Claude Code transcript, into lessons/playbooks/proposals.
  `dh next` and `dh run` read them back.

## STATE — every file the skill reads or writes outside its own folder
| path | written by | read by | holds |
|---|---|---|---|
| <project>/.deckhand/run.json | [[dhlib/state.py#save]] | [[dhlib/state.py#load]] | name, mode phased/auto, path pool/mine/existing/scratch, phases{status}, gates{status}, base |
| .deckhand/history.jsonl | [[dhlib/state.py#log]] | humans | init / phase_done / gate / reopen events |
| .deckhand/brief.json | [[dhlib/cli.py#cmd_brief]] | checks, pool.query, brand, sitelinks, harvest | business, shape, languages, audience, brand{name,tagline,primary,logo,social} ([[templates/brief.json]]) |
| .deckhand/research.json | the agent | [[dhlib/checks.py#research]] | 3 competitors with URL, strengths and gaps; audience; conversion plays; features.now ([[templates/research.json]]) |
| .deckhand/sitemap.json | the agent, after [[dhlib/plan.py#init]] | [[dhlib/plan.py#lint]], render, split, sitelinks, verify routes | pages, actions with typed targets, nav, forms, features, entities ([[templates/sitemap.json]]) |
| .deckhand/PLAN.md · work/WP-*.md · blackboard.jsonl | [[dhlib/plan.py#render]] · [[dhlib/plan.py#split]] · [[dhlib/plan.py#bb_post]] | owner · sub-agents | the plan for G1; one work package per bounded context; contract/done/blocker posts |
| .deckhand/copy.json | the agent | [[tryon/compose.mjs]] | section copy (schema in compose.mjs header; footer.columns/social, navbar.links) |
| .deckhand/dev.json · dev.log | [[dhlib/build.py#dev_start]] | checks.build, verify | url, pid, port · the dev server log |
| .deckhand/swap-map.json | [[dhlib/swap.py#scan]] | [[dhlib/swap.py#check]] | vendor SDKs found → owned target |
| .deckhand/demo-copy.json | [[tryon/lib/engine.mjs#recordDemoCopy]] | [[dhlib/brand.py#check]] | demo words a kept design still shows (block), or AI-written words to confirm (ai:true → warn) |
| .deckhand/seo.json · SEO.md · seo-plan.json | [[dhlib/seo.py#audit]] · [[dhlib/seo.py#apply]] | owner, `dh next` (G4 summary), verify row `seo` | score, launch-breakers, findings by rule, owner gaps · the plan handed to the engine |
| PENDING.md "Detected by `dh seo`" block | [[dhlib/seo.py#sync_pending]] (every audit) | owner, [[dhlib/seo.py#pending_summary]] → `dh next` | open owner facts/actions (P-SEO-<key>), first-asked dates kept |
| <project>/lib/seo.ts · app/robots.ts · sitemap.ts · manifest.ts · opengraph-image.tsx · not-found.tsx · components/seo/json-ld.tsx | [[tryon/lib/seo.mjs#seoApply]] (marker `dh:seo`) | the app | business facts + JSON-LD · crawl rules · public routes · share image · real 404 |
| .deckhand/tryon/seo/last.json | [[tryon/lib/seo.mjs#seoApply]] | [[tryon/lib/seo.mjs#seoUndo]] | the files before the last SEO apply (byte-exact undo) |
| .deckhand/verify.json · VERIFY.md | [[dhlib/verify.py#run_verify]] | checks.review, handoff, harvest, [[dhlib/resume.py#check]] | rows {check, ok, blocking, detail}, commit (HEAD it proved) |
| .deckhand/deploy.json | [[dhlib/deploy.py#target]] · ship | checks.deploy, handoff, ops | app_uuid, url, last{commit,result}, smoke |
| .deckhand/RESUME.md (gitignored) | [[dhlib/resume.py#write]] after EVERY dh command ([[dhlib/cli.py#_refresh]]), success or failure | a cold agent (`dh resume`, the SessionStart hook) | where the project stands, rendered from its files by [[dhlib/resume.py#gather]] → [[dhlib/resume.py#render]]: switch verdict, stage, exact next commands, done+proof, gates, in progress, decisions, PENDING, recent; ≤ [[dhlib/resume.py#BUDGET]] chars |
| .deckhand/notes.jsonl (gitignored) | [[dhlib/resume.py#note]] (`dh note decision\|doing\|next`) | [[dhlib/resume.py#gather]], [[dhlib/resume.py#safety_facts]] | {at, ts, kind, text (redacted), phase}: what otherwise lives only in the chat |
| .deckhand/profile.json · vault.env (gitignored; project layer) | [[dhlib/profile.py#set_scope]] (`dh init --for client`) · [[dhlib/profile.py#set_fields]] / [[dhlib/profile.py#vault_set]] (`--here`, or default in a client project) | [[dhlib/profile.py#load]] (machine merged under project) · [[dhlib/profile.py#secret]] | scope me/client + project facts · that project's secrets (a client's keys never leave its project) |
| <project>/AGENTS.md (marked block) · CLAUDE.md (`@AGENTS.md` when new; the same block when the owner has one) | [[dhlib/resume.py#agent_entry]] (dh init, every build path) | any harness at session start | "run `dh resume` first" between `deckhand:begin`/`deckhand:end`; the owner's text is kept |
| ~/.claude/settings.json hooks.SessionStart | [[dhlib/resume.py#install_hook]] (`dh resume --install-hook claude`, `install.sh --claude-hook`) | Claude Code | `dh resume --hook` on startup/resume/clear/compact → [[dhlib/resume.py#hook]] prints the RESUME as context (nothing outside a project) |
| .deckhand/runs.jsonl · failures.jsonl | [[dhlib/learn.py#log_run]] · [[dhlib/learn.py#run_cmd]] | [[dhlib/autopsy.py#load_runs]], [[dhlib/learn.py#from_failure]] | every command {cmd, exit, out} · failed tails |
| .deckhand/lessons.jsonl | [[dhlib/learn.py#add]] (scope=project) | [[dhlib/learn.py#match]] | project-only lessons |
| .deckhand/autopsy/<A-id>.md,.json | [[dhlib/autopsy.py#autopsy]] | owner, `--apply` | the deterministic report |
| .deckhand/tryon/setup.json · runtime/ | [[tryon/lib/setup.mjs#setup]] | [[tryon/lib/setup.mjs#unsetup]], doctor | journal of the config patch (byte-exact undo) · copied loader/plugin |
| .deckhand/tryon/sessions/<id>.json · backups/<id>/ | [[tryon/lib/engine.mjs#open]] | show/keep/discard, checks.tryon, verify | open→kept/discarded, variants[], shaBefore/After · original file bytes |
| .deckhand/tryon/drafts/<D>.json · <D>/draft.tsx | [[tryon/lib/draft.mjs#requestDraft]] · the agent | [[tryon/lib/draft.mjs#checkDraft]], completeDraft | AI draft brief + state pending/rejected/done · the agent's component |
| .deckhand/tryon/tune/<id>.json(+.orig) | [[tryon/lib/tune.mjs#tuneOpen]] | tuneSet/Keep/Reset | dials, original file bytes and sha (FILE_CHANGED guard) |
| .deckhand/tryon/theme/last.json | [[tryon/lib/sitetheme.mjs#themeApply]] | [[tryon/lib/sitetheme.mjs#themeUndo]] | the files before the last Site apply |
| <project>/PENDING.md · HANDOFF.md | [[dhlib/state.py#init]] (from [[templates/PENDING.md]]) · [[dhlib/handoff.py#write]] | owner | facts only the owner holds · access LOCATIONS, commands, pending |
| <project>/NOTICE · THIRD_PARTY_NOTICES.md | [[dhlib/build.py#clone]] · [[tryon/lib/engine.mjs#recordNotice]] | never rewritten | upstream + licence of the base and of every kept design |
| <project>/<components>/sections/ or ui-kit/<slug>/ · dh-tryon/ | keep · open | the app | kept designs · staging (removed on keep/discard/clean) |
| <project>/globals.css marked blocks | [[tryon/lib/theme.mjs#tokenLayer]] (deckhand:tokens) · [[tryon/lib/engine.mjs#open]] (dh:css per variant) · [[tryon/lib/sitetheme.mjs#themeCss]] (dh:theme) | the app | derived tokens · variant CSS · Site knobs |
| ~/.deckhand/profile.json · vault.env (0600) | [[dhlib/profile.py#set_fields]] · [[dhlib/profile.py#vault_set]] | [[dhlib/profile.py#secret]] (env → project vault → machine vault → v1 keyring), [[ops/scripts/coolify_api.py#resolve]] | owner facts · secrets as `NAME='value'` (single-quoted: `set -a; . vault.env; set +a` is safe), never printed |
| ~/.vps-ops/ssh/ · ~/.vps-ops/secrets/*.env.sh (v1 keyring) | the ops runbooks (SSH keys) · v1 | [[dhlib/profile.py#legacy_read]] (fallback), backup scripts | SSH keys for the servers · the backup keyring (backup.env.sh, b2-scoped.env.sh) · v1 tokens still honoured |
| <project>/.gitignore (deckhand block) | [[dhlib/util.py#ensure_gitignore]] (dh init, every build path) | git, verify `logs-ignored` | [[dhlib/util.py#GITIGNORE_LINES]]: runs, failures, *.log, dev.json, autopsy/, tryon/, RESUME.md, notes.jsonl, profile.json, vault.env; an older block is upgraded in place (every RESUME write calls it) |
| ~/.deckhand/pool.json · bases/<name>/ | [[dhlib/pool.py#add_local]] · [[dhlib/harvest.py#harvest]] | [[dhlib/pool.py#rows]] (ranked first) | personal bases (source mine) |
| ~/.deckhand/lessons.jsonl · playbooks.jsonl · autopsy/proposals/E-*.md | [[dhlib/learn.py#add]] · [[dhlib/autopsy.py#apply_report]] | match/preflight · [[dhlib/guide.py#_playbook]] · a human | global lessons (+recipe, auto) · steps that finished a phase ≥2× · skill-fix proposals |
| ~/.deckhand/library/ (components/, components.index.json) | [[tryon/lib/library.mjs#saveToLibrary]] | [[tryon/lib/catalog.mjs#loadCatalog]] (r=mine, ranked first) | the owner's saved components |
| ~/.deckhand/registries.json · catalog/registry-<id>.json | [[tryon/lib/vet.mjs#addRegistry]] | [[tryon/lib/catalog.mjs#loadCatalog]] | vetted extra registries and their mapped items |
| ~/.deckhand/cache/tryon/ | [[tryon/lib/registry.mjs#getText]] | same | fetched registry files (a click never refetches) |
| GitHub <login>/deckhand-base-<name> (private) · <login>/deckhand-library | [[dhlib/harvest.py#harvest]] via [[dhlib/github.py#push]] · [[dhlib/harvest.py#library_upsert]] | [[dhlib/harvest.py#library_sync]], [[dhlib/build.py#clone]] | a harvested base · library.json + README table |

## INVARIANTS — never break these (and what enforces each)
1. Output contract: one JSON object on stdout; exit 0 ok · 1 check failed/refused · 2 usage. Nothing else on stdout
   ([[dhlib/util.py#emit]]; tryon `out`). The exceptions: `tryon serve` streams JSON lines, including
   {"event":"draft_request"}; `dh resume --hook` prints plain text (a harness injects it as context) and never fails.
2. Dependencies: Python stdlib only (3.9+). Node built-ins only (18+). The only vendored code is [[tryon/vendor]]
   (babel parser, MIT). Never use the project's own `typescript` package: TS7 has no JS API (lesson S-008).
3. Deterministic: same inputs → same bytes. This covers ranking ([[tryon/lib/catalog.mjs#rank]], [[dhlib/pool.py#score]]),
   verdicts ([[dhlib/vet.py#verdict]], [[tryon/lib/vet.mjs#vetRegistry]]), autopsy reports, tune/theme transforms and
   this file. No clocks or randomness in outputs, except ids and timestamps in state.
4. Edits are exact and reversible. Every source edit is AST-located, re-parsed before it is written, and backed up.
   Discard, tune reset, theme undo and `tryon clean` restore bytes exactly ([[tryon/lib/engine.mjs#discard]],
   [[tryon/lib/tune.mjs#tuneReset]], [[tryon/lib/sitetheme.mjs#themeUndo]], [[tryon/lib/setup.mjs#unsetup]]).
5. Dev tooling never ships. Stamps load only when NODE_ENV=development. Verify rows `prod-clean` and
   `tryon-closed` block ([[dhlib/verify.py#run_verify]]). `tryon clean` runs before review.
6. Owner facts are never invented. Unknowns go to PENDING.md. Demo copy left in a kept design blocks
   `dh rebrand check`. AI-written words are listed and warn until the owner confirms them
   ([[dhlib/brand.py#check]], [[tryon/lib/engine.mjs#demoTexts]], [[tryon/lib/engine.mjs#literalFit]]).
7. Secrets stay in the vault or env. They never appear on a command line, in a remote URL, stdout, a commit or
   HANDOFF.md. The GitHub token reaches git through GIT_CONFIG_* env ([[dhlib/github.py#git_env]]).
   One policy, [[data/secrets.json]], drives every scanner and the redaction:
   - [[dhlib/util.py#SECRET_RX]] feeds verify, harvest and vet; [[tryon/lib/library.mjs]] is strict.
   - [[dhlib/util.py#redact]] scrubs runs.jsonl, failures.jsonl and `dh run` output ([[dhlib/learn.py#scrub]]), plus
     every autopsy report, lesson and playbook. A recipe with a redacted step is never auto-replayed.
   - `harvest --push` refuses on any secret-shaped file or string ([[dhlib/harvest.py#secret_scan]], [[!SECRETS_IN_BASE]]).
   - Every project gitignores the run logs ([[dhlib/util.py#ensure_gitignore]]); verify blocks when they're not ignored.
   - Layers: [[dhlib/profile.py#use_project]] is set by [[dhlib/cli.py#main]] for every command. A client project
     (scope client) writes settings and secrets to its own gitignored layer by default ([[dhlib/profile.py#_target]]);
     another project never reads it. The RESUME, notes and project vault never leave the machine.
   Helper/CLI inputs are validated before they become CSS, class lists or paths: [[tryon/lib/sitetheme.mjs#cleanTheme]]
   ([[!BAD_THEME]]), [[tryon/lib/tune.mjs#dialsOf]] ([[!BAD_DIAL]]), safe ids ([[!BAD_ID]]).
8. One licence policy ([[data/licenses.json]]) for bases, registries and the catalog. NOTICE and
   THIRD_PARTY_NOTICES.md are never deleted or rewritten ([[dhlib/brand.py#NEVER]]). AI-generated variants carry a
   provenance header and no third-party notice.
9. Nothing enters on trust: `dh pool vet|add` ([[dhlib/vet.py#verdict]]) and `tryon registry vet|add`
   ([[tryon/lib/vet.mjs#vetRegistry]]). A refused item is refused with the reason and what would be accepted
   ([[dhlib/vet.py#acceptable_text]]).
10. Gates are hard in phased mode. [[dhlib/state.py#phase_done]] refuses out of order ([[!OUT_OF_ORDER]]) or behind an
   unpassed gate ([[!GATE_BLOCKED]]). A phase is done only when [[dhlib/checks.py#run]] says ok (or `--force REASON`,
   which is recorded).
11. The autopsy never edits the skill. It writes lessons, playbooks, and proposals for a human or a reviewed PR.
12. The agent is never in the click loop. The overlay calls the local helper; the helper calls the engine. A new
   try-on feature must not require polling the model.
13. Every behaviour change ships with a test. A fix that lives only in prose isn't a fix. After any change,
   regenerate LLM_CONTEXT.md.
14. Windows parity. Use `py`; read files with CRLF normalized; delete trees with [[dhlib/util.py#rmtree]] (read-only
   git objects); resolve launchers with [[dhlib/util.py#which]] (npm.cmd). Line endings follow [[.gitattributes]].
   CI runs Ubuntu and Windows.
15. Nothing lives only in the chat. RESUME.md is regenerated from files after every dh command; it is never a
   model recap. The switch verdict ([[dhlib/resume.py#safe]]) is computed: NO while files changed after the last note
   (dh-managed files excluded: [[dhlib/resume.py#MANAGED]]) or a failure newer than the last note has no known fix.

## FLOWS (→ = then; each step names its code)
F1 RUN LOOP
- `dh init` → [[dhlib/state.py#init]] writes run.json, PENDING.md and the AGENTS.md cold-start block ([[dhlib/resume.py#agent_entry]]).
- `dh next` → [[dhlib/guide.py#next_step]] returns:
  - STEPS[phase], a list of commands ([[dhlib/guide.py#STEPS]]);
  - `read`, the one reference to load;
  - `lessons` from [[dhlib/learn.py#preflight]];
  - `worked_before` from playbooks;
  - `pool_top` during plan.
- Agent works → `dh phase done X` → [[dhlib/checks.py#run]]:
  - red → [[!CHECK_FAILED]] with `why[]`;
  - green → in phased mode a gate may block → owner says go → `dh gate pass Gn`.
- `dh reopen X` resets X and every later phase and gate.
- Phases and their gates: [[dhlib/state.py#PHASES]]. G1 plan, G2 build, G3 tryon, G4 review.

F2 BUILD PATHS (run.json.path)
- pool/mine: `dh pool query` ([[dhlib/pool.py#query]]: [[dhlib/pool.py#score]] = shape +40, features, freshness…;
  blockers exclude) → `dh clone NAME --to DIR` ([[dhlib/build.py#clone]]):
  - licence re-checked;
  - shallow clone at the measured commit, or a private GitHub clone for mine;
  - fresh git history ([[dhlib/build.py#_fresh_git]]);
  - NOTICE written; .env seeded with LOCAL secrets only ([[dhlib/build.py#seed_env]]);
  - base recorded.
- existing: `dh adopt PATH|URL` ([[dhlib/build.py#adopt]]); history kept.
- scratch: `dh scaffold` ([[dhlib/build.py#scaffold]]: create-next-app + [[templates/scaffold]] tokens/cn/Button) →
  `dh compose` (F3).
- Then:
  - `dh swap scan|check` swaps rented vendor SDKs for owned targets ([[dhlib/swap.py#TARGETS]]; payment processors
    are kept);
  - `dh dev start` ([[dhlib/build.py#serve]]: detached process group, waits until the URL answers < 500) → owner
    tests → G2.

F3 COMPOSE (scratch landing page, no codegen)
- [[dhlib/build.py#compose]] → `node tryon/compose.mjs` reads .deckhand/copy.json → for each section:
  1. [[tryon/lib/catalog.mjs#rank]] (with a kit-coherence bonus);
  2. fetch and materialize;
  3. [[tryon/lib/transplant.mjs#parameterize]], then [[tryon/lib/transplant.mjs#bind]] with the copy;
  4. [[tryon/lib/sitelinks.mjs#fillLinks]] for footer/navbar;
  5. [[tryon/lib/engine.mjs#bake]].
- Output: components/sections/<slug>/, and the page imports them in order.
- Rules: one <h1> per page; copy with no room in the design is reported, never dropped silently.

F4 TRY-ON SESSION WIRING
- `tryon setup` ([[tryon/lib/setup.mjs#setup]]):
  - next.config → `withDeckhandTryon(config)` ([[tryon/lib/setup.mjs#patchNextConfig]]);
  - vite → dhTryon() ([[tryon/lib/setup.mjs#patchViteConfig]]);
  - adds the token layer ([[tryon/lib/engine.mjs#ensureTokens]]);
  - journaled.
- Restart dev → `tryon serve` ([[tryon/server.mjs#startServer]]):
  - proxy rewrites Host/Origin to localhost (Next dev guard) and injects the overlay into HTML;
  - HMR websockets are passed through;
  - API gated by the per-run token; writes run one at a time.
- Overlay ([[tryon/overlay.js]]): owner clicks Try-on → picks an element (nearest data-dh stamp, breadcrumb of
  ancestors) → chooses a slot ([[tryon/lib/slots.mjs]]) → tabs "Swap it | Tune it"; a "Site" button sits on the pill.

F5 OPEN (swap) [[tryon/lib/engine.mjs#open]]
1. Find the element at file:line:col.
2. [[tryon/lib/transplant.mjs#extractUnits]] gets the owner's content units: text, links, images, inputs, and
   unrolled .map lists.
3. [[tryon/lib/catalog.mjs#rank]] ranks candidates: mine first; primitive-base mismatch hidden and counted.
4. For each candidate:
   1. [[tryon/lib/materialize.mjs#fetchBundle]]: [[tryon/lib/registry.mjs]] json or gh transport, cached, https only,
      size/file caps.
   2. [[tryon/lib/materialize.mjs#writeBundle]]:
      - every file needed; the project's ui primitives reused; cn from lib/utils;
      - palette classes → tokens ([[tryon/lib/theme.mjs#normalizeClasses]]); compat fixes.
   3. Blocks only:
      - [[tryon/lib/transplant.mjs#parameterize]]: static units → `content.x ?? demo`, demo lists → list slots;
        chrome, demo logos and forms hidden;
      - then [[tryon/lib/sitelinks.mjs#fillLinks]], then [[tryon/lib/transplant.mjs#bind]];
      - fit gate: a candidate carrying < half the owner's units is skipped as POOR_FIT.
5. One batched npm install.
6. Sort by fit.
7. Write ONE wrapper (`data-dh-session`, variant 0 = the original, hidden). Imports are marked `// dh-tryon:<id>`.
   The result is re-parsed; the backup is saved.
8. Cycling ← → is client-side display toggling: zero writes. [[tryon/lib/engine.mjs#show]] persists the choice.
9. Nothing fits → [[!NO_CANDIDATES]] or [[!NO_VARIANTS]] with `draft:{file,line,col,slot}`; the overlay offers an
   AI draft (F7).

F6 KEEP / DISCARD
- [[tryon/lib/engine.mjs#keep]]:
  - the wrapper collapses to the chosen variant under a clean local name;
  - the folder graduates to <components>/sections/ or ui-kit/<slug>;
  - [[tryon/lib/engine.mjs#bake]] writes the literal copy into the component (show/hide switches resolved);
  - losers and their CSS are deleted;
  - THIRD_PARTY_NOTICES entry ([[tryon/lib/engine.mjs#recordNotice]]; not for AI drafts);
  - leftover demo copy → demo-copy.json.
- Keeping variant 0 is a discard.
- [[tryon/lib/engine.mjs#discard]]: backup restore when sha matches, else a surgical unwrap.
- `tryon save` → [[tryon/lib/library.mjs#saveToLibrary]]: refuses without a licence or when a credential-shaped string
  is found.

F7 AI DRAFT (labelled fallback; the agent writes once, scripts gate)
1. Overlay "AI draft", or `tryon draft` → [[tryon/lib/draft.mjs#requestDraft]] writes drafts/<D>.json. The brief holds:
   - content units, markup, hrefs, lists, images, dynamic expressions;
   - the original JSX;
   - the project's ui/utils/packages;
   - the rules and `write_to`.
   `tryon serve` also prints {"event":"draft_request"} on stdout.
2. Agent: `tryon drafts [--wait]` → writes <D>/draft.tsx (default export) → `tryon draft-done --id D`.
3. [[tryon/lib/draft.mjs#checkDraft]] gates:
   - DRAFT_EMPTY, DRAFT_FILE, DRAFT_ENTRY, DRAFT_PARSE, DRAFT_EXPORT;
   - DRAFT_IMPORT: only the project's ui/utils, installed packages, draft-local files;
   - DRAFT_SIDE_EFFECT: no fetch/env;
   - DRAFT_RAW_COLOR: tokens only;
   - DRAFT_IMAGE / DRAFT_LINK: only the owner's;
   - DRAFT_DROPPED_CONTENT: [[tryon/lib/engine.mjs#literalFit]] must carry every owner unit.
4. Gate outcome:
   - rejected → [[!DRAFT_REJECTED]] with problems; state rejected; fix and re-run;
   - passed → [[tryon/lib/draft.mjs#completeDraft]] folds any open session on the same element (discard, reopen
     with [aiItem, ...its registry items]) → engine.open with `candidates`.
5. Every AI variant is labelled everywhere:
   - `generated:true`; purple "AI-generated" badge;
   - file header "AI-generated … no licence notice applies";
   - invented words listed as ai-copy (warn).

F8 TUNE (one element; the Impeccable verbs as deterministic knobs)
- [[tryon/lib/tune.mjs#tuneOpen]] saves the original, then [[tryon/lib/tune.mjs#tuneSet]].
- Each set recomputes from the ORIGINAL: [[tryon/lib/tune.mjs#tuneElement]] → [[tryon/lib/tune.mjs#tuneClassList]] →
  [[tryon/lib/tune.mjs#tuneToken]] over the subtree's class strings. The result is written each time; HMR shows
  exactly what would be kept.
- Knobs: [[tryon/lib/tune.mjs#DIALS]]. Presets: quieter/bolder/airy/compact/clarity/softer/sharper
  ([[tryon/lib/tune.mjs#PRESETS]]).
- Keep = stop tracking. Reset = byte-exact. [[!FILE_CHANGED]] if the file was edited meanwhile.
- From chat, no browser: [[tryon:tune]] `--file F --line N --col C --preset airy` (or `--density 1 …`) →
  `tune --id T --keep|--reset`.

F9 SITE (whole look)
- Knobs ([[tryon/lib/sitetheme.mjs#KNOBS]]): accent ([[tryon/lib/sitetheme.mjs#ACCENTS]] or any hex), neutrals,
  corners, density (Tailwind 4 --spacing), headlines (--text-*), fonts ([[tryon/lib/sitetheme.mjs#FONTS]]).
- Preview: the overlay asks [[api:theme-vars]] for the exact values ([[tryon/lib/sitetheme.mjs#themeVars]]) and sets
  them on :root.
- Apply ([[tryon/lib/sitetheme.mjs#themeApply]]):
  - writes one `dh:theme` block at the end of globals.css ([[tryon/lib/sitetheme.mjs#themeCss]]; unlayered body
    rule, headings in @layer base);
  - fonts: [[tryon/lib/sitetheme.mjs#rewriteFonts]] rewrites next/font in the root layout (AST) and adds
    --font-heading;
  - backs up to theme/last.json.
- Undo is byte-exact.
- From chat, no browser: [[tryon:theme]] (state and allowed values) · `theme --neutrals warm --corners round …` ·
  `theme --undo`.

F10 REVIEW `dh verify` → [[dhlib/verify.py#run_verify]]
- Rows: typecheck · lint (advisory) · build · prod-clean · tryon-closed · secrets · leaks/honesty
  ([[dhlib/brand.py#check]]) · routes · a11y (advisory) · audit (advisory).
- routes: every planned static route plus every internal home-page link must answer < 400, on the production build
  served on a free port 4100+ (falls back to --url or the dev server).
- Writes verify.json and VERIFY.md. Any red blocking row → [[!VERIFY_FAILED]] → G4 can't pass.

F11 DEPLOY
- First time: runbooks [[references/ops/00-user-checklist.md]] → 10/11 (server) → 20/21 (domain) → 30 (app).
- `dh deploy target --app UUID --url U` → `dh deploy ship` ([[dhlib/deploy.py#ship]]):
  1. clean tree required ([[!DIRTY_TREE]]);
  2. git push;
  3. Coolify /deploy;
  4. [[ops/scripts/coolify_api.py#wait_for_deploy]] with expect_commit=HEAD, so a stale deployment can't pass;
  5. [[dhlib/deploy.py#smoke]] (http → NO_TLS warning; sslip/nip → PREVIEW_URL warning).
- `dh handoff` ([[dhlib/handoff.py#write]]).

F12 LEARN
- `dh run -- CMD` ([[dhlib/learn.py#run_cmd]]):
  - failure → [[dhlib/learn.py#match]] against lessons (seed [[data/lessons.seed.jsonl]] + ~/.deckhand + project) →
    prints the known fix;
  - `--fix` replays an `auto` recipe (safe commands only), then retries once.
- `dh autopsy [src|--latest] [--apply]` ([[dhlib/autopsy.py#autopsy]]):
  1. Sources: Claude JSONL ([[dhlib/autopsy.py#load_claude]]), runs.jsonl ([[dhlib/autopsy.py#load_runs]]), plain.
  2. Failure = non-zero exit, or error MARKERS in an executing command's output (pipes hide exits;
     [[dhlib/autopsy.py#is_failure]]). Designed refusals (USAGE, GATE_BLOCKED, OUT_OF_ORDER, DRAFT_REJECTED) are
     not failures.
  3. Episodes are merged by [[dhlib/autopsy.py#signature]]. The recipe = the state-changing steps between the LAST
     failed attempt and the success (verification commands excluded).
  4. Owner ([[dhlib/autopsy.py#_owner]]): skill · environment · project.
  5. Rung ([[dhlib/autopsy.py#_rung]]): eliminate > preflight > reorder > gate > pitfall.
  6. `--apply` ([[dhlib/autopsy.py#apply_report]]): lessons with recipe/auto, skill proposals E-*.md, and playbooks
     that `dh next` shows as `worked_before` (seen ≥ 2).
  7. In a dev session (cwd has skills/deckhand/SKILL.md), everything is owned by the skill and no playbooks are made.

F13 VET
- Bases: `dh pool vet|add owner/repo`:
  - [[dhlib/pool.py#measure]] reads the GitHub API and raw files; no clone, no code run;
  - [[dhlib/vet.py#evidence]] → [[dhlib/vet.py#verdict]];
  - hard criteria: licence, consistent, alive, runnable, clean, free; soft criteria are warnings and ranking
    penalties;
  - add refuses with [[!REFUSED]].
- Registries: `tryon registry vet|add` → [[tryon/lib/vet.mjs#vetRegistry]]:
  - checks: refused-list hosts, the repo licence, shadcn schema, usable items, sampled downloads with no paywall;
  - accepted → [[tryon/lib/vet.mjs#addRegistry]], items mapped by [[tryon/lib/regmap.mjs#mapShadcnItems]].

F14 REUSE
- `dh harvest --name N [--push]` ([[dhlib/harvest.py#harvest]]):
  1. copy tracked files, minus [[dhlib/harvest.py#DROP]];
  2. neutralize the brand to N;
  3. write a manifest (proven by verify and live URL);
  4. register in the personal pool.
- `--push`:
  1. [[dhlib/harvest.py#secret_scan]];
  2. [[dhlib/github.py#ensure_repo]] creates a private <login>/deckhand-base-N;
  3. push to main;
  4. [[dhlib/harvest.py#library_upsert]] updates <login>/deckhand-library (library.json + README table).
- Another machine: `dh pool sync` ([[dhlib/harvest.py#library_sync]]) → `dh clone N` (private clone on the recorded
  branch).
- Components: `tryon save` → ~/.deckhand/library (ranked first).

F15 OPERATE
- `dh ops suggest` ([[dhlib/ops.py#suggest]]: [[data/bots.json]] vs the brief and whether it's deployed) →
  `dh ops add BOT --runner github|cron` ([[dhlib/ops.py#add]]):
  - generic bots are real scripts ([[templates/bots]]: watchdog, link_audit, notify);
  - app bots are a spec plus skeleton the agent completes.
- Change pipeline: [[references/80-operate.md]].

F16 BRAND
- `dh rebrand scan|apply|check` ([[dhlib/brand.py#apply]]): package name, metadata, template names, primary colour
  token, monogram icon.
- check blocks on: template names, demo companies, lorem, example contacts, placeholder images, demo-copy markers,
  third-party logos as social proof.

F17 FOUND ON GOOGLE (SEO)
- Policy: [[data/seo.json]] (rules C/M/T/S/L/O/I/P/E/A, owner facts, owner actions, AI crawlers, schema types).
  By path ([[dhlib/guide.py#_seo_steps]]):
  - scratch and existing: `dh seo apply` in the brand phase;
  - pool and mine: `dh seo audit` + DECISION NEEDED, repeated at G4.
- [[dh:seo]] `apply` ([[dhlib/seo.py#apply]]):
  1. [[dhlib/seo.py#plan]] builds the plan: facts from the brief only ([[dhlib/seo.py#jsonld]]), the plan's public
     pages, the model's words from copy.json seo.pages, an IndexNow key stored in the brief.
  2. `tryon seo apply` → [[tryon/lib/seo.mjs#seoApply]] adds or improves: never replaces an owner file or title;
     removes a root-layout canonical (rule M05 is why); skips 'use client' pages and dynamic routes with a note.
- `audit` ([[dhlib/seo.py#audit]]) combines:
  - source: [[dhlib/seo.py#check_source]] via [[tryon/lib/seo.mjs#seoInspect]];
  - the plan: [[dhlib/seo.py#check_plan]];
  - images: [[dhlib/seo.py#check_images]];
  - rendered pages: [[dhlib/seo.py#check_page]], [[dhlib/seo.py#check_graph]], [[dhlib/seo.py#check_home]],
    [[dhlib/seo.py#check_nap]];
  - the host: [[dhlib/seo.py#check_site]] (live https: redirects, one host, rule M12: placeholder canonicals).
  It then applies the score, [[dhlib/seo.py#sync_pending]] and SEO.md.
- A REMOTE preview (sslip/nip/http) must be noindex (C07); a local production build must not be (C02).
- [[dhlib/verify.py#run_verify]] adds row `seo` on the served build (blocking = launch-breakers only).
- [[dhlib/deploy.py#ship]] → [[dhlib/seo.py#ping]] (IndexNow) on production.

F18 RESUME (any session, any AI)
- Every `dh` command → [[dhlib/cli.py#_refresh]] → [[dhlib/resume.py#write]] (after the command, even when it failed;
  clone/adopt/scaffold also refresh the new project). `resume`/`note` write it themselves and are not logged in runs.jsonl.
- [[dhlib/resume.py#gather]] reads run.json, history, notes, brief/research/sitemap/verify/deploy, SEO + PENDING
  ([[dhlib/seo.py#pending_summary]]), try-on sessions ([[dhlib/resume.py#_sessions]]), git status/log, and
  [[dhlib/guide.py#next_step]] (DH/TRYON shortened to `dh`/`tryon`).
- [[dh:note]] decision|doing|next → notes.jsonl (redacted with the vault values). `doing done` clears doing.
- [[dh:resume]] → {safe_to_switch, why, file, resume, session}; session = the Claude Code log size
  ([[dhlib/resume.py#session_hint]]; > 2 MB → "a fresh session will be sharper").
- `dh resume --check` → [[dhlib/resume.py#check]]: phase checks re-run (define…tryon); G1 vs brief/sitemap mtime;
  dev URL answers (info); verify.commit vs HEAD and files edited after verify; deploy last.commit vs HEAD (info);
  `--online` smoke; open try-on after tryon done. Drift → [[!DRIFT]] exit 1.
- [[dhlib/guide.py#_fresh_session]]: last history event is a gate and the verdict is YES → `dh next` returns
  `fresh_session` (the moment to offer a new session).
- Cold start: `dh init` → [[dhlib/resume.py#agent_entry]]; Claude Code → [[dhlib/resume.py#install_hook]] +
  [[dhlib/resume.py#hook]] (finds the project from the hook's stdin cwd, [[dhlib/resume.py#stdin_if_piped]] never hangs).

## ROUTING — "to change X, edit Y (and prove it in Z)"
| change | edit | prove in |
|---|---|---|
| a phase, its order, gate or reference | [[dhlib/state.py#PHASES]], [[dhlib/checks.py]], [[dhlib/guide.py#STEPS]], references/NN-*.md | [[skills/deckhand/tests/test_dh.py]] |
| what `dh next` prints | [[dhlib/guide.py#next_step]] | test_dh.py |
| a dh command or flag | [[dhlib/cli.py#build_parser]] + [[dhlib/cli.py#dispatch]] + the module; SKILL.md §4 table | test_dh.py |
| plan lint rules (E0–E11, W1–W4) | [[dhlib/plan.py#lint]] | test_dh.py |
| pool ranking / vetting criteria / licence policy | [[dhlib/pool.py#score]] · [[dhlib/vet.py#verdict]] · [[data/licenses.json]] | [[skills/deckhand/tests/test_vet.py]] |
| clone/adopt/scaffold/dev server | [[dhlib/build.py]] | test_dh.py |
| rebrand / honesty findings | [[dhlib/brand.py#check]] | test_dh.py |
| verify rows | [[dhlib/verify.py#run_verify]] | test_dh.py (Verify) |
| deploy / smoke / Coolify client | [[dhlib/deploy.py]] · [[ops/scripts/coolify_api.py]] | [[skills/deckhand/ops/tests/test_coolify_api.py]], test_dh.py (Deploy) |
| server, DNS, backup and storage clients (used by the ops runbooks) | [[ops/scripts/hostinger_api.py]] · [[ops/scripts/coolify_backup_setup.py]] · [[ops/scripts/backup_verify.py]] · [[ops/scripts/b2_setup.py]] · [[ops/scripts/tigris_bucket.py]] · [[ops/scripts/repo_presence.py]] | [[skills/deckhand/ops/tests]] (pytest) |
| lessons, `dh run`, recipes | [[dhlib/learn.py]] · seed [[data/lessons.seed.jsonl]] | test_dh.py, test_autopsy.py |
| autopsy detection / owner / rung | [[dhlib/autopsy.py#is_failure]] · [[dhlib/autopsy.py#_owner]] · [[dhlib/autopsy.py#_rung]] · MARKERS | [[skills/deckhand/tests/test_autopsy.py]] |
| harvest / GitHub library | [[dhlib/harvest.py]] · [[dhlib/github.py]] | [[skills/deckhand/tests/test_library.py]] (mock API) |
| candidate ranking / slots | [[tryon/lib/catalog.mjs#rank]] · [[tryon/lib/slots.mjs]] | [[skills/deckhand/tryon/test/engine.test.mjs]] |
| fetching registry items | [[tryon/lib/registry.mjs]] (fixtures: DH_FIXTURES, record: DH_RECORD) | engine.test.mjs |
| staging files / import rewriting | [[tryon/lib/materialize.mjs]] | engine.test.mjs |
| owner content carried into designs | [[tryon/lib/transplant.mjs]] | [[skills/deckhand/tryon/test/transplant.test.mjs]], sections.test.mjs |
| footer/navbar links from the plan | [[tryon/lib/sitelinks.mjs]] | [[skills/deckhand/tryon/test/sections.test.mjs]] |
| colours → tokens | [[tryon/lib/theme.mjs]] | setup-theme-server.test.mjs |
| open/show/keep/discard/bake | [[tryon/lib/engine.mjs]] | engine.test.mjs, sections.test.mjs |
| AI draft gates | [[tryon/lib/draft.mjs#checkDraft]] | [[skills/deckhand/tryon/test/draft.test.mjs]] |
| Tune knobs / presets | [[tryon/lib/tune.mjs]] (+ overlay tuneUI) | [[skills/deckhand/tryon/test/tune.test.mjs]] |
| Site knobs / fonts | [[tryon/lib/sitetheme.mjs]] (+ overlay sitePanel) | tune.test.mjs |
| overlay UI | [[tryon/overlay.js]] (plain ES5-ish browser JS, no build) | browser e2e (manual, Playwright + Chromium) |
| helper routes / proxy | [[tryon/server.mjs]] | [[skills/deckhand/tryon/test/setup-theme-server.test.mjs]] |
| dev-only wiring (Next/Vite) | [[tryon/lib/setup.mjs]] · [[tryon/lib/stamp.cjs]] · [[tryon/loader.cjs]] · [[tryon/vite.mjs]] | setup-theme-server.test.mjs, stamp.test.mjs |
| registry vetting | [[tryon/lib/vet.mjs]] · [[data/registries.json]] | [[skills/deckhand/tryon/test/vet.test.mjs]] |
| the shipped catalog | [[tryon/catalog-build.mjs]] (maintainer, network) → [[data/components.index.json]] | engine.test.mjs |
| installer | [[install.sh]] · [[install.ps1]] | manual |
| owner-facing docs | [[README.md]] · [[docs/USE-CASES.md]] · [[skills/deckhand/SKILL.md]] | [[scripts/version_check.py]] (versions) |
| secret patterns / redaction / project gitignore | [[data/secrets.json]] · [[dhlib/util.py#redact]] · [[dhlib/util.py#ensure_gitignore]] | [[skills/deckhand/tests/test_security.py]], [[skills/deckhand/tryon/test/hardening.test.mjs]] |
| resume, notes, switch verdict, cold-start entry, hook, project profile/vault layer | [[dhlib/resume.py]] · [[dhlib/profile.py]] · [[dhlib/cli.py#_refresh]] | [[skills/deckhand/tests/test_resume.py]] |
| SEO rules, owner facts, crawler lists | [[data/seo.json]] · [[dhlib/seo.py]] (checks, PENDING block, ping) · [[tryon/lib/seo.mjs]] (writes) | [[skills/deckhand/tests/test_seo.py]], [[skills/deckhand/tryon/test/seo.test.mjs]] |
| docs ↔ commands, README numbers | whatever changed (docs, SKILL.md §4, README) | [[scripts/test_repo_coherence.py]] |
| this file | code (generated part) · [[scripts/llm_context.core.md]] (curated part) · [[scripts/llm_context.py]] | [[scripts/test_llm_context.py]] |

## DEV — working on this repo
- Tests (all offline):
  - `python3 -m unittest discover -s skills/deckhand/tests`
  - `python3 -m pytest skills/deckhand/ops/tests -q`
  - `node --test skills/deckhand/tryon/test/*.test.mjs`
  - `python3 -m unittest discover -s scripts -p 'test_*.py'`
- Registry HTTP comes from [[skills/deckhand/tryon/test/fixtures/registry]] (DH_FIXTURES; re-record with DH_RECORD).
  GitHub is a local mock API plus file:// remotes (DH_GITHUB_API/DH_GITHUB_GIT).
  The fixture site is [[skills/deckhand/tryon/test/fixtures/site]].
- CI: [[.github/workflows/ci.yml]] runs every suite on Ubuntu and Windows (Windows non-blocking), plus the version
  check, plus `llm_context.py --check` off main.
  [[.github/workflows/llm-context.yml]] regenerates this file on main when it drifts.
- Hooks: `git config core.hooksPath .githooks` once per clone. [[.githooks/pre-commit]] then regenerates this file
  from the index on every commit.
- Release: [[RELEASING.md]].
  - [[scripts/version_check.py]]: README badge = SKILL.md version = CHANGELOG top.
  - [[scripts/leak_sweep.py]]: private terms list, refuses to pass without it.
- Style:
  - terse docstrings/headers that state the contract (they are copied into MODULES, so write them for a model);
  - JSON-first outputs; error codes UPPER_SNAKE;
  - one reason per refusal, plus what would be accepted.
- Traps already paid for (do not re-learn them):
  - Killing by pattern (`pkill -f X`, `ps | grep X | xargs kill`) kills your own shell when X is in your command
    line (exit 144). Kill by PID.
  - Regex `(?:\s+.*\n)+` backtracks catastrophically (\s matches \n). Use `[ \t]+`.
  - Python heredoc patch scripts collide with `"""` quoting. Write the patch to a file, then run it.
  - A GITHUB_TOKEN in the env overrides the vault ([[dhlib/profile.py#secret]] reads env first). Tests must pop it.
  - [[dhlib/util.py#DhError]] takes code and message positional-only. Its extra may carry its own `code`
    (a subprocess result). The CLI prints extra first, so ok/code/message always win. `dh run` used to crash here.
  - Env-assignment redaction must stay case-sensitive (`MY_TOKEN=`). Case-insensitive, it ate `api_key=…&ok=1`
    query strings.
  - A bare repo's HEAD may be master. Push and clone explicit branches (main).
  - Empty dirs are not tracked by git (a fixture's public/). [[tryon/lib/engine.mjs#ensurePlaceholder]] creates
    public/.
  - Windows read-only .git objects make shutil.rmtree fail → [[dhlib/util.py#rmtree]].
  - Next dev blocks HMR via a proxy unless Host/Origin = localhost (S-006). Turbopack rules must not use `as` (S-005).
  - create-next-app's `body{font-family:Arial}` beats next/font variables. The dh:theme body rule is unlayered for
    that reason.
  - Next.js metadata is inherited and shallow-merged: a canonical or openGraph.url in the root layout lands on
    every page, and a page-level openGraph replaces the layout's whole object. That's why [[tryon/lib/seo.mjs]] puts
    the canonical per page and the share image in `opengraph-image`.
  - Turbopack refuses a symlinked node_modules pointing outside the project: copy it for a real build test.
  - Live registry/GitHub/Google Fonts calls may be blocked in sandboxes. Prove behaviour with fixtures and say what
    wasn't live-tested.
  - LLM_CONTEXT.md merge conflict → never hand-merge. Run `python3 scripts/llm_context.py` and commit the result.
- Not proven live yet: a full `dh deploy ship` against a real server (the Coolify client itself is live-proven from
  v1), and the $0 Oracle track. Business bots are specs plus skeletons.
