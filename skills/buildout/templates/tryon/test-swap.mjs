#!/usr/bin/env node
/**
 * test-swap.mjs — the codemod battery, re-run against the shipped swap.mjs.
 *
 * Needs `typescript` resolvable from --ts-root (or TS_ROOT env): point it at any project that has
 * typescript installed (a Next app does). Everything else happens in a throwaway temp dir.
 *
 *   node templates/tryon/test-swap.mjs --ts-root C:/path/to/next-app
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const args = process.argv.slice(2);
const tsRoot = (args.includes("--ts-root") ? args[args.indexOf("--ts-root") + 1] : process.env.TS_ROOT) || process.cwd();
process.env.TRYON_TS_ROOT = tsRoot;

const here = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1").replace(/^\/([A-Za-z]:)/, "$1"));
const swap = await import(pathToFileURL(path.join(here, "swap.mjs")).href);

const ROOT = fs.mkdtempSync(path.join(os.tmpdir(), "tryon-swap-"));
fs.writeFileSync(path.join(ROOT, "tsconfig.json"),
  JSON.stringify({ compilerOptions: { baseUrl: ".", paths: { "@/*": ["./*"] } } }));

let pass = 0, fail = 0;
function ok(cond, name, detail) {
  if (cond) { pass++; console.log("  ok  " + name); }
  else { fail++; console.log("  FAIL " + name + (detail ? "  :: " + detail : "")); }
}
function fixture(name, text) {
  const rel = `app/${name}.tsx`;
  const abs = path.join(ROOT, rel);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, text);
  return { rel, abs, text };
}
const read = (p) => fs.readFileSync(p, "utf8");
const TARGET = "@/components/variants/button/button";

// typescript must resolve from the project root we were pointed at
if (!fs.existsSync(path.join(tsRoot, "package.json"))) {
  console.error("no package.json under --ts-root " + tsRoot);
  process.exit(2);
}
process.env.NODE_PATH = path.join(tsRoot, "node_modules");

try {
  // 1. sole binding -> specifier replace + byte-exact revert
  {
    const f = fixture("sole", 'import { Button } from "@/components/ui/button";\n\nexport function P() {\n  return <Button>Save</Button>;\n}\n');
    const a = swap.applySwap({ root: ROOT, file: f.rel, local: "Button", to: TARGET });
    ok(a.ok && a.changed && a.mode === "specifier-replace", "sole binding -> specifier-replace", JSON.stringify(a));
    ok(read(f.abs).includes(`from "${TARGET}"`), "specifier actually written");
    const r = swap.revertSwap({ root: ROOT, file: f.rel });
    ok(r.ok && r.results[0].mode === "byte-exact-restore" && read(f.abs) === f.text, "revert restores bytes exactly");
  }

  // 2. aliased import keeps the alias
  {
    const f = fixture("aliased", 'import { Button as Btn } from "@/components/ui/button";\n\nexport function A() {\n  return <Btn>Go</Btn>;\n}\n');
    const a = swap.applySwap({ root: ROOT, file: f.rel, local: "Btn", to: TARGET });
    ok(a.ok && a.changed, "aliased local resolves", JSON.stringify(a));
    ok(read(f.abs).includes(`from "${TARGET}"`) && read(f.abs).includes("Button as Btn"), "alias survives the swap");
    swap.revertSwap({ root: ROOT, file: f.rel });
    ok(read(f.abs) === f.text, "aliased revert byte-exact");
  }

  // 3. multiline import, several named bindings -> import-split, siblings untouched
  {
    const f = fixture("multi", 'import {\n  Button,\n  Card,\n  Badge,\n} from "@/components/ui/multi";\n\nexport function M() {\n  return <Button>B</Button>;\n}\n');
    const a = swap.applySwap({ root: ROOT, file: f.rel, local: "Button", to: TARGET });
    const now = read(f.abs);
    ok(a.ok && a.changed && a.mode === "import-split", "multiline -> import-split", JSON.stringify(a.mode));
    ok(now.includes("Card") && now.includes("Badge"), "sibling bindings untouched");
    ok(new RegExp('import \\{ Button \\} from "' + TARGET.replace(/[/@]/g, (m) => "\\" + m) + '"').test(now), "one new import line added");
    swap.revertSwap({ root: ROOT, file: f.rel });
    ok(read(f.abs) === f.text, "multiline revert byte-exact");
  }

  // 4. unrelated import in the same file is byte-identical after the swap
  {
    const f = fixture("unrelated", 'import { Panel } from "@/components/ui/panel";\nimport { Button } from "@/components/ui/button";\n\nexport function U() {\n  return (<div><Panel /><Button>x</Button></div>);\n}\n');
    const before = read(f.abs).split("\n")[0];
    swap.applySwap({ root: ROOT, file: f.rel, local: "Button", to: TARGET });
    ok(read(f.abs).split("\n")[0] === before, "unrelated import line byte-identical");
    swap.revertSwap({ root: ROOT, file: f.rel });
  }

  // 5. default import
  {
    const f = fixture("def", 'import Button from "@/components/ui/button";\n\nexport function D() {\n  return <Button>d</Button>;\n}\n');
    const a = swap.applySwap({ root: ROOT, file: f.rel, local: "Button", to: TARGET });
    ok(a.ok && a.changed && a.mode === "specifier-replace", "default import swaps");
    swap.revertSwap({ root: ROOT, file: f.rel });
  }

  // 6. windows separators accepted for --to (path -> specifier)
  {
    const f = fixture("winpath", 'import { Button } from "@/components/ui/button";\n\nexport function W() {\n  return <Button>w</Button>;\n}\n');
    const to = path.join(ROOT, "components", "variants", "button", "button.tsx").replace(/\//g, "\\");
    const a = swap.applySwap({ root: ROOT, file: f.rel, local: "Button", to });
    ok(a.ok && a.changed && a.to === TARGET, "windows path normalises to the same specifier", a.to);
    swap.revertSwap({ root: ROOT, file: f.rel });
  }

  // 7. refusal: no binding for the local name — file untouched
  {
    const f = fixture("missing", 'import { Button } from "@/components/ui/button";\n\nexport function X() {\n  return <Button>x</Button>;\n}\n');
    const a = swap.applySwap({ root: ROOT, file: f.rel, local: "Nope", to: TARGET });
    ok(a.ok === false && a.changed === false && a.reason === "NO_IMPORT_FOR_LOCAL" && read(f.abs) === f.text,
      "unknown local refuses with NO_IMPORT_FOR_LOCAL, not ok, and no write");
  }

  // 8. idempotence
  {
    const f = fixture("idem", 'import { Button } from "@/components/ui/button";\n\nexport function I() {\n  return <Button>i</Button>;\n}\n');
    swap.applySwap({ root: ROOT, file: f.rel, local: "Button", to: TARGET });
    const b = swap.applySwap({ root: ROOT, file: f.rel, local: "Button", to: TARGET });
    ok(b.ok && b.changed === false && b.reason === "ALREADY_AT_TARGET", "second apply is a no-op");
    swap.revertSwap({ root: ROOT, file: f.rel });
  }

  // 9. drift revert: owner edits the file after the swap; revert re-derives and keeps the edit
  {
    const f = fixture("drift", 'import { Button } from "@/components/ui/button";\n\nexport function R() {\n  return <Button>r</Button>;\n}\n');
    swap.applySwap({ root: ROOT, file: f.rel, local: "Button", to: TARGET });
    fs.writeFileSync(f.abs, read(f.abs) + "// owner edit\n");
    const r = swap.revertSwap({ root: ROOT, file: f.rel });
    const now = read(f.abs);
    ok(r.ok && /re-derived/.test(r.results[0].mode || ""), "drifted revert re-derives", JSON.stringify(r.results));
    ok(now === f.text + "// owner edit\n", "owner edit preserved, specifier restored");
  }

  // 10. variant install: export check, dest path, specifier; and the refusal path
  {
    const src = path.join(ROOT, "components", "variants-src", "pink.tsx");
    fs.mkdirSync(path.dirname(src), { recursive: true });
    fs.writeFileSync(src, "export function Button({ children }) { return <button data-v=\"pink\">{children}</button>; }\n");
    const a = swap.installVariant({ root: ROOT, from: src, slot: "button", entry: "Button" });
    ok(a.ok && a.specifier === TARGET && fs.existsSync(a.dest), "installVariant stages and maps the specifier", JSON.stringify(a));
    const b = swap.installVariant({ root: ROOT, from: src, slot: "button", entry: "Nope" });
    ok(b.ok === false && b.reason === "ENTRY_EXPORT_NOT_FOUND" && b.exportsFound.includes("Button"),
      "installVariant refuses an entry the file does not export");
  }
  // 11. prop-shape fit (inspectProps): the check that needs the project's own type info
  {
    const candDir = path.join(ROOT, "components", "variants", "button");
    fs.mkdirSync(candDir, { recursive: true });
    const requires = path.join(candDir, "requires.tsx");
    fs.writeFileSync(requires, 'export interface BtnProps { children?: React.ReactNode; label: string }\nexport default function Btn({ children, label }: BtnProps) { return <button>{label}{children}</button>; }\n');
    const f1 = fixture("props-a", 'import { Button } from "@/components/ui/button";\n\nexport function A() {\n  return <Button variant="outline">Go</Button>;\n}\n');
    const r1 = swap.inspectProps({ root: ROOT, file: f1.rel, line: 4, local: "Button", candidate: "components/variants/button/requires.tsx", entry: "Btn" });
    ok(r1.ok === false && r1.verdict === "missing-required-props" && r1.missing_required.includes("label"),
      "props: candidate requiring a prop the usage never passes is refused", JSON.stringify(r1));

    const drops = path.join(candDir, "drops.tsx");
    fs.writeFileSync(drops, 'export function Card({ children, variant }: { children?: any; variant?: string }) { return <div data-v={variant}>{children}</div>; }\n');
    const f2 = fixture("props-b", 'import { Button } from "@/components/ui/button";\n\nexport function B() {\n  return <Button variant="outline" size="sm">Go</Button>;\n}\n');
    const r2 = swap.inspectProps({ root: ROOT, file: f2.rel, line: 4, local: "Button", candidate: "components/variants/button/drops.tsx", entry: "Card" });
    ok(r2.ok === true && r2.verdict === "fit" && r2.dropped.includes("size"),
      "props: props the candidate drops are reported (variant/size must never vanish silently)", JSON.stringify(r2));

    const ext = path.join(candDir, "external.tsx");
    fs.writeFileSync(ext, 'import type { P } from "./p";\nexport default function X(p: P) { return null; }\n');
    const f3 = fixture("props-c", 'import { Button } from "@/components/ui/button";\n\nexport function C() {\n  return <Button>Go</Button>;\n}\n');
    const r3 = swap.inspectProps({ root: ROOT, file: f3.rel, line: 4, local: "Button", candidate: "components/variants/button/external.tsx" });
    ok(r3.ok === true && r3.verdict === "unverifiable",
      "props: an imported props type is honestly unverifiable (not a fake pass, not a fake refusal)", JSON.stringify(r3));

    const f4 = fixture("props-d", 'import { Button } from "@/components/ui/button";\n\nexport function D() {\n  return <Button {...rest}>Go</Button>;\n}\n');
    const r4 = swap.inspectProps({ root: ROOT, file: f4.rel, line: 4, local: "Button", candidate: "components/variants/button/requires.tsx", entry: "Btn" });
    ok(r4.ok === true && r4.usage.hasSpread === true && r4.missing_required.length === 0,
      "props: a spread usage cannot be judged missing — reported as spread, not refused", JSON.stringify(r4));

    // the classic shadcn shape: plain declarations + a named export list at the bottom
    const shadcnish = path.join(candDir, "shadcnish.tsx");
    fs.writeFileSync(shadcnish, 'function Button({ className, icon }: { className?: string; icon: React.ReactNode }) { return <button className={className}>{icon}</button>; }\nfunction buttonVariants() { return ""; }\nexport { Button, buttonVariants };\n');
    const f5 = fixture("props-e", 'import { Button } from "@/components/ui/button";\n\nexport function E() {\n  return <Button className="x">Go</Button>;\n}\n');
    const r5 = swap.inspectProps({ root: ROOT, file: f5.rel, line: 4, local: "Button", candidate: "components/variants/button/shadcnish.tsx", entry: "Button" });
    ok(r5.ok === false && r5.missing_required.includes("icon"),
      "props: export-list declarations are found (shadcn shape) and their required props enforced", JSON.stringify(r5));

    // React.ComponentProps<"x"> alone: never invents a missing prop, never reports a drop it cannot know
    const native = path.join(candDir, "native.tsx");
    fs.writeFileSync(native, 'function Btn(props: React.ComponentProps<"button">) { return <button {...props} />; }\nexport { Btn };\n');
    const r6 = swap.inspectProps({ root: ROOT, file: f5.rel, line: 4, local: "Button", candidate: "components/variants/button/native.tsx", entry: "Btn" });
    ok(r6.ok === true && r6.verdict === "fit" && r6.dropped.length === 0,
      "props: native props type → fit, and extras are not guessed as dropped", JSON.stringify(r6));

    // cva / VariantProps: the dominant registry shape resolves from the file's own cva() call
    const cvaCand = path.join(candDir, "cvaish.tsx");
    fs.writeFileSync(cvaCand, 'import { cva, type VariantProps } from "class-variance-authority";\nconst buttonVariants = cva("b", { variants: { variant: { ghost: "g" }, size: { sm: "s" } } });\nfunction Button({ className, ...p }: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { className?: string }) { return <button {...p} />; }\nexport { Button, buttonVariants };\n');
    const r7 = swap.inspectProps({ root: ROOT, file: f2.rel, line: 4, local: "Button", candidate: "components/variants/button/cvaish.tsx", entry: "Button" });
    ok(r7.ok === true && r7.verdict === "fit" && r7.candidate.accepts.includes("variant") && r7.candidate.accepts.includes("size") && r7.dropped.length === 0,
      "props: cva variants resolved (variant/size accepted) and native part keeps extras unknown", JSON.stringify(r7));
    const f6 = fixture("props-g", 'import { Button } from "@/components/ui/button";\n\nexport function G() {\n  return <Button variant="ghost" magnetRadius={3}>Go</Button>;\n}\n');
    const r8 = swap.inspectProps({ root: ROOT, file: f6.rel, line: 4, local: "Button", candidate: "components/variants/button/cvaish.tsx", entry: "Button" });
    ok(r8.dropped.includes("magnetRadius") === false && r8.candidate.loose === true,
      "props: a dropped-prop claim is never invented when part of the type is native/unknown", JSON.stringify(r8));
  }

  // 12. stage manifest: one entry per install, with the candidate's registry evidence
  {
    const src2 = path.join(ROOT, "components", "variants-src", "pink2.tsx");
    fs.mkdirSync(path.dirname(src2), { recursive: true });
    fs.writeFileSync(src2, "export function Button({ children }) { return <button data-v=\"pink2\">{children}</button>; }\n");
    const meta = { registry: "magicui", item: "glare-hover-demo-cta", style: "base-nova", base: "radix",
                   type: "registry:example", license: "MIT", license_evidence: "registry claim",
                   item_url: "https://magicui.design/r/glare-hover-demo-cta.json" };
    const a = swap.installVariant({ root: ROOT, from: src2, slot: "button", entry: "Button", request: 4, meta });
    ok(a.ok && a.manifest === ".tryon/manifest.json", "manifest: install reports where the record went", JSON.stringify(a));
    const man = JSON.parse(fs.readFileSync(path.join(ROOT, ".tryon", "manifest.json"), "utf8"));
    const e = man[man.length - 1];
    ok(e.request === 4 && e.slot === "button" && e.entry === "Button" && e.sha,
      "manifest: request+slot+entry+sha recorded", JSON.stringify(e));
    ok(e.dest.split(path.sep).join("/").startsWith("components/variants/button/") && e.specifier,
      "manifest: dest + specifier recorded");
    ok(e.source === meta.item_url && e.candidate && e.candidate.license === "MIT" &&
       e.candidate.license_evidence === "registry claim" && e.candidate.base === "radix",
      "manifest: fetch origin + licence evidence survive the stage (a save replays THIS)", JSON.stringify(e.candidate));
  }
} catch (e) {
  fail++;
  console.log("  FAIL (exception) " + (e && e.stack || e));
}

console.log(`\n${pass}/${pass + fail} assertions passed`);
process.exit(fail ? 1 : 0);
