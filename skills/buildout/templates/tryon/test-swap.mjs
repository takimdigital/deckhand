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
import { spawnSync } from "node:child_process";

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
// the apply-time export check (T02) needs a real target file on disk: every fixture below applies to it
fs.mkdirSync(path.join(ROOT, "components", "variants", "button"), { recursive: true });
fs.writeFileSync(path.join(ROOT, "components", "variants", "button", "button.tsx"),
  "export function Button({ children, ...p }: React.ComponentProps<\"button\">) { return <button {...p}>{children}</button>; }\nexport default Button;\n");

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

  // 6. a filesystem path is accepted for --to (path -> specifier). The absolute form runs on every
  //    platform; the backslash-separator form only means anything on Windows (a fabricated
  //    backslash path is not a POSIX path — caught by CI: it passed on the owner's box, failed on
  //    the Linux runner)
  {
    const mk = (name) => fixture(name, 'import { Button } from "@/components/ui/button";\n\nexport function W() {\n  return <Button>w</Button>;\n}\n');
    const abs = path.join(ROOT, "components", "variants", "button", "button.tsx");
    const f1 = mk("winpath");
    const a1 = swap.applySwap({ root: ROOT, file: f1.rel, local: "Button", to: abs });
    ok(a1.ok && a1.changed && a1.to === TARGET, "filesystem path normalises to the same specifier", a1.to);
    swap.revertSwap({ root: ROOT, file: f1.rel });
    if (process.platform === "win32") {
      const f2 = mk("winpath2");
      const a2 = swap.applySwap({ root: ROOT, file: f2.rel, local: "Button", to: abs.replace(/\//g, "\\") });
      ok(a2.ok && a2.changed && a2.to === TARGET, "backslash separators normalise on Windows", a2.to);
      swap.revertSwap({ root: ROOT, file: f2.rel });
    }
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
    ok(r3.ok === null && r3.verdict === "unverifiable",
      "props: an imported props type is honestly unverifiable (ok is null — not a pass, not a refusal)", JSON.stringify(r3));

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
  // 13. verify-stage (T03): the machine drift check — a save never compares a sha by hand
  {
    const srcV = path.join(ROOT, "components", "variants-src", "pink3.tsx");
    fs.mkdirSync(path.dirname(srcV), { recursive: true });
    fs.writeFileSync(srcV, "export function Button3({ children }) { return <button>{children}</button>; }\n");
    const inst = swap.installVariant({ root: ROOT, from: srcV, slot: "button", entry: "Button3", as: "pink3.tsx", request: 7 });
    ok(inst.ok, "verify-stage fixture: staged", JSON.stringify(inst));
    const v1 = swap.verifyStage({ root: ROOT, request: 7 });
    ok(v1.ok && v1.sha256 && v1.sha256.length === 64, "verify-stage: matching bytes → ok with a full sha256",
      JSON.stringify({ dest: v1 && v1.dest, len: v1 && v1.sha256 && v1.sha256.length }));
    fs.appendFileSync(path.join(ROOT, v1.dest), "\n");
    const v2 = swap.verifyStage({ root: ROOT, request: 7 });
    ok(v2.ok === false && v2.reason === "STAGE_DRIFT", "verify-stage: one appended byte → STAGE_DRIFT", JSON.stringify(v2));
    const cli = spawnSync(process.execPath, [path.join(here, "swap.mjs"), "verify-stage", "--root", ROOT, "--request", "7"],
      { cwd: ROOT, env: { ...process.env }, encoding: "utf8" });
    ok(cli.status === 1 && /STAGE_DRIFT/.test(String(cli.stdout)), "verify-stage CLI: exits 1 with STAGE_DRIFT",
      String(cli.status) + " " + String(cli.stdout).trim());
    const v3 = swap.verifyStage({ root: ROOT, request: 99 });
    ok(v3.ok === false && v3.reason === "NO_STAGE_RECORD", "verify-stage: unknown request → NO_STAGE_RECORD");
  }

  // 14. apply refuses a target that cannot satisfy the import (T02) — the export check runs BEFORE any write
  {
    const demoP = path.join(ROOT, "components", "variants", "button", "demo.tsx");
    fs.writeFileSync(demoP, "export function Demo() { return <button>Demo</button>; }\n");
    const f = fixture("t02-missing", 'import { Button } from "@/components/ui/button";\n\nexport function P() {\n  return <Button>x</Button>;\n}\n');
    const bad = swap.applySwap({ root: ROOT, file: f.rel, local: "Button", to: "components/variants/button/demo.tsx" });
    ok(bad.ok === false && bad.reason === "TARGET_EXPORT_MISSING" && bad.need === "Button" && read(f.abs) === f.text,
      "apply: target lacking the needed export refuses with TARGET_EXPORT_MISSING, no write", JSON.stringify(bad));
    const good = swap.applySwap({ root: ROOT, file: f.rel, local: "Button", to: "components/variants/button/demo.tsx", entry: "Demo" });
    ok(good.ok && good.changed && read(f.abs).split("\n")[0] === 'import { Demo as Button } from "@/components/variants/button/demo";',
      "apply --entry Demo: the import reads { Demo as Button }", read(f.abs).split("\n")[0]);
    const rev = swap.revertSwap({ root: ROOT, file: f.rel });
    ok(rev.ok && read(f.abs) === f.text, "apply --entry revert is byte-exact");
  }
  {
    const soleP = path.join(ROOT, "components", "variants", "button", "sole-default.tsx");
    fs.writeFileSync(soleP, "export default function SoleDemo() { return <button>s</button>; }\n");
    const f = fixture("t02-default", 'import { Button } from "@/components/ui/button";\n\nexport function P() {\n  return <Button>x</Button>;\n}\n');
    const a = swap.applySwap({ root: ROOT, file: f.rel, local: "Button", to: "components/variants/button/sole-default.tsx", entry: "default" });
    ok(a.ok && read(f.abs).split("\n")[0] === 'import Button from "@/components/variants/button/sole-default";',
      "apply --entry default: named import converted to a default import", read(f.abs).split("\n")[0]);
    const rev = swap.revertSwap({ root: ROOT, file: f.rel });
    ok(rev.ok && read(f.abs) === f.text, "apply --entry default revert is byte-exact");
  }

  // 15. prop-fit counts children + behaviour (T10)
  {
    const demo2 = path.join(ROOT, "components", "variants", "button", "demo-destructive.tsx");
    fs.writeFileSync(demo2, "export default function ButtonDemo() { return <Button>Button</Button>; }\n");
    const f = fixture("t10-demo", 'import { Button } from "@/components/ui/button";\n\nexport function P() {\n  return <Button onClick={() => {}}>Book this trip</Button>;\n}\n');
    const r = swap.inspectProps({ root: ROOT, file: f.rel, line: 4, local: "Button", candidate: "components/variants/button/demo-destructive.tsx" });
    ok(r.ok === false && r.verdict === "drops-content" && r.behaviour_dropped.includes("onClick") && r.children.passed === true,
      "props: a demo that drops content + onClick is refused (the old code said fit)", JSON.stringify(r));

    const f2 = fixture("t10-usage", 'import { Button } from "@/components/ui/button";\n\nexport function P() {\n  return <Button onClick={() => {}}>Book this trip</Button>;\n}\n');
    const r2 = swap.inspectProps({ root: ROOT, file: f2.rel, line: 4, local: "Button", candidate: "components/variants/button/native.tsx", entry: "Btn" });
    ok(r2.ok === true && r2.verdict === "fit" && r2.children.accepted === true && r2.behaviour_dropped.length === 0,
      "props: the real native-props component fits the same usage", JSON.stringify(r2));

    fs.writeFileSync(path.join(ROOT, "components", "variants", "button", "kids.tsx"),
      "export function Kids({ children }: { children?: React.ReactNode }) { return <div>{children}</div>; }\n");
    // a children-only usage: no behaviour props to muddy the verdict
    const f3 = fixture("t10-kids", 'import { Button } from "@/components/ui/button";\n\nexport function P() {\n  return <Button>Book this trip</Button>;\n}\n');
    const r3 = swap.inspectProps({ root: ROOT, file: f3.rel, line: 4, local: "Button", candidate: "components/variants/button/kids.tsx", entry: "Kids" });
    ok(r3.ok === true && r3.children.passed === true && r3.children.accepted === true,
      "props: a candidate rendering children fits the usage's content", JSON.stringify(r3));

    fs.writeFileSync(path.join(ROOT, "components", "variants", "button", "kids2.tsx"),
      "export function Kids2({ children, label }: { children: React.ReactNode; label: string }) { return <div>{label}{children}</div>; }\n");
    const r4 = swap.inspectProps({ root: ROOT, file: f3.rel, line: 4, local: "Button", candidate: "components/variants/button/kids2.tsx", entry: "Kids2" });
    ok(r4.ok === false && r4.missing_required.includes("label") && r4.missing_required.includes("children") === false,
      "props: required children satisfied by the JSX children — label still reported missing", JSON.stringify(r4));

    fs.writeFileSync(path.join(ROOT, "components", "variants", "button", "inter.tsx"),
      'import type { Extra } from "./extra";\nexport function BtnI(props: React.ComponentProps<"button"> & Extra) { return <button />; }\n');
    const r5 = swap.inspectProps({ root: ROOT, file: f3.rel, line: 4, local: "Button", candidate: "components/variants/button/inter.tsx", entry: "BtnI" });
    ok(r5.ok === null && r5.verdict === "unverifiable",
      "props: an unresolvable intersection is ok:null (neither pass nor fail)", JSON.stringify(r5));
    const cli3 = spawnSync(process.execPath, [path.join(here, "swap.mjs"), "props", "--root", ROOT, "--file", f3.rel, "--line", "4", "--local", "Button", "--candidate", "components/variants/button/inter.tsx", "--entry", "BtnI"],
      { cwd: ROOT, env: { ...process.env }, encoding: "utf8" });
    ok(cli3.status === 3, "props CLI exits 3 for unverifiable (documented: say it out loud)", String(cli3.status) + " " + String(cli3.stdout).trim());
  }

  // 16. TS7 native typescript → a coded refusal, never a raw TypeError (T04)
  {
    const fakeTs = path.join(ROOT, "fake-ts7");
    fs.mkdirSync(path.join(fakeTs, "node_modules", "typescript"), { recursive: true });
    fs.writeFileSync(path.join(fakeTs, "package.json"), "{}");
    fs.writeFileSync(path.join(fakeTs, "node_modules", "typescript", "package.json"), JSON.stringify({ name: "typescript", main: "index.js" }));
    fs.writeFileSync(path.join(fakeTs, "node_modules", "typescript", "index.js"),
      "module.exports = { version: \"7.0.2\", versionMajorMinor: \"7.0\" };\n");
    const cli = spawnSync(process.execPath, [path.join(here, "swap.mjs"), "props", "--root", fakeTs, "--file", "app/x.tsx", "--line", "1", "--local", "B", "--candidate", "y.tsx"],
      { cwd: fakeTs, env: { ...process.env, TRYON_TS_ROOT: fakeTs, NODE_PATH: "" }, encoding: "utf8" });
    let j = null;
    try { j = JSON.parse(String(cli.stdout).trim().split("\n").pop()); } catch { /* keep null */ }
    ok(cli.status === 1 && j && j.reason === "TS_API_UNSUPPORTED" && /no JS compiler API/.test(String(j.detail || "")),
      "TS7 native typescript refuses with TS_API_UNSUPPORTED", String(cli.status) + " " + String(cli.stdout).trim());
  }

  // 17. keep (T08): graduate a try — journal entry leaves, unimported siblings go, manifest marks it
  {
    const mk = (name) => {
      const K = fs.mkdtempSync(path.join(os.tmpdir(), "tryon-keep-" + name + "-"));
      fs.writeFileSync(path.join(K, "tsconfig.json"), JSON.stringify({ compilerOptions: { baseUrl: ".", paths: { "@/*": ["./*"] } } }));
      fs.mkdirSync(path.join(K, "app"), { recursive: true });
      fs.writeFileSync(path.join(K, "app", "page.tsx"), 'import { Button } from "@/components/ui/button";\n\nexport function P() {\n  return <Button>k</Button>;\n}\n');
      return K;
    };
    const srcOf = (K, n) => {
      const s = path.join(K, "src-src", n + ".tsx");
      fs.mkdirSync(path.dirname(s), { recursive: true });
      fs.writeFileSync(s, "export function " + n + "({ children }) { return <button data-v=\"" + n + "\">{children}</button>; }\n");
      return s;
    };

    const K = mk("a");
    const i1 = swap.installVariant({ root: K, from: srcOf(K, "KOne"), slot: "button", entry: "KOne", as: "k1.tsx", request: 9 });
    swap.installVariant({ root: K, from: srcOf(K, "KTwo"), slot: "button", entry: "KTwo", as: "k2.tsx" });
    const ap = swap.applySwap({ root: K, file: "app/page.tsx", local: "Button", to: i1.specifier, entry: "KOne" });
    ok(ap.ok && ap.changed, "keep fixture: variant applied with an aliased entry", JSON.stringify(ap));
    const kp = swap.keepSwap({ root: K, file: "app/page.tsx", local: "Button" });
    ok(kp.ok && kp.deleted.includes("components/variants/button/k2.tsx") && !fs.existsSync(path.join(K, "components", "variants", "button", "k2.tsx")),
      "keep: unimported sibling variant deleted", JSON.stringify(kp));
    ok(JSON.parse(fs.readFileSync(path.join(K, ".tryon", "journal.json"), "utf8")).length === 0, "keep: journal emptied");
    const manA = JSON.parse(fs.readFileSync(path.join(K, ".tryon", "manifest.json"), "utf8"));
    ok(manA.some((x) => x.specifier === i1.specifier && x.kept), "keep: manifest marks the staged entry kept");
    const rv = swap.revertSwap({ root: K, file: "app/page.tsx" });
    ok(rv.ok === false && rv.reason === "NO_JOURNAL_ENTRY", "keep: undo is a code edit now — revert refuses honestly");

    const K2 = mk("b");
    const j1 = swap.installVariant({ root: K2, from: srcOf(K2, "KOne"), slot: "button", entry: "KOne", as: "k1.tsx" });
    swap.installVariant({ root: K2, from: srcOf(K2, "KTwo"), slot: "button", entry: "KTwo", as: "k2.tsx" });
    fs.writeFileSync(path.join(K2, "app", "other.tsx"), 'import { KTwo } from "@/components/variants/button/k2";\n\nexport function O() {\n  return <KTwo>o</KTwo>;\n}\n');
    const pre = swap.keepSwap({ root: K2, file: "app/page.tsx", local: "Button" });
    ok(pre.ok === false && pre.reason === "NO_JOURNAL_ENTRY", "keep without apply refuses (nothing to graduate)");
    swap.applySwap({ root: K2, file: "app/page.tsx", local: "Button", to: j1.specifier, entry: "KOne" });
    const kp2 = swap.keepSwap({ root: K2, file: "app/page.tsx", local: "Button" });
    ok(kp2.ok && kp2.kept_imported.includes("components/variants/button/k2.tsx") && fs.existsSync(path.join(K2, "components", "variants", "button", "k2.tsx")),
      "keep: a sibling another file imports is kept and reported", JSON.stringify(kp2));

    // containment: request data (element.file, slot, --as) must never reach outside the project
    const C = mk("c");
    const outside = path.join(path.dirname(C), "outside-" + path.basename(C) + ".tsx");
    fs.writeFileSync(outside, 'import { Button } from "@/components/ui/button";\nexport const X = () => <Button>x</Button>;\n');
    const outBefore = fs.readFileSync(outside, "utf8");
    const code = (fn) => { try { fn(); return "NO_THROW"; } catch (e) { return String(e.message).split(":")[0]; } };
    const i3 = swap.installVariant({ root: C, from: srcOf(C, "KOne"), slot: "button", entry: "KOne", as: "k1.tsx" });
    ok(code(() => swap.applySwap({ root: C, file: "../" + path.basename(outside), local: "Button", to: i3.specifier, entry: "KOne" })) === "PATH_OUTSIDE_PROJECT"
      && fs.readFileSync(outside, "utf8") === outBefore, "containment: apply refuses a ../ file and leaves it untouched");
    ok(code(() => swap.applySwap({ root: C, file: outside, local: "Button", to: i3.specifier, entry: "KOne" })) === "PATH_OUTSIDE_PROJECT",
      "containment: apply refuses an absolute path outside the root");
    ok(code(() => swap.installVariant({ root: C, from: srcOf(C, "KOne"), slot: "../../../evil", entry: "KOne" })) === "BAD_SLOT"
      && !fs.existsSync(path.join(path.dirname(C), "evil")), "containment: install refuses a traversal slot");
    ok(code(() => swap.installVariant({ root: C, from: srcOf(C, "KOne"), slot: "button", entry: "KOne", as: "../../x.tsx" })) === "BAD_FILE_NAME",
      "containment: install refuses a path in --as");
    ok(code(() => swap.revertSwap({ root: C, file: "../" + path.basename(outside) })) === "PATH_OUTSIDE_PROJECT",
      "containment: revert refuses a ../ file");
    fs.rmSync(outside, { force: true });
  }
} catch (e) {
  fail++;
  console.log("  FAIL (exception) " + (e && e.stack || e));
}

console.log(`\n${pass}/${pass + fail} assertions passed`);
process.exit(fail ? 1 : 0);
