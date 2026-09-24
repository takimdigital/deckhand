'use strict';
/**
 * tryon loader — a dev-only Turbopack loader that stamps JSX host elements with their source
 * location: data-tryon-src="<abs file>:<line>". Shipped by buildout's /buildout try-on.
 *
 * Measured on Next 16.3.6 + Turbopack (references/tryon.md):
 *  - dev-only, twice over: the installer registers this rule only when NODE_ENV === "development",
 *    and this file hard-refuses outside development. A `condition` string inside a Turbopack rule is
 *    a matcher, NOT an env gate — a static rule stamped 4 files into a production .next (measured).
 *  - the attribute lands in BOTH the server-rendered HTML (works for server components too) and
 *    the client bundle; the overlay walks up from the clicked node to the nearest element that has it.
 *  - the TS-generic guard is mandatory: without it `useState<number>(0)` is rewritten and the
 *    module fails to compile ("Expected a semicolon").
 */
const TAG = /<([A-Za-z][A-Za-z0-9_.]*)(?=[\s/>])/g;

// Identifiers that mean the `<` starts a TS type argument list, not JSX: Promise<Metadata>, Record<…>, …
const TYPE_NAMES = new Set(['Promise', 'Array', 'Readonly', 'ReadonlyArray', 'Partial', 'Required', 'Record',
  'Map', 'Set', 'WeakMap', 'WeakSet', 'Iterable', 'AsyncIterable', 'Iterator', 'Generator', 'AsyncGenerator',
  'ReturnType', 'Parameters', 'Awaited', 'Omit', 'Pick', 'Exclude', 'Extract', 'NonNullable', 'InstanceType',
  'ThisType', 'Uppercase', 'Lowercase', 'Capitalize', 'Uncapitalize', 'ComponentProps',
  'ComponentPropsWithoutRef', 'ElementRef', 'PropsWithChildren', 'ForwardedRef', 'HTMLProps', 'SVGProps', 'JSX']);

/** Type-ish context? Ends with `:`, `<` or `,` (annotation / nested type args), follows a type name,
 *  or sits directly behind another unclosed `<Tag` (the `<List<Item> …>` generic-component shape). */
function typeishContext(line, offset) {
  const trimmed = line.slice(0, offset).replace(/\s+$/, '');
  if (/[<,:]$/.test(trimmed)) return true;
  if (/<[A-Za-z][A-Za-z0-9_.]*$/.test(trimmed)) return true;
  // a `<` glued to a preceding identifier/`)`/`]` is a type-argument list, never JSX:
  // `useState<boolean | null>(null)`, `Promise<Metadata>`, `foo<T>()`, `arr[0]<T>`
  if (/[\w$)\]]$/.test(trimmed)) return true;
  const m = trimmed.match(/([A-Za-z_$][\w$]*)$/);
  return !!(m && TYPE_NAMES.has(m[1]));
}

/** Odd number of quotes before the match ⇒ the `<` sits inside a string literal. */
function insideString(line, offset) {
  let d = 0, s = 0, b = 0, esc = false;
  for (let i = 0; i < offset; i++) {
    const c = line[i];
    if (esc) { esc = false; continue; }
    if (c === '\\') { esc = true; continue; }
    if (c === '"') d++; else if (c === "'") s++; else if (c === '`') b++;
  }
  return d % 2 === 1 || s % 2 === 1 || b % 2 === 1;
}

module.exports = function tryonLoader(source) {
  const done = typeof this.async === 'function' ? this.async() : null;
  const emit = (out) => (done ? done(null, out) : out);

  const resource = String(this.resourcePath || '').replace(/\\/g, '/');
  const root = String((this.rootContext || '')
    || (this.getOptions && (this.getOptions() || {}).root)
    || '').replace(/\\/g, '/');

  // belt and braces: a rule that leaked into a production config must still be inert here
  if (process.env.NODE_ENV !== 'development') return emit(source);

  // only project source: never node_modules, never build output, never our own tooling
  if (!/\.(t|j)sx$/.test(resource)) return emit(source);
  if (resource.includes('/node_modules/') || resource.includes('/.next/') || resource.includes('/.tryon/')) {
    return emit(source);
  }
  if (root && !resource.startsWith(root + '/')) return emit(source);

  let changed = false;
  const out = source
    .split('\n')
    .map((line, idx) => {
      if (!line.includes('<') || line.includes('data-tryon-src')) return line;
      const next = line.replace(TAG, (full, tag, offset) => {
        const after = line.slice(offset + full.length);
        // TS generics / comparisons are not JSX: `<T>(`, `<number>(0)`, `<T,`, `<T extends`
        if (after.startsWith('>(') || after.startsWith(',') || after.startsWith(' extends')) return full;
        // generic JSX components (`<List<Item> …>`) would be broken by an inserted attribute
        if (after.startsWith('<')) return full;
        if (typeishContext(line, offset)) return full;
        if (insideString(line, offset)) return full;
        changed = true;
        return '<' + tag + ' data-tryon-src="' + resource + ':' + (idx + 1) + '"';
      });
      return next;
    })
    .join('\n');

  return emit(changed ? out : source);
};
