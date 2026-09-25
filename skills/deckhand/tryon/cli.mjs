#!/usr/bin/env node
/**
 * tryon — Deckhand's live component swap. One JSON object per command on stdout; exit 0 = ok.
 *
 *   node tryon/cli.mjs setup    [--project .]                      wire the dev-only stamp (restart dev)
 *   node tryon/cli.mjs serve    [--project .] [--port 3999] [--target http://127.0.0.1:3000]
 *   node tryon/cli.mjs doctor   [--project .]                      is everything wired? (no writes)
 *   node tryon/cli.mjs slots    [--project .]                      what can be tried here
 *   node tryon/cli.mjs query    --slot hero [--project .]          ranked candidates (no writes)
 *   node tryon/cli.mjs inspect  --file f --line n --col c [--slot s]
 *   node tryon/cli.mjs try      --file f --line n --col c --slot s [--count 4] [--no-install] [--registry r]
 *   node tryon/cli.mjs show     --id S --idx N                     make variant N the visible one
 *   node tryon/cli.mjs keep     --id S [--idx N]                   collapse to N, bake the text, graduate
 *   node tryon/cli.mjs discard  --id S                             byte-exact restore
 *   node tryon/cli.mjs save     --id S [--name n]                  kept component -> personal library
 *   node tryon/cli.mjs status   [--project .]
 *   node tryon/cli.mjs clean    [--project .]                      discard open sessions, unwire
 */
import fs from 'node:fs';
import path from 'node:path';
import * as engine from './lib/engine.mjs';
import { setup, unsetup, readJournal } from './lib/setup.mjs';
import { detectProject } from './lib/project.mjs';
import { loadCatalog, rank, slotsSummary } from './lib/catalog.mjs';
import { saveToLibrary, listLibrary } from './lib/library.mjs';
import { startServer, detectTarget } from './server.mjs';

const argv = process.argv.slice(2);
const cmd = argv[0];
const flags = {};
for (let i = 1; i < argv.length; i++) {
  const a = argv[i];
  if (!a.startsWith('--')) continue;
  const k = a.slice(2);
  if (k.startsWith('no-')) { flags[k.slice(3)] = false; continue; }
  const v = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
  flags[k] = v;
}
const project = path.resolve(String(flags.project || '.'));
const out = (o, code = 0) => { process.stdout.write(JSON.stringify(o) + '\n'); process.exit(code); };
const need = (...ks) => { const miss = ks.filter((k) => flags[k] === undefined || flags[k] === true); if (miss.length) out({ ok: false, code: 'USAGE', missing: miss.map((m) => '--' + m) }, 2); };

async function main() {
  switch (cmd) {
    case 'setup': return out(setup(project));
    case 'serve': {
      const target = flags.target || await detectTarget(project);
      if (!target) out({ ok: false, code: 'NO_DEV_SERVER', hint: 'start the dev server first (npm run dev), or pass --target http://127.0.0.1:<port>' }, 1);
      const s = await startServer({ root: project, port: Number(flags.port || 3999), target, log: flags.verbose ? (e) => console.error(JSON.stringify(e)) : () => {} });
      process.stdout.write(JSON.stringify({ ok: true, open: s.url, proxying: target, note: 'open the URL, click Try-on (bottom right). Ctrl+C stops.' }) + '\n');
      return;
    }
    case 'doctor': {
      const prof = detectProject(project);
      const j = readJournal(project);
      const target = flags.target || await detectTarget(project);
      let stamped = null;
      if (target) {
        try { stamped = /data-dh="/.test(await (await fetch(target + (flags.path || '/'))).text()); } catch { stamped = false; }
      }
      const checks = {
        framework: prof.framework, supported: ['next', 'vite'].includes(prof.framework), wired: !!j, devServer: target || null,
        stampsInHtml: stamped, tailwind: prof.tailwind, tokens: prof.tokens, base: prof.base, globalsCss: prof.globalsCss,
      };
      const next = !checks.supported ? 'degraded mode: use `try` with --file/--line/--col' : !j ? 'run `setup`, then restart the dev server'
        : !target ? 'start the dev server' : stamped === false ? 'restart the dev server so the stamp loader loads' : 'run `serve` and open its URL';
      return out({ ok: true, ...checks, next });
    }
    case 'slots': {
      const prof = detectProject(project);
      return out({ ok: true, base: prof.base, slots: slotsSummary(loadCatalog(), prof) });
    }
    case 'query': {
      need('slot');
      const prof = detectProject(project);
      const r = rank(loadCatalog(), { slot: flags.slot, prof, registry: flags.registry || null });
      return out({ ok: true, slot: flags.slot, hidden: r.hidden, total: r.items.length,
        top: r.items.slice(0, Number(flags.top || 8)).map((x) => ({ id: x.id, t: x.t, score: x.score, missing: x.missing })) });
    }
    case 'inspect': need('file', 'line', 'col'); return out({ ok: true, ...engine.inspect(project, flags) });
    case 'try': {
      need('file', 'line', 'col', 'slot');
      const r = await engine.open(project, { ...flags, install: flags.install !== false, onProgress: flags.verbose ? (p) => console.error(JSON.stringify(p)) : undefined });
      return out({ ok: true, ...r, next: `compare in the browser (←/→) or \`show --id ${r.id} --idx N\`; then \`keep --id ${r.id} --idx N\` or \`discard --id ${r.id}\`` });
    }
    case 'show': need('id', 'idx'); return out({ ok: true, ...engine.show(project, flags.id, flags.idx) });
    case 'keep': need('id'); return out(engine.keep(project, flags.id, flags.idx));
    case 'discard': need('id'); return out(engine.discard(project, flags.id));
    case 'save': need('id'); return out({ ok: true, ...saveToLibrary(project, flags.id, { name: flags.name }) });
    case 'library': return out({ ok: true, items: listLibrary().map((i) => ({ id: i.id, slot: i.slot, t: i.t })) });
    case 'status': {
      const ss = engine.listSessions(project);
      return out({ ok: true, wired: !!readJournal(project), open: ss.filter((s) => s.state === 'open').map(engine.publicSession),
        kept: ss.filter((s) => s.state === 'kept').map((s) => ({ id: s.id, file: s.file, component: s.final?.entry })) });
    }
    case 'clean': {
      const ss = engine.listSessions(project);
      const discarded = ss.filter((s) => s.state === 'open').map((s) => engine.discard(project, s.id).id);
      const kept = ss.some((s) => s.state === 'kept');
      const r = unsetup(project, { keepTokens: kept ? true : false });
      if (!kept) { try { fs.unlinkSync(path.join(project, 'public', 'deckhand-placeholder.svg')); } catch { /* none */ } }
      return out({ ok: true, discarded, ...r, restartDevServer: true });
    }
    default:
      return out({ ok: false, code: 'USAGE', commands: ['setup', 'serve', 'doctor', 'slots', 'query', 'inspect', 'try', 'show', 'keep', 'discard', 'save', 'library', 'status', 'clean'] }, 2);
  }
}

main().catch((e) => out({ ok: false, code: e.code || 'ERROR', message: String(e.message || e).slice(0, 3000), skipped: e.skipped }, 1));
