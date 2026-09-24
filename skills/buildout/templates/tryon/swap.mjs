#!/usr/bin/env node
/**
 * swap.mjs — the component-swap codemod for TSX (part of buildout's /buildout try-on).
 *
 * Parse with the PROJECT's own `typescript` compiler API, compute EXACT character ranges for the
 * import binding, and do a source-preserving string splice. No regex, no AST reprint, no extra
 * dependency. Every edit re-parses the file at edit time (never trusts cached line numbers) and is
 * verified before it is written: the target local name must resolve to the new specifier, parse
 * diagnostics must stay at zero, and every other import binding must stay byte-identical.
 *
 * Subcommands
 *   install  --from <candidate.tsx> --slot <slotDir> --entry <ExportedName> [--as name.tsx] [--root R]
 *              [--request N] [--meta-file <json>]  → also appends one entry to .tryon/manifest.json
 *              (staged file + specifier + sha + the candidate's registry meta from the request
 *              record: the exact evidence a later "save to my library" replays; without it the
 *              fetch origin and licence are unrecoverable once the staged file is all that is left)
 *   apply    --file <usage.tsx> [--line N --col N] --local <LocalName> --to <specifier|filePath> [--root R]
 *   revert   --file <usage.tsx> | --all [--local <LocalName>] [--root R]
 *   inspect  --file <usage.tsx> [--root R]
 *   props    --file <usage.tsx> --line N --local <Name> --candidate <staged.tsx> [--entry Name] [--root R]
 *            → prop-shape fit: required props the usage never passes (the swap WILL break), and
 *              props the candidate drops (the usage's variant/size silently stops meaning anything)
 *
 * Journal + backups live in <root>/.tryon/ — shared with the rest of the try-on tooling.
 * Proven on Next 16.3.6 + Turbopack: HMR applied a swap in ~114 ms with no server restart,
 * the original components/ui file is never written.
 */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { createRequire } from "node:module";

/* ------------------------------------------------------------------ typescript */
let _ts = null;
function loadTs(root) {
  if (_ts) return _ts;
  const candidates = [process.env.TRYON_TS_ROOT, root, process.cwd()].filter(Boolean);
  for (const c of candidates) {
    try { _ts = createRequire(path.join(c, "package.json"))("typescript"); } catch { /* try next */ }
    if (_ts) break;
  }
  if (!_ts) {
    try { _ts = createRequire(import.meta.url)("typescript"); } catch { /* fall through */ }
  }
  if (!_ts) throw new Error("TYPESCRIPT_NOT_FOUND: install typescript in the project (a devDependency of any TS Next app)");
  return _ts;
}

/* ------------------------------------------------------------------ helpers */
const sha = (t) => crypto.createHash("sha256").update(t, "utf8").digest("hex").slice(0, 16);
const now = () => new Date().toISOString();

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const k = a.slice(2);
      const v = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : true;
      out[k] = v;
    } else out._.push(a);
  }
  return out;
}

function parseFile(file, text) {
  const ts = _ts;
  const kind = /\.tsx$/.test(file) ? ts.ScriptKind.TSX
    : /\.jsx$/.test(file) ? ts.ScriptKind.JSX
    : ts.ScriptKind.TS;
  return ts.createSourceFile(file, text, ts.ScriptTarget.Latest, /*setParentNodes*/ true, kind);
}

/** All import bindings in a source file as flat descriptors. */
function descriptors(sf) {
  const ts = _ts;
  const out = [];
  for (const st of sf.statements) {
    if (!ts.isImportDeclaration(st)) continue;
    const spec = st.moduleSpecifier.getText(sf).slice(1, -1); // strip quotes
    const c = st.importClause;
    if (!c) { out.push({ kind: "sideeffect", local: "", imported: "", spec, typeOnly: false, decl: st, el: null }); continue; }
    const t = !!c.isTypeOnly;
    if (c.name) out.push({ kind: "default", local: c.name.text, imported: "default", spec, typeOnly: t, decl: st, el: null });
    const nb = c.namedBindings;
    if (nb && ts.isNamespaceImport(nb)) {
      out.push({ kind: "namespace", local: nb.name.text, imported: "*", spec, typeOnly: t, decl: st, el: null });
    } else if (nb && ts.isNamedImports(nb)) {
      for (const el of nb.elements) {
        out.push({
          kind: "named", local: el.name.text,
          imported: el.propertyName ? el.propertyName.text : el.name.text,
          spec, typeOnly: t || !!el.isTypeOnly, decl: st, el,
        });
      }
    }
  }
  return out;
}
const sigOf = (ds) => JSON.stringify(
  ds.map(({ kind, local, imported, spec, typeOnly }) => `${typeOnly ? "T" : ""}${kind}|${local}|${imported}|${spec}`).sort()
);

/** Pick the binding for `local` in scope at (line,col) — 1-based, optional. */
function findBinding(sf, local, line, col) {
  const all = descriptors(sf).filter((d) => d.local === local);
  if (all.length === 0) return null;
  if (all.length === 1 || !line) return all[0];
  const pos = sf.getPositionOfLineAndCharacter(Math.max(0, line - 1), Math.max(0, (col || 1) - 1));
  const before = all.filter((d) => d.decl.getStart(sf) < pos);
  return before.length ? before[before.length - 1] : all[0];
}

/** Remove one named element, keeping every other byte of the list untouched. */
function removalEdit(sf, decl, el) {
  const els = decl.importClause.namedBindings.elements;
  const i = els.indexOf(el);
  if (els.length === 1) throw new Error("removalEdit: sole element (use specifier-replace)");
  if (i < els.length - 1) return { start: el.getStart(sf), end: els[i + 1].getStart(sf), text: "" };
  return { start: els[i - 1].getEnd(), end: el.getEnd(), text: "" };
}

const lineEndAfter = (text, pos) => { const i = text.indexOf("\n", pos); return i === -1 ? text.length : i + 1; };
const lineStartOf = (text, pos) => text.lastIndexOf("\n", pos - 1) + 1;
const indentOf = (text, pos) => text.slice(lineStartOf(text, pos), pos).replace(/\S.*$/, "");
const quoteOf = (text, decl) => text[decl.moduleSpecifier.getStart()];
const elementText = (d) => `${d.typeOnly && d.kind === "named" ? "type " : ""}${d.imported === d.local ? d.imported : `${d.imported} as ${d.local}`}`;

function applyEdits(text, edits) {
  const sorted = [...edits].sort((a, b) => b.start - a.start);
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i].end > sorted[i - 1].start) throw new Error("overlapping edits");
  }
  let out = text;
  for (const e of sorted) out = out.slice(0, e.start) + e.text + out.slice(e.end);
  return out;
}

/* --------------------------------------------------------- specifier mapping */
function readAliases(root) {
  const ts = _ts;
  try {
    const raw = fs.readFileSync(path.join(root, "tsconfig.json"), "utf8");
    const j = ts.parseConfigFileTextToJson("tsconfig.json", raw).config || {};
    const co = j.compilerOptions || {};
    return { baseUrl: (co.baseUrl || ".").replace(/\\/g, "/"), paths: co.paths || {} };
  } catch { return { baseUrl: ".", paths: {} }; }
}

/** Windows-safe: file path (any separator) -> module specifier using tsconfig paths alias. */
export function fileToSpecifier(absFile, root, { stripExtension = true } = {}) {
  let rel = path.relative(root, absFile).split(path.sep).join("/");
  if (stripExtension) {
    const stripped = rel.replace(/\.(tsx?|jsx?|mjs|cjs)$/, "").replace(/\/index$/, "");
    if (stripped) rel = stripped;
  }
  const { baseUrl, paths } = readAliases(root);
  for (const [key, targets] of Object.entries(paths)) {
    const star = key.indexOf("*");
    if (star === -1) continue;
    const prefix = key.slice(0, star);
    const targetBase = path.posix.normalize(
      path.posix.join(baseUrl === "." ? "" : baseUrl, String(targets[0] ?? "").replace(/\*.*$/, "").replace(/\\/g, "/"))
    ).replace(/^\.\//, "").replace(/\/$/, "");
    if (targetBase === "." || targetBase === "") return prefix + rel;
    if (rel === targetBase || rel.startsWith(targetBase + "/")) return prefix + rel.slice(targetBase.length + 1);
  }
  const r = path.posix.relative(path.posix.dirname(rel), rel);
  return r.startsWith(".") ? r : "./" + r;
}

/** Accept either a real module specifier or a filesystem path (incl. Windows). */
export function toSpecifier(input, root) {
  const s = String(input);
  if (s.includes("\\")) return fileToSpecifier(path.resolve(root, s), root);
  if (/^\.{1,2}\//.test(s) || s.startsWith("@/") || s.startsWith("~/")) return s;
  if (/\.(tsx?|jsx?)$/.test(s)) return fileToSpecifier(path.resolve(root, s), root);
  if (path.isAbsolute(s)) return fileToSpecifier(s, root);
  return s;
}

/* --------------------------------------------------------------- the planner */
/** Plan the edit. Pure function of the CURRENT text — call again right before writing. */
export function planRepoint({ text, file, local, target, line, col, allowMerge = false }) {
  const sf = parseFile(file, text);
  const hit = findBinding(sf, local, line, col);
  if (!hit) return { changed: false, reason: "NO_IMPORT_FOR_LOCAL", local, file };
  const decl = hit.decl;
  const oldSpecifier = hit.spec;
  if (oldSpecifier === target) return { changed: false, reason: "ALREADY_AT_TARGET", oldSpecifier, local, file };
  if (hit.kind === "namespace") return { changed: false, reason: "UNSUPPORTED_NAMESPACE", oldSpecifier, local, file };

  const inDecl = descriptors(sf).filter((d) => d.decl === decl);
  const edits = [];
  let mode;

  const mkStatement = (t) =>
    `${indentOf(text, decl.getStart(sf))}import ${hit.kind === "default" ? "" : "{ "}${elementText(hit)}${hit.kind === "default" ? "" : " }"} from ${quoteOf(text, decl)}${t}${quoteOf(text, decl)};\n`;
  const insertAfterDecl = () => ({ start: lineEndAfter(text, decl.getEnd()), end: lineEndAfter(text, decl.getEnd()), text: mkStatement(target) });

  if (inDecl.length === 1) {
    mode = "specifier-replace";
    edits.push({ start: decl.moduleSpecifier.getStart(sf) + 1, end: decl.moduleSpecifier.getEnd() - 1, text: target });
  } else if (hit.kind === "named" && allowMerge) {
    const merge = descriptors(sf).find((d) => d.spec === target && d.decl !== decl && (d.kind === "named" || d.kind === "default" || d.kind === "namespace"));
    if (merge) {
      mode = "merge-into-existing-import";
      edits.push(removalEdit(sf, decl, hit.el));
      const nb = merge.decl.importClause.namedBindings;
      if (nb && _ts.isNamedImports(nb)) {
        const els = nb.elements;
        const braceStart = text.indexOf("{", nb.getStart(sf));
        if (els.length === 0) edits.push({ start: braceStart + 1, end: braceStart + 1, text: ` ${elementText(hit)} ` });
        else edits.push({ start: els[els.length - 1].getEnd(), end: els[els.length - 1].getEnd(), text: `, ${elementText(hit)}` });
      } else if (merge.decl.importClause.name) {
        edits.push({ start: merge.decl.importClause.name.getEnd(), end: merge.decl.importClause.name.getEnd(), text: `, { ${elementText(hit)} }` });
      } else {
        return { changed: false, reason: "MERGE_TARGET_UNSUPPORTED", oldSpecifier, local, file };
      }
    } else {
      mode = "import-split";
      edits.push(removalEdit(sf, decl, hit.el));
      edits.push(insertAfterDecl());
    }
  } else {
    mode = "import-split";
    if (hit.kind === "named") edits.push(removalEdit(sf, decl, hit.el));
    else {
      const nb = decl.importClause.namedBindings;
      edits.push({ start: hit.el ? hit.el.getStart(sf) : decl.importClause.name.getStart(sf), end: (nb ? nb.getStart(sf) : decl.importClause.name.getEnd()), text: "" });
    }
    edits.push(insertAfterDecl());
  }

  return { changed: true, mode, edits, oldSpecifier, target, local, file, diagsBefore: sf.parseDiagnostics.length, sf };
}

/** Verify the would-be text; throws with a code the caller can report. */
export function verifyEdit({ text, file, local, expectSpecifier, othersBefore }) {
  const ts = _ts;
  const sf = parseFile(file, text);
  if (sf.parseDiagnostics.length > 0) {
    const e = new Error("VERIFY_SYNTAX_ERROR");
    e.detail = sf.parseDiagnostics.slice(0, 3).map((d) => ts.flattenDiagnosticMessageText(d.messageText, " "));
    throw e;
  }
  const mine = descriptors(sf).filter((d) => d.local === local);
  if (mine.length !== 1) { const e = new Error(`VERIFY_BINDING_COUNT=${mine.length}`); throw e; }
  if (mine[0].spec !== expectSpecifier) { const e = new Error(`VERIFY_SPECIFIER=${mine[0].spec}!=${expectSpecifier}`); throw e; }
  const othersAfter = sigOf(descriptors(sf).filter((d) => d.local !== local));
  if (othersAfter !== othersBefore) { const e = new Error("VERIFY_COLLATERAL_IMPORT_CHANGE"); e.detail = { before: othersBefore, after: othersAfter }; throw e; }
  return true;
}

/* ------------------------------------------------------------- file plumbing */
function writeAtomic(file, text) {
  const tmp = `${file}.tryon-tmp-${process.pid}`;
  fs.writeFileSync(tmp, text, "utf8");
  fs.renameSync(tmp, file);
}

const journalPath = (root) => path.join(root, ".tryon", "journal.json");
function readJournal(root) { try { return JSON.parse(fs.readFileSync(journalPath(root), "utf8")); } catch { return []; } }
function writeJournal(root, j) { fs.mkdirSync(path.dirname(journalPath(root)), { recursive: true }); fs.writeFileSync(journalPath(root), JSON.stringify(j, null, 2)); }

function manifestPath(root) { return path.join(root, ".tryon", "manifest.json"); }
function readManifest(root) {
  try {
    const v = JSON.parse(fs.readFileSync(manifestPath(root), "utf8"));
    return Array.isArray(v) ? v : [];
  } catch {
    // never silently drop a record: move an unreadable file aside, then start a fresh list
    try { if (fs.existsSync(manifestPath(root))) fs.renameSync(manifestPath(root), manifestPath(root) + ".broken-" + Date.now()); } catch { /* keep going */ }
    return [];
  }
}
function writeManifest(root, m) { fs.mkdirSync(path.dirname(manifestPath(root)), { recursive: true }); writeAtomic(manifestPath(root), JSON.stringify(m, null, 2)); }

/* --------------------------------------------------------- prop-shape fit check */
/**
 * Compare the props the owner's JSX passes at `line` with the props the candidate accepts.
 * Uses the project's own TypeScript — the check the guard cannot do without type info.
 *   missing_required: props the candidate REQUIRES that the usage never passes → the swap breaks
 *   dropped:          props the usage passes that the candidate does not accept → variant/size
 *                     silently stops meaning anything (reported, never silently ignored)
 * Verdicts: "fit" | "missing-required-props" | "unverifiable" (imported/generic props type, or spread)
 */
export function inspectProps({ root, file, line, local, candidate, entry }) {
  loadTs(root);
  const ts = _ts;
  const abs = path.resolve(root, file);
  const usageSf = parseFile(abs, fs.readFileSync(abs, "utf8"));
  const wantLine = Number(line) || 0;

  // 1. the JSX usage of `local` at/after the stamped line (nearest wins)
  let target = null;
  const walk = (node) => {
    const isEl = ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node);
    if (isEl) {
      const open = ts.isJsxElement(node) ? node.openingElement : node;
      const tag = open.tagName.getText(usageSf);
      const startLine = usageSf.getLineAndCharacterOfPosition(node.getStart(usageSf)).line + 1;
      if (tag === local && startLine >= Math.max(1, wantLine - 1)) {
        if (!target || Math.abs(startLine - wantLine) < Math.abs(target.startLine - wantLine)) {
          target = { node, open, tag, startLine };
        }
      }
    }
    ts.forEachChild(node, walk);
  };
  walk(usageSf);
  if (!target) {
    return { ok: true, verdict: "unverifiable", local, reason: "NO_USAGE_AT_LINE",
             detail: `no <${local}> found at/after line ${wantLine} in ${path.basename(abs)}` };
  }
  const usageProps = [];
  let hasSpread = false;
  for (const a of target.open.attributes.properties) {
    if (ts.isJsxAttribute(a)) usageProps.push(a.name.getText(usageSf));
    else hasSpread = true;
  }

  // 2. the candidate's props: resolve the first parameter's type IN ITS OWN FILE
  const candAbs = path.resolve(root, candidate);
  const candSf = parseFile(candAbs, fs.readFileSync(candAbs, "utf8"));
  const mods = (n) => (ts.canHaveModifiers(n) ? (ts.getModifiers(n) || []).map((m) => m.kind) : []);
  const decls = new Map();               // local name -> function/arrow node
  const exportedNames = new Set();
  let defaultDecl = null;
  for (const st of candSf.statements) {
    if (ts.isFunctionDeclaration(st) && st.name) {
      const ms = mods(st);
      decls.set(st.name.text, st);
      if (ms.includes(ts.SyntaxKind.ExportKeyword)) exportedNames.add(st.name.text);
      if (ms.includes(ts.SyntaxKind.DefaultKeyword)) defaultDecl = st.name.text;
    } else if (ts.isVariableStatement(st)) {
      const ms = mods(st);
      for (const d of st.declarationList.declarations) {
        if (ts.isIdentifier(d.name) && d.initializer && (ts.isArrowFunction(d.initializer) || ts.isFunctionExpression(d.initializer))) {
          const inner = (ts.getModifiers(d.initializer) || []).map((m) => m.kind);   // `export default () => …`
          decls.set(d.name.text, d.initializer);
          if (ms.includes(ts.SyntaxKind.ExportKeyword)) exportedNames.add(d.name.text);
          if (ms.includes(ts.SyntaxKind.DefaultKeyword) || inner.includes(ts.SyntaxKind.DefaultKeyword)) defaultDecl = d.name.text;
        }
      }
    } else if (ts.isExportDeclaration(st) && st.exportClause && ts.isNamedExports(st.exportClause) && !st.moduleSpecifier) {
      for (const e of st.exportClause.elements) exportedNames.add(e.name.text);     // `export { Button, buttonVariants }`
    } else if (ts.isExportAssignment(st) && ts.isIdentifier(st.expression)) {
      defaultDecl = st.expression.text;
    }
  }
  let comp = null, foundEntry = null;
  if (entry && decls.has(entry)) { comp = decls.get(entry); foundEntry = entry; }
  else if (defaultDecl && decls.has(defaultDecl)) { comp = decls.get(defaultDecl); foundEntry = defaultDecl; }
  else {
    const named = [...decls.keys()].filter((n) => exportedNames.has(n));
    if (named.length) { comp = decls.get(named[0]); foundEntry = named[0]; }
  }
  if (!comp) {
    return { ok: true, verdict: "unverifiable", local, reason: "NO_COMPONENT_FOUND",
             detail: `no exported component ${entry ? `"${entry}"` : ""} in ${path.basename(candAbs)}` };
  }

  const findTypeDecl = (sf, name) => {
    for (const st of sf.statements) {
      if (ts.isInterfaceDeclaration(st) && st.name.text === name) return st;
      if (ts.isTypeAliasDeclaration(st) && st.name.text === name) return st;
    }
    return null;
  };
  const collect = (members, sf) => {
    const req = [], acc = [], seen = { req: new Set(), acc: new Set() };
    let loose = false;
    const add = (name, required) => {
      if (name === "children" && !required) { acc.push(name); return; }        // children is implicit
      if (required && !seen.req.has(name)) { req.push(name); seen.req.add(name); }
      if (!seen.acc.has(name)) { acc.push(name); seen.acc.add(name); }
    };
    for (const m of members) {
      if (ts.isIndexSignatureDeclaration(m)) { loose = true; continue; }
      if (ts.isPropertySignature(m) || ts.isMethodSignature(m)) {
        const nm = m.name && m.name.getText(sf);
        if (!nm) continue;
        add(nm.replace(/["']/g, ""), !m.questionToken);
      }
    }
    return { req, acc, loose };
  };
  const cvaVariants = (sf, name) => {
    for (const st of sf.statements) {
      if (!ts.isVariableStatement(st)) continue;
      for (const d of st.declarationList.declarations) {
        if (!ts.isIdentifier(d.name) || d.name.text !== name) continue;
        const call = d.initializer;
        if (!call || !ts.isCallExpression(call)) continue;
        const cfg = call.arguments.find((a) => ts.isObjectLiteralExpression(a));
        if (!cfg) continue;
        const v = cfg.properties.find((p) => ts.isPropertyAssignment(p) && p.name.getText(sf) === "variants");
        if (!v || !ts.isObjectLiteralExpression(v.initializer)) continue;
        return v.initializer.properties
          .map((p) => (p.name && p.name.getText(sf) || "").replace(/["']/g, ""))
          .filter(Boolean);
      }
    }
    return null;
  };
  const merge = (parts) => {
    const out = { req: [], acc: [], loose: false };
    for (const p of parts) {
      const seen = new Set(out.acc);
      for (const r of p.req) if (!seen.has(r)) out.req.push(r);
      for (const a of p.acc) if (!seen.has(a) && !out.req.includes(a)) out.acc.push(a);
      out.loose = out.loose || p.loose;
    }
    return out;
  };
  const membersOf = (t, sf, depth = 0) => {
    if (!t || depth > 3) return null;
    if (ts.isInterfaceDeclaration(t)) {
      const parts = [collect(t.members, sf)];
      for (const h of t.heritageClauses || []) {
        for (const ty of h.types) {
          const p = membersOf(ty, sf, depth + 1);
          if (!p) return null;                                   // extended type not resolvable here
          parts.push(p);
        }
      }
      return parts.length === 1 ? parts[0] : merge(parts);
    }
    if (ts.isTypeAliasDeclaration(t)) return membersOf(t.type, sf, depth + 1);
    if (ts.isParenthesizedTypeNode(t)) return membersOf(t.type, sf, depth + 1);
    if (ts.isTypeReferenceNode(t)) {
      const nm = t.typeName.getText(sf);
      if (/(^|\.)VariantProps$/.test(nm)) {
        // VariantProps<typeof x>: cva variants are optional by definition — resolve their names
        // from the cva() call in this very file (the dominant registry shape)
        const arg = t.typeArguments && t.typeArguments[0];
        if (arg && ts.isTypeQueryNode(arg)) {
          const vs = cvaVariants(sf, arg.exprName.getText(sf));
          if (vs) return { req: [], acc: vs, loose: false };
        }
        return null;
      }
      const decl = findTypeDecl(sf, t.typeName.getText(sf));
      if (!decl) {
        const nm = t.typeName.getText(sf);
        // native-element props (React.ComponentProps<"button">, ButtonHTMLAttributes, …): the exact set
        // is not enumerable here, so nothing is ever "missing" and extras are treated as unknown.
        if (/(ComponentProps|ComponentPropsWithoutRef|ComponentPropsWithRef|HTMLAttributes|SVGProps)$/.test(nm)) {
          return { req: [], acc: [], loose: true };
        }
        return null;                                                // imported type → unverifiable
      }
      return membersOf(decl, sf, depth + 1);
    }
    if (ts.isTypeLiteralNode(t)) return collect(t.members, sf);
    if (ts.isIntersectionTypeNode(t)) {
      const parts = t.types.map((x) => membersOf(x, sf, depth + 1));
      if (parts.some((p) => p === null)) return null;
      return merge(parts);
    }
    return null;
  };
  const param = comp.parameters && comp.parameters[0];
  const propsInfo = param ? membersOf(param.type, candSf) : { req: [], acc: [], loose: false };
  const resolvable = !!propsInfo;
  const info = propsInfo || { req: [], acc: [], loose: true };

  const missing = resolvable && !hasSpread ? info.req.filter((p) => !usageProps.includes(p)) : [];
  const dropped = resolvable && !info.loose ? usageProps.filter((p) => !info.acc.includes(p)) : [];
  return {
    ok: missing.length === 0,
    verdict: !resolvable ? "unverifiable" : (missing.length ? "missing-required-props" : "fit"),
    local, entry: foundEntry,
    usage: { file: abs, line: target.startLine, props: usageProps, hasSpread },
    candidate: { file: candAbs, resolvable, required: info.req, accepts: info.acc, loose: !!info.loose },
    missing_required: missing, dropped,
  };
}

/* ---------------------------------------------------------------- operations */
export function applySwap({ root, file, local, to, line, col }) {
  loadTs(root);
  const abs = path.resolve(root, file);
  const target = toSpecifier(to, root);
  const text0 = fs.readFileSync(abs, "utf8");
  const plan = planRepoint({ text: text0, file: abs, local, target, line, col });
  if (!plan.changed) {
    // an impossible request is NOT a success: only ALREADY_AT_TARGET is an honest no-op
    return { ok: plan.reason === "ALREADY_AT_TARGET", changed: false, reason: plan.reason, file: abs, local, target };
  }

  const othersBefore = sigOf(descriptors(plan.sf).filter((d) => d.local !== local));
  const text1 = applyEdits(text0, plan.edits);
  verifyEdit({ text: text1, file: abs, local, expectSpecifier: target, othersBefore });

  const tWrite = now();
  writeAtomic(abs, text1);
  const back = fs.readFileSync(abs, "utf8");
  verifyEdit({ text: back, file: abs, local, expectSpecifier: target, othersBefore });

  const j = readJournal(root);
  const backupRel = path.join(".tryon", "backups", `${Date.now()}-${sha(text0)}-${path.basename(abs)}.bak`);
  fs.mkdirSync(path.dirname(path.join(root, backupRel)), { recursive: true });
  fs.writeFileSync(path.join(root, backupRel), text0, "utf8");
  j.push({ id: j.length, ts: tWrite, file: path.relative(root, abs).split(path.sep).join("/"), local, from: plan.oldSpecifier, to: target, mode: plan.mode, shaBefore: sha(text0), shaAfter: sha(text1), backup: backupRel.split(path.sep).join("/") });
  writeJournal(root, j);

  return { ok: true, changed: true, mode: plan.mode, file: abs, local, from: plan.oldSpecifier, to: target, tWrite, shaBefore: sha(text0), shaAfter: sha(text1) };
}

export function revertSwap({ root, file, local, all = false, restoreBackupIfUntouched = true }) {
  loadTs(root);
  const abs = file ? path.resolve(root, file) : null;
  const j = readJournal(root);
  let entries = j.map((e, i) => ({ e, i })).filter(({ e }) => (all || e.file === (abs ? path.relative(root, abs).split(path.sep).join("/") : null)) && (!local || e.local === local));
  if (entries.length === 0) return { ok: false, reason: "NO_JOURNAL_ENTRY", file, local };
  entries.reverse();
  const results = [];
  const drop = [];
  for (const { e, i } of entries) {
    const p = path.join(root, e.file);
    const cur = fs.readFileSync(p, "utf8");
    const othersBefore = sigOf(descriptors(parseFile(p, cur)).filter((d) => d.local !== e.local));
    let text1, mode;
    if (restoreBackupIfUntouched && sha(cur) === e.shaAfter) {
      const bak = fs.readFileSync(path.join(root, e.backup), "utf8");
      if (sha(bak) !== e.shaBefore) throw new Error("BACKUP_HASH_MISMATCH");
      text1 = bak;
      mode = "byte-exact-restore";
      verifyEdit({ text: text1, file: p, local: e.local, expectSpecifier: e.from, othersBefore });
    } else {
      const plan = planRepoint({ text: cur, file: p, local: e.local, target: e.from, allowMerge: true });
      if (!plan.changed) {
        if (plan.reason === "ALREADY_AT_TARGET") { results.push({ ok: true, changed: false, reason: plan.reason, file: p, local: e.local }); drop.push(i); continue; }
        throw new Error(`REVERT_PLAN_FAILED:${plan.reason}`);
      }
      text1 = applyEdits(cur, plan.edits);
      mode = `re-derived(${plan.mode})`;
      verifyEdit({ text: text1, file: p, local: e.local, expectSpecifier: e.from, othersBefore });
    }
    writeAtomic(p, text1);
    const back = fs.readFileSync(p, "utf8");
    verifyEdit({ text: back, file: p, local: e.local, expectSpecifier: e.from, othersBefore });
    results.push({ ok: true, changed: true, mode, file: p, local: e.local, from: e.to, to: e.from, sha: sha(text1) });
    drop.push(i);
  }
  writeJournal(root, j.filter((_, i) => !drop.includes(i)));
  return { ok: true, results };
}

export function installVariant({ root, from, slot, entry, as, request, meta }) {
  loadTs(root);
  const ts = _ts;
  const src = path.resolve(root, from);
  const slotDir = path.join(root, "components", "variants", slot);
  fs.mkdirSync(slotDir, { recursive: true });
  const text = fs.readFileSync(src, "utf8");
  const sf = parseFile(src, text);
  const exportNames = (() => {
    const names = [];
    const visit = (n) => {
      const mods = ts.canHaveModifiers(n) ? ts.getModifiers(n) || [] : [];
      const isExport = mods.some((m) => m.kind === ts.SyntaxKind.ExportKeyword);
      if (isExport && ts.isFunctionDeclaration(n)) { if (n.name) names.push(n.name.text); }
      else if (isExport && ts.isClassDeclaration(n)) { if (n.name) names.push(n.name.text); }
      else if (isExport && ts.isVariableStatement(n)) { for (const d of n.declarationList.declarations) if (ts.isIdentifier(d.name)) names.push(d.name.text); }
      else if (ts.isExportDeclaration(n) && n.exportClause && ts.isNamedExports(n.exportClause)) { for (const el of n.exportClause.elements) names.push(el.name.text); }
      ts.forEachChild(n, visit);
    };
    visit(sf);
    return names;
  })();
  if (!exportNames.includes(entry)) return { ok: false, reason: "ENTRY_EXPORT_NOT_FOUND", entry, from: src, exportsFound: exportNames };
  const ext = path.extname(src) || ".tsx";
  const kebab = String(entry).replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase();
  const dest = path.join(slotDir, as ? String(as) : `${kebab}${ext}`);
  writeAtomic(dest, text);
  // Stage-time evidence: after this point the staged file is the only thing on disk, and the fetch
  // origin + licence + base would be unrecoverable. One entry per install, idempotent-ish (append).
  const man = readManifest(root);
  man.push({
    at: now(),
    request: request != null && request !== true ? Number(request) : null,
    slot: slot ?? null,
    entry,
    dest: path.relative(root, dest).split(path.sep).join("/"),
    specifier: fileToSpecifier(dest, root),
    sha: sha(text),
    source: (meta && meta.item_url) || null,
    candidate: meta ? {
      registry: meta.registry ?? null, item: meta.item ?? null, style: meta.style ?? null,
      base: meta.base ?? null, type: meta.type ?? null, title: meta.title ?? null,
      license: meta.license ?? null, license_evidence: meta.license_evidence ?? null,
      item_url: meta.item_url ?? null,
    } : null,
  });
  writeManifest(root, man);
  return { ok: true, dest, specifier: fileToSpecifier(dest, root), entry, sha: sha(text),
           exportsFound: exportNames, manifest: ".tryon/manifest.json" };
}

/* ---------------------------------------------------------------------- CLI */
const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"));
if (isMain) {
  const a = parseArgs(process.argv.slice(2));
  const cmd = a._[0];
  const root = path.resolve(a.root || process.cwd());
  // a flag that this command does not use is an error, never silently ignored
  const KNOWN = { apply: ["file", "line", "col", "local", "to", "root"],
                  revert: ["file", "all", "local", "root"],
                  install: ["from", "slot", "entry", "as", "root", "request", "meta-file"],
                  inspect: ["file", "root"],
                  props: ["file", "line", "local", "candidate", "entry", "root"] };
  const bad = Object.keys(a).filter((k) => k !== "_" && (KNOWN[cmd] || []).indexOf(k) === -1);
  if (cmd && bad.length) {
    console.log(JSON.stringify({ ok: false, reason: "USAGE", detail: "flag --" + bad[0] + " is not used by '" + cmd + "'" }));
    process.exit(2);
  }
  try {
    loadTs(root);
    let out;
    if (cmd === "apply") out = applySwap({ root, file: a.file, local: a.local, to: a.to, line: a.line && Number(a.line), col: a.col && Number(a.col) });
    else if (cmd === "revert") out = revertSwap({ root, file: a.all ? null : a.file, local: a.local, all: !!a.all });
    else if (cmd === "install") {
      let meta = null, request = a.request;
      if (a["meta-file"]) {
        // the request record from requests.jsonl (or the candidate object itself): what is left of
        // the fetch origin and licence once the staged file is the only thing on disk
        const raw = JSON.parse(fs.readFileSync(path.resolve(root, String(a["meta-file"])), "utf8"));
        if (raw && typeof raw === "object" && raw.candidate) { meta = raw.candidate; request = request ?? raw.request; }
        else meta = raw;
        if (!meta || typeof meta !== "object") throw new Error("META_FILE_BAD: expected the request object or a candidate object");
      }
      out = installVariant({ root, from: a.from, slot: a.slot, entry: a.entry, as: a.as, request, meta });
    }
    else if (cmd === "props") out = inspectProps({ root, file: a.file, line: a.line && Number(a.line), local: a.local, candidate: a.candidate, entry: a.entry });
    else if (cmd === "inspect") {
      const abs = path.resolve(root, a.file);
      const sf = parseFile(abs, fs.readFileSync(abs, "utf8"));
      out = { ok: true, file: abs, bindings: descriptors(sf).map(({ kind, local, imported, spec, typeOnly }) => ({ kind, local, imported, spec, typeOnly })) };
    } else { console.log(JSON.stringify({ ok: false, reason: "USAGE" })); process.exit(2); }
    console.log(JSON.stringify(out));
    process.exit(out.ok === false ? 1 : 0);
  } catch (err) {
    console.log(JSON.stringify({ ok: false, error: String(err.message || err), detail: err.detail ?? null }));
    process.exit(1);
  }
}
