# 40 — Verify the Product (acceptance pass; local builds included)

Load when: a build is about to be called done — handed to a user, demoed, or marked "finished". Local-only builds are IN scope: "not deployed" never means "not testable".

The other gates verify the BUILD (does it compile, is it coherent, is it accessible). This one verifies the PRODUCT against the client's own acceptance criteria — the phase most first builds skip. Field evidence: a 12-row acceptance harness caught 2 real defects; the client's own walkthrough then caught a third that every technical gate had passed (a builder's instruction rendered as page copy).

## 1. Acceptance → test rows (the contract)

Take the brief's must-haves (or the client's checklist if one exists) and turn EACH into one row with an exact command/probe and an expected result. No row without a command; no "looks fine".

**When a `map/` exists** (`45-map.md`), the rows are GENERATED from it first — every charter → a row with an exact probe; every edge state → a render check (the error state is the one nobody builds); every flow exit → a link check — written in the map's **Given/When/Then** shape — then any brief must-have not already covered gets its own row. Also: every **ADD-tagged map row** (a check the map adds beyond the brief) becomes a row of its own — an ADD row nobody builds and nobody checks is a defect; every required placeholder named in the charters appears in the build or is explicitly disclosed (portrait AND office — one missing placeholder escaped in the field test); and any promised string (a success/thanks line) must be REACHABLE live — position included (see §2). No map → the hand-built path below, exactly as before.

| # | acceptance (client's words) | probe (exact) | expected | observed | PASS/FAIL |
|---|---|---|---|---|---|

Rules: one failing check fails the row (never partial credit); every row keeps its raw output (one log per row); a row nobody can run is a brief defect — fix the brief first.

## 2. Applicability + fallback

The design-audit kit runs on local builds too (`AUDIT_BASE_URL=http://localhost:<port>` + `AUDIT_NO_SERVER=1` — see `30-design-audit.md`). Kit not installed / not applicable → documented fallback probes, all runnable out of the box (the browser subset needs Playwright: `pnpm add -D playwright@1.63.0` once inside `tmp/qa/`, and probe scripts live there too so ESM `import` resolves from the install; everything else is curl-only):

- overflow + tap targets + font size at the **REQUESTED** width(s): a headless-browser/CDP script run explicitly at 320, 360 and 375 px — measure `scrollWidth` against the REQUESTED width, never just the emulated default (a mobile-emulated context normalized away a real 49 px overflow in the field test — the probe false-negatived its own defect). Tap-target scope: every control in the primary journey (buttons, inputs, standalone links) ≥44 px tall; in-sentence links are excluded by definition — state the scope in the row ("buttons are easy to tap" was read three ways by three graders). Body text ≥16 px.
- link crawl: extract hrefs, fetch every local target, fail on non-200.
- route chrome, per route: every fragment `#…` anchor resolves in THAT route's own DOM (a styled 404 with dead `#` links still fails); the page `<title>` is unique per route.
- confirmation + occlusion (the two the field test missed): after submit, the confirmation must be VISIBLE in the viewport at the moment it appears — check its bounding box after the form collapses, not just that the string exists; and nothing required may sit under a fixed/sticky bar — hit-test (`elementFromPoint` at center) every required element (CTAs, the field being typed in, the last lines of the disclaimer) at max scroll AND at focus time.
- the three coherence checks (`10-design-assembly.md` Phase 3).
- placeholder sweep: grep for lorem/TODO/XXX — and read the RENDERED copy wherever a placeholder sits (the placeholder-copy rule in `00-start-from-boilerplate.md` §6 exists because a builder's note shipped as visible text).

One-file fallback skeleton for the viewport probe (needs Playwright available — the audit kit's `node_modules`, or `pnpm add -D playwright@1.63.0` once in `tmp/qa/`):

```js
// tmp/qa/mobile.mjs — usage: node tmp/qa/mobile.mjs http://localhost:3000
import { chromium } from 'playwright';
const [url] = process.argv.slice(2);
const b = await chromium.launch();
const p = await (await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true })).newPage();
await p.goto(url);
console.log(JSON.stringify(await p.evaluate(() => ({
  overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
  smallControls: [...document.querySelectorAll('a,button,input,select,textarea')]
    .map(el => ({ t: el.tagName, h: Math.round(el.getBoundingClientRect().height) }))
    .filter(x => x.h > 0 && x.h < 44),
  bodyFont: getComputedStyle(document.body).fontSize,
}))));
await b.close();
```

## 3. Write paths (the "it looks like it works" killer)

Any form/CTA that stores or sends: submit → the sink gained exactly ONE correct line → kill the server (by PID, prove 0 listeners) → restart → the line is still there. A confirmation screen must not claim more than the sink does ("saved locally" ≠ "we emailed you"); when delivery is deferred, say so in the copy AND record the production destination in `PENDING.md`. An "intentionally local" deliverable is graded on the sink — never declared untestable.

## 4. Server lifecycle on Windows (kill-by-PID)

`taskkill` under MSYS mangles flags and MSYS `kill` cannot signal a native node process — both can "succeed" while the listener keeps serving the OLD build. Use the Windows API: `py -c "import os,sys; os.kill(int(sys.argv[1]),9)" <pid>`. **Get the PID from the LISTENER at kill time** — `netstat -ano | grep :<port> | grep LISTENING` and take the last column; never trust a stored PID file (it goes stale: the field test's stored PID belonged to a dead parent while a child held the port). Then the rule: **if the listener count did not change, your kill did not happen — your proof is void.** (Confirmed live: a "restart" that never restarted, proved by `netstat` still counting the old PID.) Compare `netstat -ano | grep LISTENING` before/after, then restart and run the freshness check (`verify-ladder.md`).

## 5. The acceptance → state matrix

For every interactive element, enumerate its states and make sure each is RENDERED once before handoff: empty · loading · success · error/offline. The error state is the one nobody builds: trigger it (stop the API / send garbage) and read what the person sees — the client's sharpest question is always some form of "if it fails, what does the person see?"

**Confirmation visibility + occlusion (field-test rule):** a success confirmation must be visible in the viewport at the moment it appears — after the form collapses, compute the confirmation's rect against the viewport (the field test's confirmation rendered −44 to −264 px off-screen depending on where the Send button sat; string-presence probes passed it, the client did not). And nothing required may sit under a fixed/sticky bar: `elementFromPoint` at each required element's centre must hit that element (or its descendant) — the field test's own Send button was under the Call bar.

## 6. The pass goes in the handoff

- The PASS/FAIL table + counts, with raw log paths.
- Every open item into `PENDING.md` (production delivery, real photos, credentials) — already there if the project-pending rule was followed.
- A one-line honest caveat wherever something could only be static-checked (e.g. visual judgement without a real device).
- Evidence rules: mask only secrets — never digit-mask your own probe output; when a required tool is absent (no browser installed), say "cannot check — method unavailable" rather than a silent gap; a count you cannot reproduce is logged as non-reproducible, never smoothed into a clean number.

Field-validated source: this ref generalizes the 12-row acceptance harness + client try-out hand-built around a six-role field test (solo-professional marketing site, local-only): QA read 10/12, the client's own walkthrough 11/12 — every miss filed with an exact repro.
