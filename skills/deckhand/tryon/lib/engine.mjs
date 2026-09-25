/**
 * engine.mjs — one try-on session, end to end, with no LLM in the loop.
 *
 *   open()    click target (file:line:col) -> N ranked, fetched, themed, content-transplanted
 *             variants written ONCE into the source inside a wrapper; HMR renders them; cycling
 *             is client-side (display toggles) so browsing variants costs zero writes.
 *   show()    persist which variant is visible (headless agents / reloads).
 *   keep()    the wrapper collapses to the chosen variant; literal copy is baked into the
 *             component; its folder graduates to components/sections|ui-kit; losers are deleted.
 *   discard() byte-exact restore (or a surgical unwrap if the file changed since).
 * State: <project>/.deckhand/tryon/{sessions/*.json,backups/} — the journal is the truth.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { detectProject, specFor } from './project.mjs';
import { loadCatalog, rank, SKILL_DIR } from './catalog.mjs';
import { fetchBundle, writeBundle, pascal, slugOf, entryExport } from './materialize.mjs';
import { extractUnits, parameterize, bind, contentProp, shapeOf, contentCount } from './transplant.mjs';
import { itemCss, tokenLayer } from './theme.mjs';
import { kindOf } from './slots.mjs';
import { siteLinks, fillLinks, linkTexts, FORM_SLOTS } from './sitelinks.mjs';

const require = createRequire(import.meta.url);
const { parse, walk, jsxName, findElementAt, attr, lineCol } = require('./ast.cjs');

export class TryonError extends Error {
  constructor(code, message, extra = {}) { super(message); this.code = code; Object.assign(this, extra); }
}

const PLACEHOLDER_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000"><rect width="1600" height="1000" fill="#e7e5e4"/><path d="M700 600l120-150 90 110 60-70 130 160z" fill="#a8a29e"/><circle cx="930" cy="400" r="40" fill="#a8a29e"/><text x="800" y="720" text-anchor="middle" font-family="system-ui,sans-serif" font-size="36" fill="#78716c">your image</text></svg>\n';
export const PLACEHOLDER = '/deckhand-placeholder.svg';

/** A neutral image placeholder in public/ (a registry's demo screenshot is never shown as the owner's). */
export function ensurePlaceholder(prof) {
  const pub = path.join(prof.root, 'public');
  // Next and Vite serve public/ at the site root by default — a fresh app may simply not have one yet
  if (!fs.existsSync(pub)) {
    if (!['next', 'vite'].includes(prof.framework)) return false;
    fs.mkdirSync(pub, { recursive: true });
  }
  const p = path.join(pub, 'deckhand-placeholder.svg');
  if (!fs.existsSync(p)) fs.writeFileSync(p, PLACEHOLDER_SVG);
  return true;
}
const sha = (buf) => crypto.createHash('sha256').update(buf).digest('hex');
const now = () => new Date().toISOString();

export function stateDir(root) { return path.join(root, '.deckhand', 'tryon'); }
function sessionsDir(root) { return path.join(stateDir(root), 'sessions'); }
export function loadSession(root, id) {
  if (!/^[A-Za-z0-9_-]{1,40}$/.test(String(id))) throw new TryonError('BAD_ID', 'bad session id');
  const p = path.join(sessionsDir(root), id + '.json');
  if (!fs.existsSync(p)) throw new TryonError('NO_SESSION', 'no try-on session ' + id);
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}
function saveSession(root, s) {
  fs.mkdirSync(sessionsDir(root), { recursive: true });
  fs.writeFileSync(path.join(sessionsDir(root), s.id + '.json'), JSON.stringify(s, null, 2));
}
export function listSessions(root) {
  const d = sessionsDir(root);
  if (!fs.existsSync(d)) return [];
  return fs.readdirSync(d).filter((f) => f.endsWith('.json')).map((f) => JSON.parse(fs.readFileSync(path.join(d, f), 'utf8')))
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}
function newId(root) {
  const n = listSessions(root).length + 1;
  return 's' + n + crypto.randomBytes(2).toString('hex');
}

function identifiers(code) { return new Set(code.match(/[A-Za-z_$][\w$]*/g) || []); }
function uniqueName(base, taken) {
  let n = base, i = 2;
  while (taken.has(n)) n = base + i++;
  taken.add(n);
  return n;
}

function importInsertPos(ast, code) {
  let last = null;
  for (const st of ast.program.body) if (st.type === 'ImportDeclaration') last = st;
  if (last) return code.indexOf('\n', last.end) === -1 ? code.length : code.indexOf('\n', last.end) + 1;
  // after directives ("use client")
  let pos = 0;
  for (const d of ast.program.directives || []) pos = code.indexOf('\n', d.end) + 1;
  return pos;
}

function indentAt(code, offset) {
  const ls = code.lastIndexOf('\n', offset - 1) + 1;
  return (/^[ \t]*/.exec(code.slice(ls, offset)) || [''])[0];
}

/** Find the wrapper JSXElement for a session in the current text. */
function findWrapper(ast, id) {
  let hit = null;
  walk(ast, (n) => {
    if (hit) return false;
    if (n.type === 'JSXElement') {
      const a = attr(n, 'data-dh-session');
      if (a && a.value && a.value.type === 'StringLiteral' && a.value.value === id) { hit = n; return false; }
    }
    return true;
  });
  return hit;
}
function variantChildren(wrapper) {
  return (wrapper.children || []).filter((c) => c.type === 'JSXElement' && attr(c, 'data-dh-variant'));
}
function innerSrc(code, el) {
  const kids = el.children || [];
  const s = kids.length ? code.slice(kids[0].start, kids[kids.length - 1].end) : '';
  return s.trim();
}

/** A primitive swap keeps the usage's props/children; `asChild` + single child is unwrapped. */
function primitiveUsage(code, el, local, candCode) {
  const op = el.openingElement;
  const kids = (el.children || []).filter((c) => !(c.type === 'JSXText' && !c.value.trim()));
  const keepAttr = (a) => {
    if (a.type !== 'JSXAttribute') return true;
    const n = a.name.name;
    if (n === 'asChild') return false;
    if ((n === 'variant' || n === 'size') && !new RegExp('\\b' + n + '\\b').test(candCode)) return false;
    return true;
  };
  const attrs = op.attributes.filter(keepAttr).map((a) => code.slice(a.start, a.end)).join(' ');
  const asChild = op.attributes.some((a) => a.type === 'JSXAttribute' && a.name.name === 'asChild');
  if (asChild && kids.length === 1 && kids[0].type === 'JSXElement') {
    const child = kids[0];
    const cop = child.openingElement;
    const cname = jsxName(cop.name);
    const cattrs = cop.attributes.map((a) => code.slice(a.start, a.end)).join(' ');
    const inner = innerSrc(code, child);
    return `<${cname}${cattrs ? ' ' + cattrs : ''}><${local}${attrs ? ' ' + attrs : ''}>${inner}</${local}></${cname}>`;
  }
  const inner = innerSrc(code, el);
  return inner ? `<${local}${attrs ? ' ' + attrs : ''}>${inner}</${local}>` : `<${local}${attrs ? ' ' + attrs : ''} />`;
}

export function install(prof, pkgs, log) {
  if (!pkgs.length) return { ok: true };
  const cmd = { pnpm: ['pnpm', 'add'], yarn: ['yarn', 'add'], bun: ['bun', 'add'], npm: ['npm', 'install', '--no-audit', '--no-fund'] }[prof.pm] || ['npm', 'install'];
  log && log({ phase: 'install', pkgs });
  const r = spawnSync(cmd[0], [...cmd.slice(1), ...pkgs], { cwd: prof.root, encoding: 'utf8', shell: process.platform === 'win32', timeout: 300000 });
  return { ok: r.status === 0, cmd: cmd.concat(pkgs).join(' '), out: ((r.stdout || '') + (r.stderr || '')).split('\n').slice(-8).join('\n') };
}

/** The owner's brand name: brief first, then package.json. */
export function brandName(root) {
  try { const b = JSON.parse(fs.readFileSync(path.join(root, '.deckhand', 'brief.json'), 'utf8')); if (b.brand?.name || b.name) return b.brand?.name || b.name; } catch { /* none */ }
  try { const n = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8')).name; return n ? n.replace(/[-_]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : null; } catch { return null; }
}

/** Ensure the semantic token layer exists (idempotent; recorded for `clean`). */
export function ensureTokens(prof, probe = {}) {
  if (!prof.globalsCss || prof.tailwind !== 4) return { changed: false, reason: prof.tailwind === 4 ? 'NO_GLOBALS_CSS' : 'TAILWIND_' + prof.tailwind };
  const p = path.join(prof.root, prof.globalsCss);
  const css = fs.readFileSync(p, 'utf8');
  if (css.includes('deckhand:tokens')) return { changed: false, reason: 'PRESENT' };
  const layer = tokenLayer(css, probe);
  if (!layer) return { changed: false, reason: 'COMPLETE' };
  fs.writeFileSync(p, css + (css.endsWith('\n') ? '' : '\n') + layer);
  return { changed: true, file: prof.globalsCss };
}

function appendCss(prof, block) {
  if (!block || !prof.globalsCss) return false;
  const p = path.join(prof.root, prof.globalsCss);
  const css = fs.readFileSync(p, 'utf8');
  const tag = /dh:css ([^ ]+) \*\//.exec(block)[1];
  if (css.includes(`/* dh:css ${tag} */`)) return false;
  fs.writeFileSync(p, css + (css.endsWith('\n') ? '' : '\n') + '\n' + block);
  return true;
}
function removeCss(prof, tag) {
  if (!prof.globalsCss) return;
  const p = path.join(prof.root, prof.globalsCss);
  const css = fs.readFileSync(p, 'utf8');
  const a = css.indexOf(`/* dh:css ${tag} */`);
  if (a === -1) return;
  const endTag = `/* /dh:css ${tag} */`;
  const b = css.indexOf(endTag, a);
  if (b === -1) return;
  const start = css.slice(a - 1, a) === '\n' ? a - 1 : a;       // the blank separator appendCss added
  fs.writeFileSync(p, css.slice(0, start) + css.slice(b + endTag.length).replace(/^\n/, ''));
}

/**
 * Open a session. opts: { file, line, col, slot, count=4, exclude=[], registry, stripChrome, install=true,
 *   probe, onProgress }
 */
export async function open(rootIn, opts) {
  const prof = detectProject(rootIn);
  const root = prof.root;
  const log = opts.onProgress || (() => {});
  const rel = String(opts.file).replace(/\\/g, '/');
  const abs = path.resolve(root, rel);
  if (!abs.startsWith(root + path.sep)) throw new TryonError('OUTSIDE_PROJECT', rel + ' is outside the project');
  if (/(^|\/)(node_modules|\.next|dist|build)\//.test(rel)) throw new TryonError('GENERATED_FILE', rel + ' is generated/vendored — pick the element in your source');
  if (/(^|\/)dh-tryon\//.test(rel)) throw new TryonError('INSIDE_VARIANT', 'that element belongs to a variant being tried — keep or discard it first');
  const before = fs.readFileSync(abs);
  const code = before.toString('utf8');
  const ast = parse(rel, code);
  const el = findElementAt(ast, code, Number(opts.line), Number(opts.col));
  if (!el) throw new TryonError('ELEMENT_NOT_FOUND', `no JSX element starts at ${rel}:${opts.line}:${opts.col} (file changed? reload the page)`);
  const slot = String(opts.slot || '').trim();
  if (!slot) throw new TryonError('NO_SLOT', 'say what this element is (hero, pricing, button…)');
  const kind = kindOf(slot);
  const count = Math.max(1, Math.min(8, Number(opts.count || 4)));

  const orig = extractUnits(code, el, ast);
  const origShape = shapeOf(orig);
  const origCount = contentCount(orig);
  const catalog = loadCatalog();
  // opts.candidates: an explicit list (an AI draft, alone or beside the registry variants it joins)
  const ranked = opts.candidates ? { items: opts.candidates, hidden: 0 } : rank(catalog, { slot, prof, exclude: opts.exclude || [], registry: opts.registry || null });
  if (!ranked.items.length) {
    throw new TryonError('NO_CANDIDATES', `no licensed ${slot} candidates for a ${prof.base} project` + (ranked.hidden ? ` (${ranked.hidden} hidden: other primitive base)` : ''),
      { draft: { file: rel, line: Number(opts.line), col: Number(opts.col), slot } });
  }

  if (kind === 'block' || opts.tokens !== false) {
    const t = ensureTokens(prof, opts.probe || {});
    if (t.changed) log({ phase: 'tokens', file: t.file });
  }

  const hasPublic = ensurePlaceholder(prof);
  const id = newId(root);
  const taken = identifiers(code);
  const variants = [];
  const skipped = [];
  const stripChrome = opts.stripChrome ?? (slot !== 'navbar');
  const links = ['footer', 'navbar'].includes(slot) ? siteLinks(root) : null;
  // a variant folder another open session is showing is never re-staged (it would be wiped)
  const busy = new Set(listSessions(root).filter((o) => o.state === 'open').flatMap((o) => o.variants.map((v) => v.slug)));
  for (const cand of ranked.items) {
    if (variants.length >= count) break;
    if (skipped.length > count * 3) break;
    if (busy.has(slugOf(cand))) continue;
    log({ phase: 'fetch', id: cand.id });
    let stage;
    try {
      const bundle = await fetchBundle(detectProject(root), cand);
      stage = writeBundle(detectProject(root), cand, bundle);
    } catch (e) { skipped.push({ id: cand.id, why: e.code || 'FETCH', detail: String(e.message).slice(0, 200) }); continue; }
    if (stage.problems.length || !stage.export) {
      skipped.push({ id: cand.id, why: stage.export ? 'UNRESOLVED_IMPORT' : 'NO_EXPORT', detail: stage.problems.join('; ') });
      fs.rmSync(path.join(root, stage.relDir), { recursive: true, force: true });
      continue;
    }
    let fit = { carried: [], dropped: [], demo: [], hidden: [] };
    let usage;
    const local = uniqueName('Dh' + pascal(cand.n).slice(0, 40), taken);
    const entryAbs = path.join(root, stage.entry);
    const entryCode = fs.readFileSync(entryAbs, 'utf8');
    if (cand.ai) {
      // an AI draft already holds the owner's words (its gate proved it): measured, never transplanted
      const lf = literalFit(root, stage.relDir, orig, cand.dynamic || []);
      fit = { carried: lf.carried, dropped: lf.dropped, demo: lf.invented.map((t) => ({ text: 'AI-written: ' + t })), hidden: [], demoVisual: lf.invented.length };
      const props = (cand.dynamic || []).map((d) => [d.key, `<>${d.src}</>`]);
      usage = kind === 'block' ? `<${local}${contentProp('content', props)} />` : primitiveUsage(code, el, local, entryCode);
      stage.prop = props.length ? 'content' : null;
      stage.ownerTexts = orig.units.map((x) => x.text).concat(orig.lists.flatMap((l) => l.items.flatMap((it) => it.units.map((u) => u.text).concat(it.bullets || []))));
    } else if (kind === 'block') {
      const logoLocals = logoLocalsFor(stage, entryCode, slot);
      let p;
      try { p = parameterize(stage.entry, entryCode, stage.export, { stripChrome, logoLocals, forms: FORM_SLOTS.has(slot) || orig.inputs.length ? 'keep' : 'hide' }); } catch (e) {
        skipped.push({ id: cand.id, why: 'PARAMETERIZE_FAILED', detail: e.message.slice(0, 200) });
        fs.rmSync(path.join(root, stage.relDir), { recursive: true, force: true });
        continue;
      }
      // a footer/navbar shows the owner's routes (plan sitemap), never the design's demo menu
      const fl = fillLinks(stage.entry, p.code, links, slot);
      fs.writeFileSync(entryAbs, fl.code);
      const b = bind(orig, p, { placeholder: hasPublic ? PLACEHOLDER : null, brand: brandName(root) });
      if (fl.filled.length) b.hidden.push(...fl.filled.map((f) => `${f.array}: ${f.kind} from your plan (${f.count})`));
      // fit gate: a variant that would throw away most of the owner's words is not offered
      if (origCount >= 2 && b.carried.length < Math.ceil(origCount / 2) && !opts.noFitGate) {
        skipped.push({ id: cand.id, why: 'POOR_FIT', detail: `carries ${b.carried.length}/${origCount}` });
        fs.rmSync(path.join(root, stage.relDir), { recursive: true, force: true });
        continue;
      }
      fit = b;
      fit.demoVisual = demoTexts(root, stage.relDir, []).length;
      stage.ownerTexts = orig.units.map((x) => x.text).concat(orig.lists.flatMap((l) => l.items.flatMap((it) => it.units.map((u) => u.text))), linkTexts(links));
      usage = `<${local}${contentProp(p.prop, b.props)} />`;
      stage.prop = p.prop;
      stage.removedChrome = p.removed;
    } else {
      usage = primitiveUsage(code, el, local, entryCode);
    }
    variants.push({
      idx: variants.length + 1, id: cand.id, r: cand.r, n: cand.n, t: cand.t, lic: cand.lic || 'MIT', slot: cand.slot, generated: !!cand.ai, draft: cand.draft || null,
      slug: stage.slug, dir: stage.relDir, entry: stage.entry, spec: stage.spec, export: stage.export, local, usage,
      deps: stage.deps, missingDeps: stage.missingDeps, sourceUrl: stage.sourceUrl, prop: stage.prop || null,
      css: itemCss({ css: stage.css, cssVars: stage.cssVars }, id + '-' + stage.slug) || null,
      fit: { carried: fit.carried.length, of: origCount, dropped: fit.dropped, demo: fit.demo.map((d) => d.text).slice(0, 6), hidden: fit.hidden || [], demoVisual: fit.demoVisual || 0 },
      ownerTexts: stage.ownerTexts || [],
      removedChrome: stage.removedChrome || [],
    });
  }
  if (!variants.length) throw new TryonError('NO_VARIANTS', 'no candidate could be staged', { skipped, draft: { file: rel, line: Number(opts.line), col: Number(opts.col), slot } });

  // one batched install for everything the batch needs
  const need = [...new Set(variants.flatMap((v) => v.missingDeps))];
  let installed = [];
  if (need.length) {
    if (opts.install === false) {
      for (const v of [...variants]) if (v.missingDeps.length) {
        skipped.push({ id: v.id, why: 'NEEDS_DEPS', detail: v.missingDeps.join(', ') });
        fs.rmSync(path.join(root, v.dir), { recursive: true, force: true });
        variants.splice(variants.indexOf(v), 1);
      }
      if (!variants.length) throw new TryonError('NO_VARIANTS', 'every candidate needs npm packages; re-run with install', { skipped });
    } else {
      const r = install(prof, need, log);
      if (!r.ok) throw new TryonError('INSTALL_FAILED', r.cmd + '\n' + r.out, { skipped });
      installed = need;
    }
  }
  // best fit first: most of the owner's content, then the least leftover demo copy (rank breaks ties)
  variants.sort((a, b) => (b.fit.of ? b.fit.carried / b.fit.of : 0) - (a.fit.of ? a.fit.carried / a.fit.of : 0) || a.fit.demoVisual - b.fit.demoVisual);
  variants.forEach((v, i) => { v.idx = i + 1; });
  for (const v of variants) if (v.css) appendCss(prof, v.css);

  // write the wrapper — ONE edit, re-parsed before it touches disk
  const ind = indentAt(code, el.start);
  const keyA = attr(el, 'key');
  const keySrc = keyA ? ' ' + code.slice(keyA.start, keyA.end) : '';
  const origSrc = code.slice(el.start, el.end);
  const lines = [`<div data-dh-session="${id}"${keySrc} style={{ display: "contents" }}>`,
    `${ind}  <div data-dh-variant="0" data-dh-label="Original" style={{ display: "none" }}>`,
    `${ind}    ${origSrc}`,
    `${ind}  </div>`];
  for (const v of variants) {
    lines.push(`${ind}  <div data-dh-variant="${v.idx}" data-dh-label=${JSON.stringify(v.t)} style={{ display: "${v.idx === 1 ? 'contents' : 'none'}" }}>`,
      `${ind}    ${v.usage}`, `${ind}  </div>`);
  }
  lines.push(`${ind}</div>`);
  let next = code.slice(0, el.start) + lines.join('\n') + code.slice(el.end);
  const imports = variants.map((v) => (v.export.kind === 'default'
    ? `import ${v.local} from ${JSON.stringify(v.spec)} // dh-tryon:${id}\n`
    : `import { ${v.export.name} as ${v.local} } from ${JSON.stringify(v.spec)} // dh-tryon:${id}\n`)).join('');
  const at = importInsertPos(parse(rel, next), next);
  next = next.slice(0, at) + imports + next.slice(at);
  parse(rel, next);                                              // throws PARSE_FAILED: nothing written

  const bdir = path.join(stateDir(root), 'backups', id);
  fs.mkdirSync(bdir, { recursive: true });
  fs.writeFileSync(path.join(bdir, path.basename(rel) + '.orig'), before);
  fs.writeFileSync(abs, next);
  const session = {
    id, createdAt: now(), state: 'open', file: rel, line: Number(opts.line), col: Number(opts.col), slot, kind,
    shaBefore: sha(before), shaAfter: sha(Buffer.from(next)), backup: path.relative(root, path.join(bdir, path.basename(rel) + '.orig')).split(path.sep).join('/'),
    shown: 1, origShape, variants, skipped, installed, hidden: ranked.hidden,
    tried: (opts.exclude || []).concat(variants.map((v) => v.id)),
  };
  saveSession(root, session);
  return publicSession(session);
}

export function publicSession(s) {
  return {
    id: s.id, state: s.state, file: s.file, line: s.line, slot: s.slot, shown: s.shown, hidden: s.hidden,
    variants: [{ idx: 0, t: 'Original', r: 'yours' }].concat(s.variants.map((v) => ({
      idx: v.idx, id: v.id, t: v.t, r: v.r, lic: v.lic, fit: v.fit, deps: v.deps, source: v.sourceUrl, removedChrome: v.removedChrome, generated: !!v.generated,
    }))),
    skipped: s.skipped, installed: s.installed,
  };
}

/** Local names the entry imports from brand-logo files — hidden unless the slot IS a logo cloud. */
export function logoLocalsFor(stage, entryCode, slot) {
  const out = [];
  if (slot === 'logo-cloud' || !stage.logoFiles || !stage.logoFiles.length) return out;
  for (const st of parse(stage.entry, entryCode).program.body) {
    if (st.type !== 'ImportDeclaration') continue;
    const base = path.posix.basename(st.source.value);
    if (stage.logoFiles.some((f) => f.replace(/\.(tsx|ts|jsx|js)$/, '') === base)) for (const sp of st.specifiers) out.push(sp.local.name);
  }
  return out;
}

/** Make variant `idx` the visible one in source (headless / persistence). */
export function show(rootIn, id, idx) {
  const root = path.resolve(rootIn);
  const s = loadSession(root, id);
  if (s.state !== 'open') throw new TryonError('SESSION_CLOSED', `session ${id} is ${s.state}`);
  const abs = path.join(root, s.file);
  const code = fs.readFileSync(abs, 'utf8');
  const ast = parse(s.file, code);
  const w = findWrapper(ast, id);
  if (!w) throw new TryonError('WRAPPER_MISSING', 'the variant wrapper is gone from ' + s.file);
  const edits = [];
  for (const v of variantChildren(w)) {
    const i = Number(attr(v, 'data-dh-variant').value.value);
    const st = attr(v, 'style');
    if (st) edits.push({ start: st.start, end: st.end, text: `style={{ display: "${i === Number(idx) ? 'contents' : 'none'}" }}` });
  }
  edits.sort((a, b) => b.start - a.start);
  let out = code;
  for (const e of edits) out = out.slice(0, e.start) + e.text + out.slice(e.end);
  fs.writeFileSync(abs, out);
  s.shown = Number(idx);
  s.shaAfter = sha(Buffer.from(out));
  saveSession(root, s);
  return publicSession(s);
}

function removeMarkedImports(code, id, keepLocal, newSpec) {
  return code.split('\n').filter((line) => {
    if (!line.includes(`// dh-tryon:${id}`)) return true;
    return keepLocal && new RegExp(`\\b${keepLocal}\\b`).test(line);
  }).map((line) => {
    if (!line.includes(`// dh-tryon:${id}`)) return line;
    let l = line.replace(` // dh-tryon:${id}`, '');
    if (newSpec) l = l.replace(/from\s+(["'])[^"']+\1/, `from ${JSON.stringify(newSpec)}`);
    return l;
  }).join('\n');
}

function referencedByOtherOpen(root, dir, exceptId) {
  return listSessions(root).some((o) => o.id !== exceptId && o.state === 'open' && o.variants.some((v) => v.dir === dir));
}

const SAFE_GLOBALS = new Set(['Date', 'Math', 'Intl', 'String', 'Number', 'JSON', 'undefined']);

/** Text, plain host markup and self-contained expressions (`© {new Date().getFullYear()}`) only:
 *  safe to inline into another file because nothing refers to the usage site's scope. */
function markupOnly(frag) {
  let ok = true;
  walk(frag, (n, parent, key) => {
    if (!ok) return false;
    if (n.type === 'JSXOpeningElement' && !/^[a-z]/.test(jsxName(n.name))) { ok = false; return false; }
    if (n.type === 'JSXSpreadAttribute') { ok = false; return false; }
    if (n.type === 'Identifier') {
      const isProp = parent && ((parent.type === 'MemberExpression' && key === 'property' && !parent.computed) || (parent.type === 'ObjectProperty' && key === 'key'));
      if (!isProp && !SAFE_GLOBALS.has(n.name)) { ok = false; return false; }
    }
    return true;
  });
  return ok;
}

/** Drop import specifiers nobody references any more; delete folder files nothing imports. */
export function pruneFolder(root, dirRel, entryRel) {
  const dir = path.join(root, dirRel);
  const files = () => fs.readdirSync(dir).filter((f) => /\.(tsx|ts|jsx|js)$/.test(f));
  for (let pass = 0; pass < 5; pass++) {
    let changed = false;
    for (const f of files()) {
      const p = path.join(dir, f);
      let code = fs.readFileSync(p, 'utf8');
      const ast = parse(f, code);
      const edits = [];
      for (const st of ast.program.body) {
        if (st.type !== 'ImportDeclaration' || !st.specifiers.length) continue;
        const body = code.slice(0, st.start) + code.slice(st.end);
        const used = st.specifiers.filter((sp) => new RegExp(`(^|[^\\w$.])${sp.local.name}([^\\w$]|$)`).test(body));
        if (used.length === st.specifiers.length) continue;
        const end = code[st.end] === '\n' ? st.end + 1 : st.end;
        if (!used.length) { edits.push({ start: st.start, end, text: '' }); continue; }
        const def = used.find((sp) => sp.type === 'ImportDefaultSpecifier');
        const ns = used.find((sp) => sp.type === 'ImportNamespaceSpecifier');
        const named = used.filter((sp) => sp.type === 'ImportSpecifier').map((sp) => code.slice(sp.start, sp.end));
        const parts = [def && def.local.name, ns && code.slice(ns.start, ns.end), named.length && `{ ${named.join(', ')} }`].filter(Boolean);
        edits.push({ start: st.start, end: st.end, text: `import ${st.importKind === 'type' ? 'type ' : ''}${parts.join(', ')} from ${code.slice(st.source.start, st.source.end)}` });
      }
      if (!edits.length) continue;
      edits.sort((x, y) => y.start - x.start);
      for (const e of edits) code = code.slice(0, e.start) + e.text + code.slice(e.end);
      parse(f, code);
      fs.writeFileSync(p, code);
      changed = true;
    }
    // files no other file in the folder imports (the entry is always kept)
    const imported = new Set();
    for (const f of files()) {
      for (const m of fs.readFileSync(path.join(dir, f), 'utf8').matchAll(/from\s+['"]\.\/([^'"]+)['"]/g)) imported.add(m[1].replace(/\.(tsx|ts|jsx|js)$/, ''));
    }
    for (const f of files()) {
      if (path.posix.join(dirRel, f) === entryRel) continue;
      if (!imported.has(f.replace(/\.(tsx|ts|jsx|js)$/, ''))) { fs.unlinkSync(path.join(dir, f)); changed = true; }
    }
    if (!changed) break;
  }
}

/**
 * Bake the kept variant: literal copy goes INTO the component, show/hide switches are resolved
 * (hidden demo buttons and logo rows are deleted, not left dormant), and whatever the usage still
 * has to pass (in-scope expressions like {t('x')}) stays a prop. Unused imports/files are pruned.
 */
export function bake(root, fileRel, local, variant) {
  const abs = path.join(root, fileRel);
  let code = fs.readFileSync(abs, 'utf8');
  const ast = parse(fileRel, code);
  let usageEl = null;
  walk(ast, (n) => {
    if (usageEl) return false;
    if (n.type === 'JSXElement' && jsxName(n.openingElement.name) === local) { usageEl = n; return false; }
    return true;
  });
  if (!usageEl || !variant.prop) return { baked: 0 };
  const a = attr(usageEl, variant.prop);
  const values = new Map();          // key -> { kind: 'string'|'text'|'bool'|'json', ... }
  const keepProps = [];
  if (a && a.value && a.value.type === 'JSXExpressionContainer' && a.value.expression.type === 'ObjectExpression') {
    for (const p of a.value.expression.properties) {
      if (p.type !== 'ObjectProperty') { keepProps.push(code.slice(p.start, p.end)); continue; }
      const k = p.key.name || p.key.value;
      const v = p.value;
      if (v.type === 'StringLiteral') values.set(k, { kind: 'string', value: v.value });
      else if (v.type === 'BooleanLiteral') values.set(k, { kind: 'bool', value: v.value });
      else if (v.type === 'NumericLiteral') values.set(k, { kind: 'number', value: v.value });
      else if (v.type === 'ArrayExpression' && v.elements.length && v.elements.every((x) => x && x.type === 'ObjectExpression' && markupOnly(x))) {
        values.set(k, { kind: 'list', raw: code.slice(v.start, v.end), node: v });
      }
      else if (v.type === 'ArrayExpression' && v.elements.every((x) => x && x.type === 'StringLiteral')) values.set(k, { kind: 'array', raw: code.slice(v.start, v.end) });
      else if (v.type === 'JSXFragment' && markupOnly(v)) {
        let txt = '';
        walk(v, (n) => { if (n.type === 'JSXText') txt += n.value; return true; });
        values.set(k, { kind: 'text', value: txt.replace(/\s+/g, ' ').trim(), raw: v.children.length ? code.slice(v.children[0].start, v.children[v.children.length - 1].end) : '' });
      } else keepProps.push(code.slice(p.start, p.end));
    }
  }
  const live = new Set(keepProps.map((kp) => kp.split(':')[0].trim()));
  const cAbs = path.join(root, variant.entry);
  let comp = fs.readFileSync(cAbs, 'utf8');
  const accRe = new RegExp(`^(?:${variant.prop}|\\w+\\.${variant.prop}\\?)\\.(\\w+)$`);
  const keyOf = (node) => { const m = accRe.exec(comp.slice(node.start, node.end).replace(/\s/g, '')); return m ? m[1] : null; };
  const cast = parse(variant.entry, comp);
  const edits = [];
  walk(cast, (n, parent) => {
    // show/hide: {cond && cond && (<el/>)}
    if (n.type === 'JSXExpressionContainer' && n.expression.type === 'LogicalExpression' && n.expression.operator === '&&') {
      const conds = [];
      let e = n.expression;
      while (e.type === 'LogicalExpression' && e.operator === '&&') { conds.unshift(e.right); e = e.left; }
      conds.unshift(e);
      const body = conds.pop();
      const parsed = conds.map((c) => (c.type === 'BinaryExpression' && /^[!=]==$/.test(c.operator) && c.right.type === 'BooleanLiteral' ? { key: keyOf(c.left), op: c.operator, lit: c.right.value } : null));
      if (parsed.length && parsed.every((c) => c && c.key) && (body.type === 'JSXElement' || body.type === 'JSXFragment') && !parsed.some((c) => live.has(c.key))) {
        const on = parsed.every((c) => {
          const v = values.has(c.key) ? values.get(c.key).value : undefined;
          return c.op === '!==' ? v !== c.lit : v === c.lit;
        });
        edits.push({ start: n.start, end: n.end, text: on ? '__DH_KEEP__' : '', node: body });
        return on;               // descend into kept bodies for their slots
      }
    }
    if (n.type === 'LogicalExpression' && n.operator === '??') {
      const k = keyOf(n.left);
      if (k && live.has(k)) {
        // a live prop keeps its fallback, but never the preview's demo marker
        const r = n.right;
        if (r.type === 'JSXElement' && attr(r, 'data-dh-demo')) {
          const inner = r.children.length ? comp.slice(r.children[0].start, r.children[r.children.length - 1].end) : '';
          edits.push({ start: r.start, end: r.end, text: `<>${inner}</>` });
        }
        return false;
      }
      if (!k) return true;
      const container = parent && parent.type === 'JSXExpressionContainer' ? parent : null;
      const lit = values.get(k);
      if (!container) {
        // an expression slot (bullets: `(content.bullets1 ?? [...])`): inline the owner's array
        if (lit && lit.kind === 'array') edits.push({ start: n.start, end: n.end, text: lit.raw });
        else if (!lit) edits.push({ start: n.start, end: n.end, text: comp.slice(n.right.start, n.right.end) });
        return false;
      }
      const inAttr = comp[container.start - 1] === '=';
      let text;
      if (lit && lit.kind === 'bool' && lit.value === false && !inAttr) text = '';   // an optional slot left empty
      else if (lit && lit.kind !== 'bool') {
        if (inAttr) text = JSON.stringify(lit.value);
        else text = lit.kind === 'string' ? (/[{}<>]/.test(lit.value) ? `{${JSON.stringify(lit.value)}}` : lit.value) : lit.raw;
      } else {
        const r = n.right;
        if (inAttr) text = r.type === 'StringLiteral' ? JSON.stringify(r.value) : `{${comp.slice(r.start, r.end)}}`;
        else if (r.type === 'JSXFragment' || (r.type === 'JSXElement' && attr(r, 'data-dh-demo'))) text = r.children.length ? comp.slice(r.children[0].start, r.children[r.children.length - 1].end) : '';
        else text = `{${comp.slice(r.start, r.end)}}`;
      }
      edits.push({ start: container.start, end: container.end, text });
      return false;
    }
    // list slots `((content.list1 ? merge : demo) as typeof demo)`: unbound -> the design's own data
    if (n.type === 'ConditionalExpression') {
      // resolve a whole chain statically: `content.x ? a : b` and `content.cols === 2 ? "…" : …`
      const verdict = (t) => {
        const k1 = keyOf(t);
        if (k1 && !live.has(k1)) return values.has(k1) ? !!values.get(k1).value : false;
        if (t.type === 'BinaryExpression' && t.operator === '===' && t.right.type === 'NumericLiteral') {
          const k2 = keyOf(t.left);
          if (k2 && !live.has(k2)) return values.has(k2) ? Number(values.get(k2).value) === t.right.value : false;
        }
        return null;
      };
      // a list slot with literal data: the owner's items are written INTO the design's own array
      // (fields the owner did not give — icons, ids — keep the design's values), then the switch goes
      const lk = keyOf(n.test);
      if (lk && values.has(lk) && values.get(lk).kind === 'list' && n.alternate.type === 'Identifier') {
        const arrName = n.alternate.name;
        let decl = null;
        walk(cast, (m) => {
          if (decl) return false;
          if (m.type === 'VariableDeclarator' && m.id.type === 'Identifier' && m.id.name === arrName) {
            let init = m.init;
            while (init && /^TS(As|Satisfies)Expression$/.test(init.type)) init = init.expression;
            if (init && init.type === 'ArrayExpression') decl = init;
            return false;
          }
          return true;
        });
        if (decl && decl.elements.length && decl.elements.every((e) => e && e.type === 'ObjectExpression')) {
          const ownerItems = values.get(lk).node.elements;
          const objSrc = (i) => {
            const demoEl = decl.elements[i % decl.elements.length];
            const own = ownerItems[i];
            const ownKeys = new Map(own.properties.map((p) => [p.key.name || p.key.value, code.slice(p.value.start, p.value.end)]));
            const parts = [];
            for (const p of demoEl.properties) {
              const key = p.type === 'ObjectProperty' ? (p.key.name || p.key.value) : null;
              if (key && ownKeys.has(key)) { parts.push(`${comp.slice(p.key.start, p.key.end)}: ${ownKeys.get(key)}`); ownKeys.delete(key); }
              else parts.push(comp.slice(p.start, p.end));
            }
            for (const [key, val] of ownKeys) parts.push(`${JSON.stringify(key)}: ${val}`);
            return `{ ${parts.join(', ')} }`;
          };
          const ind = indentAt(comp, decl.elements[0].start);
          edits.push({ start: decl.start, end: decl.end, text: `[\n${ownerItems.map((_, i) => ind + objSrc(i)).join(',\n')},\n${ind.slice(0, -2) || ''}]` });
          const target = parent && parent.type === 'TSAsExpression' ? parent : n;
          edits.push({ start: target.start, end: target.end, text: arrName });
          return false;
        }
      }
      if (verdict(n.test) !== null) {
        let node = n;
        while (node.type === 'ConditionalExpression' && verdict(node.test) !== null) node = verdict(node.test) ? node.consequent : node.alternate;
        const target = parent && parent.type === 'TSAsExpression' && keyOf(n.test) ? parent : n;
        edits.push({ start: target.start, end: target.end, text: comp.slice(node.start, node.end) });
        return false;
      }
    }
    return true;
  });
  // apply innermost-first: a kept wrapper body may contain slot edits
  edits.sort((x, y) => y.start - x.start || x.end - y.end);
  const applied = [];
  for (const e of edits) {
    if (applied.some((o) => o.start <= e.start && e.end <= o.end && o !== e && o.text === '')) continue;
    if (e.text === '__DH_KEEP__') {
      // unwrap: keep the body with every nested edit already applied
      // top-level edits already applied inside this body (a nested unwrap absorbed its own children)
      const inner = applied.filter((o) => o.start >= e.node.start && o.end <= e.node.end);
      const shift = inner.reduce((acc, o) => acc + (o.text.length - (o.end - o.start)), 0);
      const bodyText = comp.slice(e.node.start, e.node.end + shift);
      comp = comp.slice(0, e.start) + bodyText + comp.slice(e.end + shift);
      for (const o of inner) applied.splice(applied.indexOf(o), 1);
      applied.push({ start: e.start, end: e.end, text: bodyText });
      continue;
    }
    comp = comp.slice(0, e.start) + e.text + comp.slice(e.end);
    for (const o of applied.filter((x) => x.start >= e.start && x.end <= e.end)) applied.splice(applied.indexOf(o), 1);
    applied.push(e);
  }
  // `unoptimized` was a preview guard for remote demo images; a local src gets Next's optimizer back
  comp = comp.replace(/(<\w+) unoptimized(\s+src="\/[^"]*(?<!\.svg)")/g, '$1$2');
  if (!keepProps.length) {
    comp = comp.replace(`{ ${variant.prop} = {} }: { ${variant.prop}?: Record<string, any> } = {}`, '')
      .replace(`{ ${variant.prop} = {} } = {}`, '')
      .replace(` ${variant.prop} = {},`, '')
      .replace(` & { ${variant.prop}?: Record<string, any> }`, '');
  }
  try { parse(variant.entry, comp); } catch (e) {
    if (process.env.DH_DEBUG_BAKE) fs.writeFileSync(process.env.DH_DEBUG_BAKE, comp);
    throw e;
  }
  fs.writeFileSync(cAbs, comp);
  pruneFolder(root, path.posix.dirname(variant.entry), variant.entry);
  // the usage keeps only live props
  if (a) {
    const newAttr = keepProps.length ? `${variant.prop}={{ ${keepProps.join(', ')} }}` : '';
    const start = keepProps.length ? a.start : (code[a.start - 1] === ' ' ? a.start - 1 : a.start);
    code = code.slice(0, start) + newAttr + code.slice(a.end);
    parse(fileRel, code);
    fs.writeFileSync(abs, code);
  }
  return { baked: values.size, live: keepProps.length };
}

/** Static prose a design ships (JSX text + prose strings in its data arrays), minus the owner's words
 *  and minus fallbacks of live slots. Used to rank (mockup-heavy designs lose) and to ledger what the
 *  owner still has to replace before launch. */
const ENT = { '&apos;': "'", '&#39;': "'", '&quot;': '"', '&amp;': '&', '&lt;': '<', '&gt;': '>', '&nbsp;': ' ' };
/** Text reduced to letters and digits (markup, quotes, punctuation and spacing never decide a match). */
export const flatText = (s) => String(s || '').replace(/&[#\w]+;/g, (m) => ENT[m] || ' ').replace(/<[^>]*>/g, '').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');

/**
 * How much of the owner's content a hand-written (AI) component really holds: every text unit, link
 * target, image and bullet is looked up in its source. `invented` = words on it the owner never wrote.
 */
export function literalFit(root, dirRel, orig, dynamic = []) {
  const dir = path.join(root, dirRel);
  const code = fs.readdirSync(dir).filter((f) => /\.(tsx|jsx|ts|js)$/.test(f)).map((f) => fs.readFileSync(path.join(dir, f), 'utf8')).join('\n');
  const hay = flatText(code);
  const dynKey = new Map(dynamic.map((d) => [d.src, d.key]));
  const lit = (src) => { try { const v = JSON.parse(src); return typeof v === 'string' ? v : null; } catch { return null; } };
  const has = (v) => code.includes(JSON.stringify(v)) || code.includes(`'${v}'`) || code.includes('`' + v + '`');
  const carried = [], dropped = [];
  for (const u of orig.units) {
    let ok = u.dynamic ? new RegExp(`content\\??\\.${dynKey.get(u.src)}\\b`).test(code) : !flatText(u.text) || hay.includes(flatText(u.text));
    let text = u.text;
    const href = u.role === 'action' && u.href ? lit(u.href) : null;
    if (ok && href && !has(href)) { ok = false; text += ` (link ${href})`; }
    (ok ? carried : dropped).push({ role: u.role, text });
  }
  for (const im of orig.images) {
    const src = lit(im.src);
    if (src) (has(src) ? carried : dropped).push({ role: 'image', text: src });
  }
  for (const l of orig.lists) for (const it of l.items) for (const b of it.bullets || []) (hay.includes(flatText(b)) ? carried : dropped).push({ role: 'item', text: b });
  const own = orig.units.map((u) => flatText(u.text)).concat(orig.lists.flatMap((l) => l.items.flatMap((it) => (it.bullets || []).map(flatText)))).filter(Boolean);
  const invented = demoTexts(root, dirRel, []).map((e) => e.text).filter((t) => !own.some((o) => o.includes(flatText(t))));
  return { carried, dropped, invented: [...new Set(invented)], of: carried.length + dropped.length };
}

export function demoTexts(root, dirRel, ownerTexts = []) {
  const brand = brandName(root);   // the owner's own name is never demo copy
  const own = new Set(ownerTexts.concat(brand ? [brand, `© ${brand}`] : []).map((t) => String(t).replace(/\s+/g, ' ').trim().toLowerCase()));
  const out = [];
  const dir = path.join(root, dirRel);
  if (!fs.existsSync(dir)) return out;
  for (const f of fs.readdirSync(dir)) {
    if (!/\.(tsx|jsx)$/.test(f)) continue;
    const code = fs.readFileSync(path.join(dir, f), 'utf8');
    let ast;
    try { ast = parse(f, code); } catch { continue; }
    const push = (t) => {
      const x = String(t).replace(/\s+/g, ' ').trim();
      if ((x.match(/\p{L}/gu) || []).length < 3 || own.has(x.toLowerCase())) return;
      if (x.split(/\s+/).every((t) => /^[a-z0-9:/[\]._%!*&>()-]+$/.test(t)) && /(^|\s)[a-z0-9:]+-[\w./-]+/.test(x)) return;   // a class list
      if (/^(https?:|\/|#|mailto:|tel:)/.test(x)) return;
      out.push({ file: path.posix.join(dirRel, f), text: x.slice(0, 120) });
    };
    walk(ast, (n, parent) => {
      if (n.type === 'LogicalExpression' && n.operator === '??') return false;          // a slot fallback
      if (n.type === 'JSXAttribute') return false;
      if (n.type === 'ImportDeclaration' || n.type === 'TSTypeAnnotation') return false;
      if (n.type === 'JSXText') push(n.value);
      if (n.type === 'StringLiteral' && parent && (parent.type === 'ObjectProperty' && parent.value === n || parent.type === 'ArrayExpression')) {
        if (/\s/.test(n.value) || /^[A-Z][a-z]+/.test(n.value)) push(n.value);
      }
      return true;
    });
  }
  return out;
}

export function recordDemoCopy(root, entries) {
  const p = path.join(root, '.deckhand', 'demo-copy.json');
  let doc = { entries: [] };
  try { doc = JSON.parse(fs.readFileSync(p, 'utf8')); } catch { /* new */ }
  const key = (e) => e.file + '\u0000' + e.text;
  const seen = new Set(doc.entries.map(key));
  for (const e of entries) if (!seen.has(key(e))) { doc.entries.push(e); seen.add(key(e)); }
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(doc, null, 1));
  return doc.entries.length;
}

const NOTICE_FILE = 'THIRD_PARTY_NOTICES.md';

function recordNotice(root, v) {
  const p = path.join(root, NOTICE_FILE);
  const regs = JSON.parse(fs.readFileSync(path.join(SKILL_DIR, 'data', 'registries.json'), 'utf8')).registries;
  const reg = regs.find((r) => r.id === v.r) || {};
  let text = fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '# Third-party notices\n\nComponents adapted from open-source registries (kept via deckhand try-on).\n';
  const line = `- \`${v.finalDir || v.dir}\` — ${v.t} · ${v.r}/${v.n} · ${v.lic} · ${v.sourceUrl}${reg.copyright ? ' · ' + reg.copyright : ''}`;
  if (!text.includes(v.sourceUrl)) text = text.replace(/\s*$/, '\n') + line + '\n';
  if (reg.license === 'MIT' && !text.includes('Permission is hereby granted')) {
    text += '\n## MIT License (applies to the components above unless noted)\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n';
  }
  fs.writeFileSync(p, text);
}

export function keep(rootIn, id, idx) {
  const root = path.resolve(rootIn);
  const prof = detectProject(root);
  const s = loadSession(root, id);
  if (s.state !== 'open') throw new TryonError('SESSION_CLOSED', `session ${id} is ${s.state}`);
  const i = Number(idx ?? s.shown);
  if (i === 0) return discard(root, id, { reason: 'kept original' });
  const v = s.variants.find((x) => x.idx === i);
  if (!v) throw new TryonError('NO_VARIANT', `session ${id} has no variant ${i}`);
  const abs = path.join(root, s.file);
  let code = fs.readFileSync(abs, 'utf8');
  const w = findWrapper(parse(s.file, code), id);
  if (!w) throw new TryonError('WRAPPER_MISSING', 'the variant wrapper is gone from ' + s.file);
  const chosen = variantChildren(w).find((c) => Number(attr(c, 'data-dh-variant').value.value) === i);
  let inner = innerSrc(code, chosen);
  // graduate the folder
  const final = path.posix.join(prof.componentsDir, s.kind === 'block' ? 'sections' : 'ui-kit', v.slug);
  const shared = referencedByOtherOpen(root, v.dir, id);
  fs.mkdirSync(path.dirname(path.join(root, final)), { recursive: true });
  fs.rmSync(path.join(root, final), { recursive: true, force: true });
  if (shared) fs.cpSync(path.join(root, v.dir), path.join(root, final), { recursive: true });
  else fs.renameSync(path.join(root, v.dir), path.join(root, final));
  const entryFinal = path.posix.join(final, path.posix.basename(v.entry));
  const newSpec = specFor(prof, entryFinal) || './' + entryFinal;
  // a clean local name for the kept component
  const cleanLocal = uniqueName((v.generated ? pascal(s.slot) + 'AiDraft' : pascal(v.n)).slice(0, 48), identifiers(code.replace(new RegExp(`\\b${v.local}\\b`, 'g'), '')));
  inner = inner.replace(new RegExp(`\\b${v.local}\\b`, 'g'), cleanLocal);
  code = code.slice(0, w.start) + inner + code.slice(w.end);
  code = removeMarkedImports(code, id, v.local, newSpec).replace(new RegExp(`\\b${v.local}\\b`, 'g'), cleanLocal);
  parse(s.file, code);
  fs.writeFileSync(abs, code);
  // strip the staging header note, keep attribution
  const eAbs = path.join(root, entryFinal);
  for (const f of fs.readdirSync(path.join(root, final))) {
    const p = path.join(root, final, f);
    if (/\.(tsx|ts|jsx|js)$/.test(f)) fs.writeFileSync(p, fs.readFileSync(p, 'utf8').replace(' · staged by deckhand try-on */', ' */'));
  }
  const baked = s.kind === 'block' ? bake(root, s.file, cleanLocal, { ...v, entry: entryFinal }) : { baked: 0 };
  void eAbs;
  // losers
  for (const o of s.variants) {
    if (o.idx === i) continue;
    if (!referencedByOtherOpen(root, o.dir, id)) fs.rmSync(path.join(root, o.dir), { recursive: true, force: true });
    if (o.css) removeCss(prof, /dh:css ([^ ]+) \*\//.exec(o.css)[1]);
  }
  const stageRoot = path.join(root, prof.componentsDir, 'dh-tryon');
  if (fs.existsSync(stageRoot) && !fs.readdirSync(stageRoot).length) fs.rmdirSync(stageRoot);
  v.finalDir = final;
  if (!v.generated) recordNotice(root, v);             // AI-written code is the owner's: provenance lives in its header
  let leftovers = demoTexts(root, final, v.ownerTexts || []);
  if (v.generated) {
    const own = (v.ownerTexts || []).map(flatText);
    leftovers = leftovers.filter((e) => !own.some((o) => o.includes(flatText(e.text)))).map((e) => ({ ...e, ai: true }));
  }
  if (leftovers.length) recordDemoCopy(root, leftovers);
  s.state = 'kept';
  s.chosen = i;
  s.keptAt = now();
  s.final = { dir: final, entry: entryFinal, spec: newSpec, local: cleanLocal, baked };
  saveSession(root, s);
  return { ok: true, id, kept: v.t, file: s.file, component: entryFinal, local: cleanLocal, baked, fit: v.fit, notice: NOTICE_FILE,
    generated: !!v.generated,
    demo_copy_to_replace: leftovers.map((e) => e.text).slice(0, 20),
    next: v.generated ? (leftovers.length ? 'the AI wrote the words listed above — the owner confirms or rewrites them (dh rebrand check warns until then)' : null)
      : leftovers.length ? 'replace or delete the design\'s demo copy listed above (dh rebrand check blocks until then)' : null };
}

export function discard(rootIn, id, { reason } = {}) {
  const root = path.resolve(rootIn);
  const prof = detectProject(root);
  const s = loadSession(root, id);
  if (s.state !== 'open') throw new TryonError('SESSION_CLOSED', `session ${id} is ${s.state}`);
  const abs = path.join(root, s.file);
  const cur = fs.readFileSync(abs);
  let mode;
  if (sha(cur) === s.shaAfter) {
    fs.writeFileSync(abs, fs.readFileSync(path.join(root, s.backup)));
    mode = 'byte-exact';
  } else {
    let code = cur.toString('utf8');
    const w = findWrapper(parse(s.file, code), id);
    if (w) {
      const orig = variantChildren(w).find((c) => Number(attr(c, 'data-dh-variant').value.value) === 0);
      code = code.slice(0, w.start) + innerSrc(code, orig) + code.slice(w.end);
    }
    code = removeMarkedImports(code, id, null);
    parse(s.file, code);
    fs.writeFileSync(abs, code);
    mode = 'surgical (file changed since the try)';
  }
  for (const v of s.variants) {
    if (!referencedByOtherOpen(root, v.dir, id)) fs.rmSync(path.join(root, v.dir), { recursive: true, force: true });
    if (v.css) removeCss(prof, /dh:css ([^ ]+) \*\//.exec(v.css)[1]);
  }
  const stageRoot = path.join(root, prof.componentsDir, 'dh-tryon');
  if (fs.existsSync(stageRoot) && !fs.readdirSync(stageRoot).length) fs.rmdirSync(stageRoot);
  s.state = 'discarded';
  s.discardedAt = now();
  s.reason = reason || null;
  saveSession(root, s);
  return { ok: true, id, restored: s.file, mode };
}

/** Where is this element, what could it be swapped with? (no writes) */
export function inspect(rootIn, { file, line, col, slot }) {
  const prof = detectProject(rootIn);
  const rel = String(file).replace(/\\/g, '/');
  const abs = path.join(prof.root, rel);
  if (!fs.existsSync(abs)) throw new TryonError('NO_FILE', rel);
  const code = fs.readFileSync(abs, 'utf8');
  const el = findElementAt(parse(rel, code), code, Number(line), Number(col));
  if (!el) throw new TryonError('ELEMENT_NOT_FOUND', `${rel}:${line}:${col}`);
  const u = extractUnits(code, el, parse(rel, code));
  const r = slot ? rank(loadCatalog(), { slot, prof }) : { items: [], hidden: 0 };
  const lc = lineCol(code, el.end);
  return {
    file: rel, line: Number(line), col: Number(col), endLine: lc.line, tag: jsxName(el.openingElement.name),
    content: u.units.map((x) => ({ role: x.role, text: x.text.slice(0, 80), list: x.list })), images: u.images.length, lists: u.lists.length, dynamicLists: u.dynamicLists,
    project: { framework: prof.framework, base: prof.base, tailwind: prof.tailwind, tokens: prof.tokens.primary },
    candidates: r.items.length, hidden: r.hidden, top: r.items.slice(0, 8).map((x) => ({ id: x.id, t: x.t, missing: x.missing })),
  };
}

export { entryExport, slugOf };
