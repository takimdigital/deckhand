/**
 * catalog.mjs — deterministic candidate ranking. Same inputs -> same order, always.
 * Personal library items (r = "mine") rank first; base mismatches are hidden AND counted.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { COMPATIBLE, kindOf } from './slots.mjs';
import { depInstalled } from './project.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const SKILL_DIR = path.resolve(HERE, '..', '..');

export function libraryDir() {
  return process.env.DECKHAND_LIBRARY || path.join(process.env.DECKHAND_HOME || path.join(os.homedir(), '.deckhand'), 'library');
}

export function loadCatalog() {
  const main = JSON.parse(fs.readFileSync(path.join(SKILL_DIR, 'data', 'components.index.json'), 'utf8'));
  let items = main.items;
  const mine = path.join(libraryDir(), 'components.index.json');
  if (fs.existsSync(mine)) {
    try { items = JSON.parse(fs.readFileSync(mine, 'utf8')).items.concat(items); } catch { /* a broken personal index never blocks the catalog */ }
  }
  return items;
}

function baseScore(projectBase, itemBase) {
  if (itemBase === 'any' || !itemBase) return 20;
  if (projectBase === 'none') return itemBase === 'radix' ? 25 : 10;
  if (projectBase === itemBase) return 30;
  return null;                                   // hidden: a Radix project never gets Base UI code
}

export function rank(items, { slot, prof, exclude = [], registry = null }) {
  const cousins = COMPATIBLE[slot] || [slot];
  const out = [];
  let hidden = 0;
  for (const it of items) {
    if (exclude.includes(it.id)) continue;
    if (registry && it.r !== registry) continue;
    const exact = it.slot === slot;
    if (!exact && !cousins.includes(it.slot)) continue;
    // the project's own primitive is not an alternative to itself
    if (it.kind === 'ui' && (it.r === 'shadcn' || it.r === 'basecn') && prof.ui && prof.ui[it.n]) continue;
    const b = baseScore(prof.base, it.base);
    if (b === null) { hidden++; continue; }
    let s = (exact ? 100 : 40) + b;
    if (it.r === 'mine') s += 60;
    if (kindOf(slot) === 'block' && it.r === 'tailark-oss') s += 5;
    const missing = (it.deps || []).filter((d) => !depInstalled(prof, d));
    s -= missing.length * 6;
    out.push({ ...it, score: s, missing });
  }
  out.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
  // diversity: round-robin over registry+kit groups so a batch shows different design languages
  const group = kitOf;
  const buckets = new Map();
  for (const x of out) { const g = group(x); if (!buckets.has(g)) buckets.set(g, []); buckets.get(g).push(x); }
  const order = [...buckets.keys()].sort((a, b) => buckets.get(b)[0].score - buckets.get(a)[0].score || a.localeCompare(b));
  const mixed = [];
  for (let i = 0; mixed.length < out.length; i++) for (const g of order) if (buckets.get(g)[i]) mixed.push(buckets.get(g)[i]);
  return { items: mixed, hidden };
}

/** A design family: one Tailark kit (dusk / mist / veil) or one registry. */
export const kitOf = (x) => x.r + ':' + (x.r === 'tailark-oss' ? x.n.split('-')[0] : '');

export function slotsSummary(items, prof) {
  const counts = {};
  for (const it of items) {
    if (baseScore(prof.base, it.base) === null) continue;
    counts[it.slot] = (counts[it.slot] || 0) + 1;
  }
  return counts;
}
