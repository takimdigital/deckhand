#!/usr/bin/env node
/**
 * compose.mjs — a page from licensed blocks + the plan's copy, no code generation.
 *
 *   node tryon/compose.mjs --project . --page app/page.tsx --sections hero,features,pricing,faq,cta,footer
 *                          [--copy .deckhand/copy.json] [--registry tailark-oss]
 *
 * copy.json (the one input a model writes, from the plan — words, never code):
 *   { "hero": { "heading": "…", "text": ["…"], "actions": [{ "label": "…", "href": "/order" }], "image": { "src": "/x.jpg", "alt": "…" } },
 *     "pricing": { "heading": "…", "items": [{ "title": "…", "price": "€9", "text": "…", "bullets": ["…"], "action": { "label": "…", "href": "…" } }] } }
 * Every section lands in components/sections/<slug>/, the page imports them in order; each is then
 * swappable with try-on. Copy the design has no room for is reported, never silently dropped.
 */
import fs from 'node:fs';
import path from 'node:path';
import { detectProject, specFor } from './lib/project.mjs';
import { loadCatalog, rank } from './lib/catalog.mjs';
import { fetchBundle, writeBundle, pascal } from './lib/materialize.mjs';
import { parameterize, bind, contentProp } from './lib/transplant.mjs';
import { ensureTokens, bake, PLACEHOLDER, logoLocalsFor } from './lib/engine.mjs';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const root = path.resolve(opt('project', '.'));
const page = opt('page', 'app/page.tsx');
const sections = String(opt('sections', 'hero,features,cta,footer')).split(',').map((s) => s.trim()).filter(Boolean);
const copy = opt('copy') ? JSON.parse(fs.readFileSync(path.resolve(root, opt('copy')), 'utf8')) : {};
const registry = opt('registry', null);
const out = (o, c = 0) => { process.stdout.write(JSON.stringify(o) + '\n'); process.exit(c); };

const esc = (s) => (/[{}<>]/.test(String(s)) ? `{${JSON.stringify(String(s))}}` : String(s));
const unit = (role, text, href) => ({ role, text: String(text), src: esc(text), href: href ? JSON.stringify(href) : null, list: null });

/** copy.json section -> the same shape extractUnits() returns for a clicked element. */
function origFromCopy(c = {}) {
  const units = [];
  if (c.eyebrow) units.push(unit('text', c.eyebrow));
  if (c.heading) units.push(unit('heading', c.heading));
  for (const t of [].concat(c.text || [])) units.push(unit('text', t));
  for (const a of [].concat(c.actions || [])) units.push(unit('action', a.label, a.href));
  const images = c.image ? [{ src: JSON.stringify(c.image.src), alt: JSON.stringify(c.image.alt || '') }] : [];
  const lists = [];
  if (Array.isArray(c.items) && c.items.length) {
    lists.push({ items: c.items.map((it) => {
      const us = [];
      if (it.title) us.push(unit('heading', it.title));
      if (it.price) us.push(unit('price', it.price));
      for (const t of [].concat(it.text || [])) us.push(unit('text', t));
      if (it.action) us.push(unit('action', it.action.label, it.action.href));
      return { units: us.map((u) => ({ ...u, list: 0 })), images: it.image ? [{ src: JSON.stringify(it.image.src), alt: JSON.stringify(it.image.alt || '') }] : [], bullets: it.bullets || [] };
    }) });
    lists[0].items.forEach((it, i) => it.units.forEach((u) => units.push({ ...u, item: i })));
  }
  return { units, images, inputs: [], lists, dynamicLists: 0 };
}

async function main() {
  const prof = detectProject(root);
  if (prof.tailwind === 4) ensureTokens(prof, {});
  const catalog = loadCatalog();
  const used = new Set();
  const placed = [];
  const report = [];
  for (const slot of sections) {
    const ranked = rank(catalog, { slot, prof: detectProject(root), registry }).items;
    let done = null;
    for (const cand of ranked.slice(0, 8)) {
      try {
        const p0 = detectProject(root);
        const bundle = await fetchBundle(p0, cand);
        const stage = writeBundle(p0, cand, bundle, { baseDir: path.posix.join(p0.componentsDir, 'sections') });
        if (stage.problems.length || !stage.export) { fs.rmSync(path.join(root, stage.relDir), { recursive: true, force: true }); continue; }
        const entryAbs = path.join(root, stage.entry);
        const entryCode = fs.readFileSync(entryAbs, 'utf8');
        const p = parameterize(stage.entry, entryCode, stage.export, { stripChrome: slot !== 'navbar', logoLocals: logoLocalsFor(stage, entryCode, slot) });
        fs.writeFileSync(entryAbs, p.code);
        const b = bind(origFromCopy(copy[slot]), p, { placeholder: fs.existsSync(path.join(root, 'public')) ? PLACEHOLDER : null });
        let local = pascal(cand.n).slice(0, 40);
        while (used.has(local)) local += '2';
        used.add(local);
        done = { slot, cand, stage, prop: p.prop, local, usage: `<${local}${contentProp(p.prop, b.props)} />`, fit: b };
        break;
      } catch { /* next candidate */ }
    }
    if (!done) { report.push({ slot, ok: false, why: 'no candidate could be staged' }); continue; }
    placed.push(done);
    report.push({ slot, ok: true, component: done.stage.entry, from: done.cand.id, licence: done.cand.lic,
      carried: done.fit.carried.length, dropped: done.fit.dropped.map((d) => d.text), demo: done.fit.demo.map((d) => d.text), hidden: done.fit.hidden });
  }
  const imports = placed.map((d) => (d.stage.export.kind === 'default'
    ? `import ${d.local} from ${JSON.stringify(specFor(prof, d.stage.entry))}`
    : `import { ${d.stage.export.name} as ${d.local} } from ${JSON.stringify(specFor(prof, d.stage.entry))}`)).join('\n');
  const pageAbs = path.join(root, page);
  if (fs.existsSync(pageAbs)) fs.copyFileSync(pageAbs, pageAbs + '.before-compose');
  fs.mkdirSync(path.dirname(pageAbs), { recursive: true });
  fs.writeFileSync(pageAbs, `${imports}\n\nexport default function Page() {\n  return (\n    <main>\n${placed.map((d) => '      ' + d.usage).join('\n')}\n    </main>\n  );\n}\n`);
  for (const d of placed) bake(root, page, d.local, { entry: d.stage.entry, prop: d.prop });
  const deps = [...new Set(placed.flatMap((d) => d.stage.missingDeps))];
  out({ ok: placed.length > 0, page, sections: report, missingDeps: deps,
    next: deps.length ? `install: ${deps.join(' ')} — then dh dev start; swap any section with try-on` : 'dh dev start; swap any section with try-on' });
}
main().catch((e) => out({ ok: false, code: e.code || 'ERROR', message: String(e.message || e) }, 1));
