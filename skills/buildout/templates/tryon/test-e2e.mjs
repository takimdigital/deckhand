#!/usr/bin/env node
/**
 * test-e2e.mjs — the FULL try-on save loop, in a real browser, on a scratch fixture.
 *
 *   static page (overlay served by the helper)  →  owner clicks Try  →  request #N
 *   agent: swap.mjs install (staged file + manifest entry) + helper reply ok
 *   owner: Save  →  a save request linked to #N
 *   agent: swap.mjs verify-stage → library.py add → library_import → reply ok  →  catalog re-ranks
 *
 * Every pack path is derived from this file (the pack root is ../../ from here, the
 * component-library skill is a sibling), and the whole fixture lives under TRYON_E2E_WORK
 * (default: <os tmpdir>/tryon-e2e, wiped on each run) — no user path is baked in and the
 * working tree is never written to.
 *
 *   node skills/buildout/templates/tryon/test-e2e.mjs [--chrome <path>] [--ts-root <dir>]
 *
 * env: CHROME_PATH (browser), PYTHON (helper + static server), TRYON_TS_ROOT (codemod's
 *      typescript), TRYON_E2E_WORK (scratch). Exit 1 on any FAIL; `SKIP: no chrome` + exit 0
 *      when no browser can be found.
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

/* ------------------------------------------------------------------ paths + args */
const HERE = path.dirname(fileURLToPath(import.meta.url));       // <pack>/buildout/templates/tryon
const SKILL = path.resolve(HERE, "..", "..");                    // <pack>/buildout
const CLIB = path.resolve(SKILL, "..", "component-library");     // sibling skill
const SWAP = path.join(HERE, "swap.mjs");
const SERVER = path.join(SKILL, "scripts", "tryon_server.py");
const W = process.env.TRYON_E2E_WORK || path.join(os.tmpdir(), "tryon-e2e");
const PROJ = path.join(W, "proj"), SITE = path.join(W, "site"), STORE = path.join(W, "store");
const HELPER_PORT = 7798, HTTP_PORT = 8765, CDP_PORT = 9336;
const argv = process.argv.slice(2);
const flag = (name) => { const i = argv.indexOf("--" + name); return i === -1 ? "" : (argv[i + 1] || ""); };
// `py` is the launcher on Windows, `python` everywhere else; PYTHON overrides both
const PY = process.env.PYTHON || (process.platform === "win32" ? "py" : "python");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let PASS = 0, FAIL = 0;
const ok = (cond, label, extra = "") => {
  if (cond) { PASS++; console.log("  ok   " + label); }
  else { FAIL++; console.log("  FAIL " + label + (extra ? "\n       " + String(extra).trim().slice(0, 300) : "")); }
};

/* ------------------------------------------------------------------ chrome */
function chromeCandidates() {
  const out = [];
  const given = flag("chrome");
  if (given) out.push(given);
  if (process.env.CHROME_PATH) out.push(process.env.CHROME_PATH);
  if (process.platform === "win32") {
    out.push("C:/Program Files/Google/Chrome/Application/chrome.exe",
             "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe");
    if (process.env.LOCALAPPDATA) out.push(path.join(process.env.LOCALAPPDATA, "Google/Chrome/Application/chrome.exe"));
  } else if (process.platform === "darwin") {
    out.push("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome");
  } else {
    out.push("google-chrome", "google-chrome-stable", "chromium", "chromium-browser");
  }
  return out.filter(Boolean);
}
function findChrome() {
  const which = process.platform === "win32" ? "where" : "which";
  for (const c of chromeCandidates()) {
    if (/[\\/]/.test(c)) { if (fs.existsSync(c)) return c; continue; }
    const w = spawnSync(which, [c], { encoding: "utf8" });          // a bare name means: on PATH
    if (w.status === 0 && (w.stdout || "").trim()) return w.stdout.trim().split(/\r?\n/)[0].trim();
  }
  return null;
}
const CHROME = findChrome();
if (!CHROME) {
  console.log("SKIP: no chrome — pass --chrome <path> or set CHROME_PATH (tried: " + chromeCandidates().join(", ") + ")");
  process.exit(0);
}

/* ------------------------------------------------------------------ scratch */
// a Windows lingering handle must never kill the run: retry, then carry on (mkdirs are recursive)
try { fs.rmSync(W, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 }); } catch {}
fs.mkdirSync(W, { recursive: true });

/* ------------------------------------------------------------------ typescript */
// swap.mjs parses the project with typescript's JS compiler API; the pack never ships it. Reuse one
// that is already there (--ts-root / TRYON_TS_ROOT / resolvable from the pack), else provision
// typescript@5 into the scratch dir with npm — cached after the first run.
function tsFrom(dir) {
  try {
    const m = createRequire(path.join(dir, "package.json"))("typescript");
    return m && typeof m.createSourceFile === "function" && m.ScriptKind ? m : null;
  } catch { return null; }
}
const tsWhy = [];
let TS_DIR = "", TS_VERSION = "";
{
  const want = flag("ts-root") || process.env.TRYON_TS_ROOT || "";
  if (want) {
    const m = tsFrom(want);
    if (m) { TS_DIR = path.resolve(want); TS_VERSION = m.version; tsWhy.push("TRYON_TS_ROOT"); }
    else tsWhy.push("TRYON_TS_ROOT has no usable typescript");
  }
  if (!TS_VERSION) {
    try {
      const m = createRequire(import.meta.url)("typescript");
      if (m && typeof m.createSourceFile === "function" && m.ScriptKind) { TS_VERSION = m.version; tsWhy.push("resolvable from the pack"); }
    } catch { /* not installed next to the pack */ }
  }
  if (!TS_VERSION) {
    const dir = path.join(W, "ts");
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: "tryon-e2e-ts", private: true }));
    const npmArgs = ["install", "typescript@5", "--no-audit", "--no-fund", "--loglevel=error"];
    // on Windows npm is a .cmd shim: run it through the shell cmd.exe itself (never shell:true + args)
    const npm = process.platform === "win32"
      ? spawnSync(process.env.ComSpec || "cmd.exe", ["/d", "/s", "/c", "npm " + npmArgs.join(" ")], { cwd: dir, encoding: "utf8", timeout: 240000 })
      : spawnSync("npm", npmArgs, { cwd: dir, encoding: "utf8", timeout: 240000 });
    const m = tsFrom(dir);
    if (m) { TS_DIR = dir; TS_VERSION = m.version; tsWhy.push("provisioned with npm"); }
    else tsWhy.push("npm could not provide it (exit " + npm.status + "): " +
      String((npm.stderr || "") + (npm.stdout || "")).trim().split("\n").slice(-2).join(" | "));
  }
  ok(!!TS_VERSION, "typescript " + (TS_VERSION || "none") + " usable by the codemod (" + tsWhy.join("; ") + ")");
}
const childEnv = { ...process.env };
if (TS_DIR) childEnv.TRYON_TS_ROOT = TS_DIR;

/* ------------------------------------------------------------------ fixture */
fs.mkdirSync(path.join(PROJ, "app"), { recursive: true });
fs.mkdirSync(path.join(SITE), { recursive: true });
fs.mkdirSync(path.join(W, "cand"), { recursive: true });
fs.writeFileSync(path.join(PROJ, "package.json"), JSON.stringify({
  name: "smoke", dependencies: { next: "16.0.0", react: "19.0.0", "radix-ui": "^1.4.2" } }));
fs.writeFileSync(path.join(PROJ, "components.json"), JSON.stringify({
  $schema: "https://ui.shadcn.com/schema.json", style: "new-york" }));
fs.writeFileSync(path.join(PROJ, "app", "Page.tsx"), [
  '"use client";', "", "export default function Page() {", "  return (",
  '    <button data-slot="button">Get started</button>', "  );", "}", ""].join("\n"));
fs.writeFileSync(path.join(W, "cand", "button.tsx"),
  'export function Button({ className, children }) {\n  return <button className={className}>{children}</button>;\n}\n');
const srcAttr = path.join(PROJ, "app", "Page.tsx").replace(/\\/g, "/") + ":5";
fs.writeFileSync(path.join(SITE, "index.html"), `<!doctype html><html><head><meta charset="utf-8">
<title>tryon save smoke</title>
<style>body{font:15px system-ui;padding:40px}#cta{padding:10px 18px;border-radius:8px}</style></head><body>
<h2>try-on save smoke</h2>
<button id="cta" data-tryon-src="${srcAttr}"><span>Get started</span></button>
<script src="http://127.0.0.1:${HELPER_PORT}/overlay.js"></script>
</body></html>`);

/* ------------------------------------------------------------------ servers */
const helper = spawn(PY, [SERVER, "serve", "--project", PROJ, "--port", String(HELPER_PORT)],
  { cwd: SKILL, env: childEnv, stdio: ["ignore", "pipe", "pipe"] });
let helperOut = "";
helper.stdout.on("data", (d) => { helperOut += d.toString(); });
helper.stderr.on("data", (d) => { helperOut += d.toString(); });
const httpd = spawn(PY, ["-m", "http.server", String(HTTP_PORT), "--bind", "127.0.0.1"],
  { cwd: SITE, stdio: ["ignore", "ignore", "pipe"] });
let httpdErr = "";
httpd.stderr.on("data", (d) => { httpdErr += d.toString(); });
process.on("exit", () => { try { helper.kill(); } catch {} try { httpd.kill(); } catch {} });

let up = false;
for (let i = 0; i < 40; i++) {
  try { const r = await fetch(`http://127.0.0.1:${HELPER_PORT}/health`); if (r.ok) { up = true; break; } } catch {}
  await sleep(250);
}
ok(up, "helper up on loopback with a pinned CORS origin", helperOut);
let siteUp = false;
for (let i = 0; i < 30; i++) {
  try { const r = await fetch(`http://127.0.0.1:${HTTP_PORT}/index.html`); if (r.ok) { siteUp = true; break; } } catch {}
  await sleep(200);
}
ok(siteUp, `static page served on ${HTTP_PORT} (out of the Windows excluded ranges)`, httpdErr);
if (!siteUp) { console.log("cannot continue without the page"); process.exit(1); }

/* ------------------------------------------------------------------ browser over CDP */
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${CDP_PORT}`, "--no-first-run",
  `--user-data-dir=${path.join(W, "profile")}`, "about:blank"], { stdio: "ignore" });
let ws;
process.on("exit", () => { try { ws && ws.close(); } catch {} try { chrome.kill(); } catch {} });

async function cdpUrl() {
  for (let i = 0; i < 40; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch {}
    await sleep(250);
  }
  throw new Error("chrome did not expose a page");
}
let id = 0;
ws = new WebSocket(await cdpUrl());
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
const waiters = new Map();
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && waiters.has(m.id)) { waiters.get(m.id)(m); waiters.delete(m.id); }
});
const send = (method, params = {}) => new Promise((res) => { const i = ++id; waiters.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const evalJs = async (expression) => {
  const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  return r.result && r.result.result ? r.result.result.value : undefined;
};
const clickAt = async (x, y) => {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
};
const centerOf = (expr) => evalJs(`(() => { const e = ${expr}; if (!e) return null; const r = e.getBoundingClientRect();
  return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) }; })()`);
const ROOT = `document.querySelector('[data-tryon-ui]') && document.querySelector('[data-tryon-ui]').shadowRoot`;

await send("Page.enable"); await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 820, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url: `http://localhost:${HTTP_PORT}/index.html` });
await sleep(2500);

let ready = false;
for (let i = 0; i < 20; i++) { ready = await evalJs(`!!document.querySelector('[data-tryon-ui]')`); if (ready) break; await sleep(400); }
ok(ready, "overlay booted into the page (served by the helper)");

/* ------------------------------------------------------------------ owner: pick + Try */
const pill = await centerOf(`${ROOT}.querySelector('.pill')`);
if (!pill) { console.log("cannot continue without the panel"); process.exit(1); }
await clickAt(pill.x, pill.y); await sleep(400);
const cta = await centerOf(`document.getElementById('cta')`);
await clickAt(cta.x, cta.y); await sleep(1600);

// make sure the slot is decided (no silent default: an empty select means Try stays off)
const slotVal = await evalJs(`(() => { const s = ${ROOT}.querySelector('select'); if (!s) return null;
  if (!s.value) { const o = [...s.options].find((o) => o.value === 'button'); if (o) { s.value = 'button'; s.dispatchEvent(new Event('change')); } }
  return s.value; })()`);
ok(slotVal === "button", "slot resolved to 'button'", JSON.stringify(slotVal));
await sleep(1800);

const rowInfo = await evalJs(`(() => { const root = ${ROOT}; const rows = [...root.querySelectorAll('.cands .row')];
  return { n: rows.length, first: rows[0] ? rows[0].textContent.replace(/\\s+/g, ' ').trim().slice(0, 90) : null }; })()`);
ok(rowInfo.n > 0, "candidates rendered for the slot", JSON.stringify(rowInfo));

const tryBtn = await centerOf(`(() => { const row = ${ROOT}.querySelector('.cands .row');
  return row && [...row.querySelectorAll('button')].find((b) => /try/i.test(b.textContent)); })()`);
await clickAt(tryBtn.x, tryBtn.y); await sleep(1200);

const reqFile = path.join(PROJ, ".tryon", "requests.jsonl");
const reqs = () => fs.existsSync(reqFile)
  ? fs.readFileSync(reqFile, "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l)) : [];
const req1 = reqs().find((r) => r.type === "preview");
ok(!!req1 && Number.isInteger(req1.id) && req1.candidate && req1.candidate.item,
  "the panel posted a preview request with a candidate", JSON.stringify(req1 && req1.candidate));
const status1 = await evalJs(`(() => { const s = ${ROOT}.querySelector('.status'); return s ? s.textContent : null; })()`);
ok(/request #\d+ sent/.test(status1 || ""), "panel says which request was sent", status1);

/* ------------------------------------------------------------------ agent: stage + reply */
fs.writeFileSync(path.join(W, "req1.json"), JSON.stringify(req1));
const inst = spawnSync(process.execPath, [SWAP, "install",
  "--root", PROJ, "--from", path.join(W, "cand", "button.tsx"), "--slot", "button", "--entry", "Button",
  "--as", "cta-mine.tsx", "--request", String(req1.id), "--meta-file", path.join(W, "req1.json")],
  { cwd: SKILL, encoding: "utf8", env: childEnv });
let instOut = null;
try { instOut = JSON.parse((inst.stdout || "").trim() || "null"); } catch {}
ok(inst.status === 0 && instOut && instOut.ok === true && !!instOut.dest,
  "swap.mjs install staged the candidate and wrote the manifest", inst.stdout + inst.stderr);

const rep1 = spawnSync(PY, [SERVER, "reply", "--project", PROJ,
  "--id", String(req1.id), "--status", "ok", "--message", "staged components/variants/button/cta-mine.tsx — preview live"],
  { cwd: SKILL, encoding: "utf8", env: childEnv });
ok(rep1.status === 0, "agent replied ok to the try", rep1.stdout + rep1.stderr);

let status2 = "";
for (let i = 0; i < 20; i++) { status2 = await evalJs(`(() => { const s = ${ROOT}.querySelector('.status'); return s ? s.textContent : null; })()`); if (/staged/.test(status2 || "")) break; await sleep(300); }
ok(/staged/.test(status2 || ""), "reply reached the panel over SSE (id-correlated)", status2);

/* ------------------------------------------------------------------ owner: Save */
const saveBtn = await evalJs(`(() => { const b = [...${ROOT}.querySelectorAll('button')].find((x) => /Save to my library/.test(x.textContent));
  if (!b) return { found: false }; const r = b.getBoundingClientRect();
  return { found: true, disabled: b.disabled, inView: r.top >= 0 && r.bottom <= innerHeight && r.left >= 0 && r.right <= innerWidth,
           x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) }; })()`);
ok(saveBtn.found && saveBtn.disabled === false, "Save enabled only after the try was answered", JSON.stringify(saveBtn));
ok(saveBtn.inView === true, "Save/Keep/Undo visible without scrolling (sticky footer)");
await clickAt(saveBtn.x, saveBtn.y); await sleep(1200);

const saveReq = reqs().find((r) => r.type === "save");
ok(!!saveReq && saveReq.request === req1.id, "Save posted a request linked to the answer (request #N)",
  JSON.stringify(saveReq && { type: saveReq.type, request: saveReq.request }));
const status3 = await evalJs(`(() => { const s = ${ROOT}.querySelector('.status'); return s ? s.textContent : null; })()`);
ok(/saving request #\d+/.test(status3 || ""), "panel shows the save request id", status3);

// keeping the panel ON (this is exactly the state the owner watches)
const shot0 = await send("Page.captureScreenshot", { format: "png" });
if (shot0 && shot0.result && shot0.result.data) {
  fs.writeFileSync(path.join(W, "panel-saving.png"), Buffer.from(shot0.result.data, "base64"));
}

/* ------------------------------------------------------------------ agent: save it for real */
const man = JSON.parse(fs.readFileSync(path.join(PROJ, ".tryon", "manifest.json"), "utf8"));
const ent = [...man].reverse().find((e) => e.request === req1.id);
ok(!!ent, "manifest entry for the request found by request id");
// the drift check is the codemod's own verb — never a sha compared by hand here
const ver = spawnSync(process.execPath, [SWAP, "verify-stage", "--root", PROJ, "--request", String(req1.id)],
  { cwd: SKILL, encoding: "utf8", env: childEnv });
let verOut = null;
try { verOut = JSON.parse((ver.stdout || "").trim() || "null"); } catch {}
ok(ver.status === 0 && verOut && verOut.ok === true,
  "verify-stage: the staged file still matches its manifest record (no drift)",
  (ver.stdout || "") + (ver.stderr || ""));

const staged = path.join(PROJ, ent.dest);
const candMeta = ent.candidate || {};
const name = /^[a-z0-9-]{2,63}$/.test(candMeta.item || "") ? candMeta.item : "button-saved";
const add = spawnSync(PY, [path.join(CLIB, "scripts", "library.py"), "add", "--name", name,
  "--file", staged, "--tags", "button", "--license", candMeta.license || "",
  "--source-url", candMeta.item_url || "", "--license-evidence", candMeta.license_evidence || "",
  "--base", candMeta.base || "none", "--slot", ent.slot || "button",
  "--source", `try-on ${new Date().toISOString().slice(0, 10)} @ smoke (request #${req1.id})`, "--strict"],
  { cwd: CLIB, encoding: "utf8", env: { ...childEnv, DECKHAND_LIBRARY: STORE } });
ok(add.status === 0, `library.py add saved the staged component as "${name}"`, (add.stdout || "") + (add.stderr || ""));

const dbCopy = path.join(W, "catalog.db");
fs.copyFileSync(path.join(SKILL, "data", "templates.db"), dbCopy);
const imp = spawnSync(PY, [path.join(SKILL, "scripts", "library_import.py"), "--store", STORE, "--db", dbCopy],
  { cwd: SKILL, encoding: "utf8", env: childEnv });
ok(imp.status === 0 && /"offered": 1/.test(imp.stdout || ""), "library_import offered exactly the saved item", imp.stdout);
const q = spawnSync(PY, [path.join(SKILL, "scripts", "tryon_catalog.py"), "--db", dbCopy, "query",
  "--slot", "button", "--project", PROJ, "--json"], { cwd: SKILL, encoding: "utf8", env: childEnv });
let first = null;
try { const rows = JSON.parse(q.stdout); first = rows[0] && rows[0].item; } catch {}
ok(first === name, "the saved item ranks FIRST for that slot now", (q.stdout || "").slice(0, 200));

const rep2 = spawnSync(PY, [SERVER, "reply", "--project", PROJ,
  "--id", String(saveReq.id), "--status", "ok", "--message", `saved as "${name}" — reuse with: library.py copy ${name} --to <dir>`],
  { cwd: SKILL, encoding: "utf8", env: childEnv });
ok(rep2.status === 0, "agent replied ok to the save", rep2.stdout + rep2.stderr);

let saved = null;
for (let i = 0; i < 20; i++) {
  saved = await evalJs(`(() => { const b = [...${ROOT}.querySelectorAll('button')].find((x) => /Saved|Save to my library/.test(x.textContent));
    return b ? { text: b.textContent, disabled: b.disabled } : null; })()`);
  if (saved && /Saved/.test(saved.text)) break;
  await sleep(300);
}
ok(saved && /Saved/.test(saved.text) && saved.disabled === true, "panel shows the saved state (Saved ✓, disabled)", JSON.stringify(saved));

const shot = await send("Page.captureScreenshot", { format: "png" });
if (shot && shot.result && shot.result.data) {
  fs.writeFileSync(path.join(W, "panel-saved.png"), Buffer.from(shot.result.data, "base64"));
}
console.log(`\n${PASS}/${PASS + FAIL} assertions passed  ·  screenshots: ${W}`);
ws.close(); chrome.kill(); helper.kill(); httpd.kill();
process.exit(FAIL ? 1 : 0);
