#!/usr/bin/env node
/**
 * test-loader.cjs — the loader corpus. Every case here was a real misfire risk; the Promise<Metadata>
 * one broke a real Next 15 dev server (`}: Promise<Metadata data-tryon-src=…> {` → parse error).
 *
 *   node templates/tryon/test-loader.cjs
 */
const path = require('node:path');
const loader = require(path.join(__dirname, 'loader.cjs'));

process.env.NODE_ENV = 'development';
const ctx = () => ({
  resourcePath: 'C:/proj/src/app/page.tsx',
  rootContext: 'C:/proj',
  getOptions: () => ({ root: 'C:/proj' }),
});
const run = (src) => loader.call(ctx(), src);
const at = (n) => ` data-tryon-src="C:/proj/src/app/page.tsx:${n}"`;
const S = at(1);

let pass = 0, fail = 0;
const ok = (cond, name, detail) => {
  if (cond) { pass++; console.log('  ok  ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '  :: ' + detail : '')); }
};

// --- must stamp -------------------------------------------------------------------------------
ok(run('<div className="x">ok</div>') === `<div${S} className="x">ok</div>`, 'plain jsx tag with attribute');
ok(run('<Button onClick={f} />') === `<Button${S} onClick={f} />`, 'self-closing component');
ok(run('<div id="a"><span>x</span></div>') === `<div${S} id="a"><span${S}>x</span></div>`,
  'two tags on one line, closing tags untouched');
ok(run('  return (\n    <main>\n      <h1>hi</h1>\n    </main>\n  );') ===
  `  return (\n    <main${at(2)}>\n      <h1${at(3)}>hi</h1>\n    </main>\n  );`, 'multi-line markup, per-line numbers, no stray stamp on closing tags');
ok(run('<Foo bar={<Bar/>}>x</Foo>') === `<Foo${S} bar={<Bar${S}/>}>x</Foo>`, 'attribute expression holds jsx');

// --- must NOT stamp (the type-position class that broke a real dev server) ---------------------
ok(run('export function generateMetadata(): Promise<Metadata> {') === 'export function generateMetadata(): Promise<Metadata> {',
  'Promise<Metadata> return type (the real 500)');
ok(run('async function f(p: Promise<Record<string, string>>) {') === 'async function f(p: Promise<Record<string, string>>) {',
  'nested type args Promise<Record<string, string>>');
ok(run('const [n, setN] = useState<number>(0);') === 'const [n, setN] = useState<number>(0);', 'useState<number>(0)');
ok(run('const [d, setD] = useState<boolean | null>(null);') === 'const [d, setD] = useState<boolean | null>(null);',
  'useState<boolean | null>(null) — the real ThemeToggle break');
ok(run('const [v, setV] = useState<number | undefined>(undefined);') ===
  'const [v, setV] = useState<number | undefined>(undefined);', 'useState<number | undefined>');
ok(run('{cond && (<A/>)}') === `{cond && (<A${S}/>)}`, 'jsx after `(`');
ok(run('{items.map((i) => <Item key={i} />)}') === `{items.map((i) => <Item${S} key={i} />)}`, 'jsx after `=>`');
ok(run('function foo<T extends object>(x: T) {') === 'function foo<T extends object>(x: T) {', 'generic function');
ok(run('const el = createContext<Foo>(null);') === 'const el = createContext<Foo>(null);', 'generic call');
ok(run('type P = React.ComponentProps<typeof Button>;') === 'type P = React.ComponentProps<typeof Button>;',
  'React.ComponentProps<typeof …>');
ok(run('if (a < b && c > d) {') === 'if (a < b && c > d) {', 'plain comparison');
ok(run('const s = "<div>hi</div>";') === 'const s = "<div>hi</div>";', 'tag-looking text inside a string');
ok(run('const el = <List<Item> items={x} />;') === 'const el = <List<Item> items={x} />;', 'generic jsx component');
ok(run('function f(): Array<string> {') === 'function f(): Array<string> {', 'Array<string> return type');

// --- path + env guards -------------------------------------------------------------------------
const outside = loader.call({ ...ctx(), resourcePath: 'C:/other/app/page.tsx' }, '<div>x</div>');
ok(outside === '<div>x</div>', 'a file outside root is never stamped');
const nm = loader.call({ ...ctx(), resourcePath: 'C:/proj/node_modules/pkg/ui.tsx' }, '<div>x</div>');
ok(nm === '<div>x</div>', 'node_modules is never stamped');
process.env.NODE_ENV = 'production';
ok(run('<div>x</div>') === '<div>x</div>', 'production build is inert (hard env guard)');
process.env.NODE_ENV = 'development';

console.log(`\n${pass}/${pass + fail} assertions passed`);
process.exit(fail ? 1 : 0);
