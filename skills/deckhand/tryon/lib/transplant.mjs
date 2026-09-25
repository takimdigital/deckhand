/**
 * transplant.mjs — "their design, your words", deterministically (no model call).
 *
 * extractUnits(): the clicked JSX subtree -> content units in document order. A unit is the
 *   nearest content-bearing element (h1-h6, p, a/Link/Button, li, label, blockquote …); its source is
 *   the deepest element holding all the text (so icons beside a label survive), taken VERBATIM:
 *   inner markup and in-scope expressions like {t('title')} are carried as-is.
 *   Lists rendered with `arr.map(…)` over a literal array in the same file are UNROLLED: each
 *   item's fields are evaluated, so a pricing grid carries every plan, price and feature.
 * parameterize(): the candidate component -> slots. Static units become
 *   `{content.heading1 ?? <>demo</>}`; a `.map()` over the candidate's own demo array becomes a
 *   list slot `(content.list1 ? content.list1.map(merge-with-demo) : demo).map(…)`.
 * bind(): pair units by role and order; pair lists item by item, field by role.
 * The usage replaces the clicked element in place, so every carried expression stays in scope.
 */
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { parse, walk, jsxName, attr } = require('./ast.cjs');

const BLOCK_TAGS = new Set(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'button', 'li', 'label', 'blockquote',
  'figcaption', 'dt', 'dd', 'td', 'th', 'cite', 'q', 'legend', 'summary', 'caption', 'option']);

export function roleOf(name) {
  if (/^h[1-6]$/.test(name)) return 'heading';
  if (/^(a|button)$/.test(name) || /(^|\.)(Link|Button|NavLink|Anchor)$/.test(name) || /Button$/.test(name)) return 'action';
  if (/^(li|dt|dd)$/.test(name)) return 'item';
  if (name === 'label' || name === 'legend') return 'label';
  if (/^(blockquote|q|cite|figcaption)$/.test(name)) return 'quote';
  return 'text';
}
const isBlockEl = (name) => BLOCK_TAGS.has(name) || roleOf(name) === 'action';
const CONTENT_ROLES = ['heading', 'text', 'price', 'action', 'item', 'label', 'quote'];
const ITEM_CLASSES = [['heading', 'text', 'quote', 'label'], ['price'], ['action'], ['item']];
const PRICE = /^(?:from\s+)?[$€£¥₹]?\s?\d[\d.,\s]*(?:k)?\s?(?:[$€£¥₹]|eur|usd|mad|dh)?\s*(?:\/\s*\w+|per \w+)?$/i;
const withPrice = (u) => (u.role !== 'action' && u.role !== 'heading' && PRICE.test(u.text) ? { ...u, role: 'price' } : u);

const isStaticExpr = (e) => e.type === 'StringLiteral' || (e.type === 'TemplateLiteral' && !e.expressions.length);

function hasStaticText(kids) {
  return kids.some((c) => (c.type === 'JSXText' && c.value.trim()) || (c.type === 'JSXExpressionContainer' && isStaticExpr(c.expression)));
}
/** An expression that renders content (`{t('x')}`, `{p.name}`) — not structure (`{list.map(…)}`, `{ok && <X/>}`). */
function isDynamicChild(c) {
  if (c.type !== 'JSXExpressionContainer' || c.expression.type === 'JSXEmptyExpression' || isStaticExpr(c.expression)) return false;
  let structural = false;
  walk(c.expression, (n) => {
    if (structural) return false;
    if (n.type === 'JSXElement' || n.type === 'JSXFragment' || /Function/.test(n.type) || mapCall(n)) return (structural = true, false);
    return true;
  });
  return !structural;
}
function childExpressions(el) {
  return (el.children || []).some((c) => isDynamicChild(c) || (c.type === 'JSXElement' && childExpressions(c)));
}
function directContent(kids, dyn) { return hasStaticText(kids) || (dyn && kids.some(isDynamicChild)); }
function inlineContent(el, dyn) {
  const kids = el.children || [];
  if (directContent(kids, dyn)) return true;
  return kids.some((c) => c.type === 'JSXElement' && !isBlockEl(jsxName(c.openingElement.name)) && inlineContent(c, dyn));
}
/** Deepest element holding ALL the text: `<Link><span>Go</span><Icon/></Link>` -> span. */
function textHost(el, dyn) {
  const kids = el.children || [];
  if (directContent(kids, dyn)) return el;
  const bearing = kids.filter((c) => c.type === 'JSXElement' && inlineContent(c, dyn));
  return bearing.length === 1 ? textHost(bearing[0], dyn) : el;
}
function containsBlock(el) {
  let found = false;
  walk(el, (n) => {
    if (found) return false;
    if (n.type === 'JSXElement' && isBlockEl(jsxName(n.openingElement.name)) && inlineContent(n, true)) return (found = true, false);
    return true;
  });
  return found;
}
/** `<Button asChild><Link href="/x">…` — the href lives on the single child element. */
function findHref(el) {
  const own = attr(el, 'href') || attr(el, 'to');
  if (own) return own;
  const kids = (el.children || []).filter((c) => c.type === 'JSXElement');
  return kids.length === 1 ? findHref(kids[0]) : null;
}

function textOf(code, node) {
  let s = '';
  walk(node, (n, parent) => {
    if (n.type === 'JSXAttribute') return false;
    if (n.type === 'JSXText') s += n.value;
    else if (n.type === 'JSXExpressionContainer' && parent && parent.type !== 'JSXAttribute') {
      const e = n.expression;
      if (e.type === 'StringLiteral') s += e.value;
      else if (e.type !== 'JSXEmptyExpression') s += '{' + code.slice(e.start, e.end) + '}';
      return false;
    }
    return true;
  });
  return s.replace(/\s+/g, ' ').trim();
}

/* ------------------------------------------------------------------ literal data */

/** JS value of a literal AST node; undefined when anything is non-literal. */
export function litValue(node) {
  if (!node) return undefined;
  switch (node.type) {
    case 'StringLiteral': case 'NumericLiteral': case 'BooleanLiteral': return node.value;
    case 'TemplateLiteral': return node.expressions.length ? undefined : node.quasis.map((q) => q.value.cooked).join('');
    case 'TSAsExpression': case 'TSSatisfiesExpression': case 'TSConstAssertion': return litValue(node.expression);
    case 'ArrayExpression': {
      const out = [];
      for (const e of node.elements) { const v = litValue(e); out.push(v); }
      return out;
    }
    case 'ObjectExpression': {
      const o = {};
      for (const p of node.properties) {
        if (p.type !== 'ObjectProperty' || p.computed) continue;
        const k = p.key.type === 'Identifier' ? p.key.name : p.key.value;
        o[k] = litValue(p.value);                      // non-literal fields become undefined (icons, components)
      }
      return o;
    }
    default: return undefined;
  }
}

function topArrays(ast) {
  const m = new Map();
  for (const st of ast.program.body) {
    const d = st.type === 'ExportNamedDeclaration' ? st.declaration : st;
    if (!d || d.type !== 'VariableDeclaration') continue;
    for (const v of d.declarations) {
      let init = v.init;
      while (init && /^TS(As|Satisfies)Expression$/.test(init.type)) init = init.expression;
      if (v.id.type === 'Identifier' && init && init.type === 'ArrayExpression') m.set(v.id.name, init);
    }
  }
  return m;
}

function mapCall(e) {
  if (e.type !== 'CallExpression' || e.callee.type !== 'MemberExpression' || e.callee.property.name !== 'map') return null;
  const cb = e.arguments[0];
  if (!cb || !/Function/.test(cb.type)) return null;
  return { object: e.callee.object, cb };
}

function binding(cb) {
  const p = cb.params[0];
  if (!p) return null;
  if (p.type === 'Identifier') return { kind: 'id', name: p.name };
  if (p.type === 'ObjectPattern') {
    const map = {};
    for (const pr of p.properties) {
      if (pr.type !== 'ObjectProperty') continue;
      const key = pr.key.name || pr.key.value;
      const local = pr.value.type === 'Identifier' ? pr.value.name : (pr.value.type === 'AssignmentPattern' && pr.value.left.type === 'Identifier' ? pr.value.left.name : null);
      if (local) map[local] = key;
    }
    return { kind: 'obj', map };
  }
  return null;
}

/** Field name an expression reads from the map item (`p.name`, destructured `name`), else null. */
function fieldOf(e, bind) {
  if (!bind || !e) return null;
  if (bind.kind === 'id' && e.type === 'MemberExpression' && !e.computed && e.object.type === 'Identifier' && e.object.name === bind.name) return e.property.name;
  if (bind.kind === 'obj' && e.type === 'Identifier' && bind.map[e.name]) return bind.map[e.name];
  return null;
}

function callbackJsx(cb) {
  const out = [];
  if (cb.body.type !== 'BlockStatement') {
    walk(cb.body, (n) => { if (n.type === 'JSXElement') { out.push(n); return false; } return true; });
  } else {
    walk(cb.body, (n) => {
      if (n !== cb.body && /Function/.test(n.type)) return false;
      if (n.type === 'ReturnStatement' && n.argument) { walk(n.argument, (m) => { if (m.type === 'JSXElement') { out.push(m); return false; } return true; }); return false; }
      return true;
    });
  }
  return out;
}

const escapeJsxText = (s) => (/[{}<>]/.test(s) ? `{${JSON.stringify(s)}}` : s);

/** Source of `host`'s children with every item-field expression replaced by its literal. */
function resolvedSrc(code, host, env) {
  const kids = host.children || [];
  if (!kids.length) return null;
  const edits = [];
  let ok = true;
  walk({ type: 'X', children: kids }, (n, parent) => {
    if (!ok) return false;
    if (n.type === 'JSXAttribute') return false;
    if (n.type === 'JSXExpressionContainer' && parent && parent.type !== 'JSXAttribute') {
      const e = n.expression;
      if (e.type === 'JSXEmptyExpression' || isStaticExpr(e)) return false;
      const f = fieldOf(e, env.bind);
      const v = f != null ? env.item[f] : undefined;
      if (typeof v === 'string' || typeof v === 'number') edits.push({ start: n.start, end: n.end, text: escapeJsxText(String(v)) });
      else ok = false;
      return false;
    }
    return true;
  });
  if (!ok) return null;
  let s = code.slice(kids[0].start, kids[kids.length - 1].end);
  const base = kids[0].start;
  edits.sort((a, b) => b.start - a.start);
  for (const e of edits) s = s.slice(0, e.start - base) + e.text + s.slice(e.end - base);
  return s;
}

function resolvedText(src) {
  return src.replace(/<[^>]+>/g, ' ').replace(/\{"(.*?)"\}/g, '$1').replace(/\s+/g, ' ').trim();
}

/* ------------------------------------------------------------------ collection */

/**
 * Walk a JSX root. mode 'original': expressions allowed, literal-array maps unrolled.
 * mode 'candidate': static units only; maps over demo arrays become list slots.
 */
function collect(code, root, ast, mode) {
  const arrays = topArrays(ast);
  const units = [], images = [], inputs = [], lists = [], bullets = [];
  let dynamicLists = 0;

  const unitFor = (el, env) => {
    const name = jsxName(el.openingElement.name);
    const dyn = mode === 'original';
    const host = textHost(el, dyn || !!env);
    const hk = host.children || [];
    if (!hk.length) return null;
    const hrefAttr = findHref(el);
    const level = /^h([1-6])$/.exec(name);
    const base = { role: roleOf(name), level: level ? Number(level[1]) : null, el, tag: name, host };
    if (env) {
      const src = resolvedSrc(code, host, env);
      if (src == null || !src.trim()) return null;
      let href = null;
      if (hrefAttr && hrefAttr.value) {
        if (hrefAttr.value.type === 'StringLiteral') href = JSON.stringify(hrefAttr.value.value);
        else if (hrefAttr.value.type === 'JSXExpressionContainer') {
          const f = fieldOf(hrefAttr.value.expression, env.bind);
          if (f != null && typeof env.item[f] === 'string') href = JSON.stringify(env.item[f]);
        }
      }
      return { ...base, src: src.trim(), text: resolvedText(src), href, dynamic: false };
    }
    const dynamic = childExpressions(host);
    if (mode === 'candidate' && dynamic) return null;
    const src = code.slice(hk[0].start, hk[hk.length - 1].end);
    if (!src.trim()) return null;
    return { ...base, childrenStart: hk[0].start, childrenEnd: hk[hk.length - 1].end, src, text: textOf(code, host), dynamic, hrefAttr };
  };

  const visit = (el, ctx) => {
    if (el.type !== 'JSXElement') return;
    const name = jsxName(el.openingElement.name);
    if (roleOf(name) === 'action' && !ctx.actionOuter) ctx = { ...ctx, actionOuter: el };
    if (/^(img|Image)$/.test(name)) {
      const src = attr(el, 'src'), alt = attr(el, 'alt');
      if (src && src.value) {
        if (ctx.env) {
          const val = (a) => {
            if (!a || !a.value) return null;
            if (a.value.type === 'StringLiteral') return JSON.stringify(a.value.value);
            const f = a.value.type === 'JSXExpressionContainer' ? fieldOf(a.value.expression, ctx.env.bind) : null;
            return f != null && typeof ctx.env.item[f] === 'string' ? JSON.stringify(ctx.env.item[f]) : null;
          };
          ctx.item.images.push({ src: val(src), alt: val(alt) });
        } else if (!ctx.inMap) images.push({ el, src, alt });
      }
    }
    if (/^(input|textarea|Input|Textarea)$/.test(name) && !ctx.inMap && !ctx.env) {
      const ph = attr(el, 'placeholder');
      if (ph && ph.value) inputs.push({ el, ph });
    }
    const kids = el.children || [];
    const nestedBlock = kids.some((c) => c.type === 'JSXElement' && containsBlock(c));
    const blockish = isBlockEl(name) && !nestedBlock && inlineContent(el, mode === 'original' || !!ctx.env);
    // a div/span that holds text directly (a price, a tagline) is content too — decorative bits are not
    const loose = !blockish && !nestedBlock && /^[a-z]/.test(name) && !/^(svg|path|g|circle|rect|code|pre|kbd|option)$/.test(name)
      && directContent(kids, mode === 'original' || !!ctx.env);
    if (blockish || loose) {
      if (!ctx.inMap || ctx.env) {
        let u = unitFor(el, ctx.env);
        if (u) u = withPrice(u);
        if (u && loose && u.role !== 'price' && u.text.replace(/[^\p{L}\p{N}]/gu, '').length < 4) u = null;
        if (u) {
          if (u.role === 'action') u.outer = ctx.actionOuter || el;
          if (ctx.env) { u.list = ctx.list; u.itemIdx = ctx.itemIdx; ctx.item.units.push(u); }
          units.push(u);
          return;
        }
      }
    }
    for (const c of kids) {
      if (c.type === 'JSXElement') visit(c, ctx);
      else if (c.type === 'JSXFragment') { for (const cc of c.children) if (cc.type === 'JSXElement') visit(cc, ctx); }
      else if (c.type === 'JSXExpressionContainer') visitExpr(c.expression, ctx);
    }
  };

  const visitExpr = (e, ctx) => {
    const mc = mapCall(e);
    if (mc) {
      const arr = mc.object.type === 'Identifier' ? arrays.get(mc.object.name) : (mc.object.type === 'ArrayExpression' ? mc.object : null);
      const bind = binding(mc.cb);
      const roots = callbackJsx(mc.cb);
      // nested list inside a list item: `p.features.map(f => <li>{f}</li>)`
      if (ctx.env && mc.object.type === 'MemberExpression') {
        const f = fieldOf(mc.object, ctx.env.bind);
        const vals = f != null ? ctx.env.item[f] : undefined;
        if (Array.isArray(vals) && vals.every((v) => typeof v === 'string')) ctx.item.bullets.push(...vals);
        return;
      }
      if (mode === 'original' && arr && !ctx.env && bind) {
        const items = litValue(arr);
        if (Array.isArray(items) && items.length && items.every((x) => x && typeof x === 'object')) {
          const list = { items: [] };
          lists.push(list);
          items.forEach((item, i) => {
            const it = { units: [], images: [], bullets: [] };
            list.items.push(it);
            for (const r of roots) visit(r, { env: { bind, item }, list, itemIdx: i, item: it });
          });
          return;
        }
      }
      if (mode === 'candidate' && mc.object.type === 'ArrayExpression' && !ctx.inMap) {
        const vals = litValue(mc.object);
        if (Array.isArray(vals) && vals.length && vals.every((v) => typeof v === 'string')) bullets.push({ node: mc.object, count: vals.length });
      }
      if (mode === 'candidate' && arr && mc.object.type === 'Identifier' && !ctx.inMap && bind) {
        const demo = litValue(arr);
        if (Array.isArray(demo) && demo.length && demo.every((x) => x && typeof x === 'object')) {
          lists.push({ name: mc.object.name, object: mc.object, fields: listFields(code, roots, bind), demoCount: demo.length });
        }
      }
      if (mode === 'original' && !ctx.env) dynamicLists++;
      for (const r of roots) visit(r, { ...ctx, inMap: true });
      return;
    }
    walk(e, (n) => {
      if (n.type === 'JSXElement') { visit(n, ctx); return false; }
      if (n !== e && mapCall(n)) { visitExpr(n, ctx); return false; }
      return true;
    });
  };

  if (root.type === 'JSXFragment') for (const c of root.children) { if (c.type === 'JSXElement') visit(c, {}); else if (c.type === 'JSXExpressionContainer') visitExpr(c.expression, {}); }
  else visit(root, {});
  return { units, images, inputs, lists, bullets, dynamicLists };
}

/** Candidate list schema: which item field feeds which role, in JSX order. */
function listFields(code, roots, bind) {
  const fields = [];
  const seen = new Set();
  const push = (f) => { if (!seen.has(f.field + ':' + f.role)) { seen.add(f.field + ':' + f.role); fields.push(f); } };
  for (const r of roots) {
    walk(r, (n) => {
      if (n.type === 'JSXElement') {
        const name = jsxName(n.openingElement.name);
        for (const a of n.openingElement.attributes) {
          if (a.type !== 'JSXAttribute' || !a.value || a.value.type !== 'JSXExpressionContainer') continue;
          const f = fieldOf(a.value.expression, bind);
          if (f == null) continue;
          const an = a.name.name;
          if (an === 'href' || an === 'to') push({ field: f, role: 'href' });
          else if (an === 'src' && /^(img|Image)$/.test(name)) push({ field: f, role: 'image' });
          else if (an === 'alt') push({ field: f, role: 'imageAlt' });
        }
        if (isBlockEl(name)) {
          const host = textHost(n, true);
          const exprs = (host.children || []).filter((c) => c.type === 'JSXExpressionContainer' && c.expression.type !== 'JSXEmptyExpression');
          if (exprs.length === 1) {
            const f = fieldOf(exprs[0].expression, bind);
            if (f != null) push({ field: f, role: roleOf(name) });
          }
        }
      }
      if (n.type === 'JSXExpressionContainer') {
        const mc = mapCall(n.expression);
        if (mc && mc.object.type === 'MemberExpression') {
          const f = fieldOf(mc.object, bind);
          if (f != null) push({ field: f, role: 'bullets' });
          return false;
        }
      }
      return true;
    });
  }
  return fields;
}

/** Repeated sibling elements that each hold >= 2 content units (tier cards, feature cards, FAQ rows). */
function siblingGroups(root, units) {
  const groups = [];
  walk(root, (n) => {
    if (n.type !== 'JSXElement') return true;
    const kids = (n.children || []).filter((c) => c.type === 'JSXElement');
    if (kids.length < 2) return true;
    const byTag = new Map();
    for (const k of kids) {
      const t = jsxName(k.openingElement.name);
      if (!byTag.has(t)) byTag.set(t, []);
      byTag.get(t).push(k);
    }
    for (const members of byTag.values()) {
      if (members.length < 2) continue;
      const per = members.map((m) => units.filter((u) => u.el.start >= m.start && u.el.end <= m.end));
      if (per.filter((p) => p.length >= 2).length >= 2) groups.push({ members, per, total: per.reduce((a, p) => a + p.length, 0) });
    }
    return true;
  });
  groups.sort((a, b) => b.total - a.total || a.members[0].start - b.members[0].start);
  return groups;
}

const attrValueSrc = (code, a) => {
  if (!a || !a.value) return null;
  if (a.value.type === 'StringLiteral') return JSON.stringify(a.value.value);
  if (a.value.type === 'JSXExpressionContainer') return code.slice(a.value.expression.start, a.value.expression.end);
  return null;
};

/** Content of the clicked element. `ast` = the whole file (to evaluate literal data arrays). */
export function extractUnits(code, el, ast = null) {
  const fileAst = ast || parse('x.tsx', code);
  const c = collect(code, el, fileAst, 'original');
  const pub = (u) => ({
    role: u.role, level: u.level, text: u.text, src: u.src.trim(), dynamic: !!u.dynamic,
    href: u.href !== undefined ? u.href : attrValueSrc(code, u.hrefAttr), list: u.list ? c.lists.indexOf(u.list) : null, item: u.itemIdx ?? null,
  });
  const lists = c.lists.map((l) => ({ items: l.items.map((it) => ({ units: it.units.map(pub), images: it.images, bullets: it.bullets })) }));
  let units = c.units.map(pub);
  if (!lists.length) {
    const g = siblingGroups(el, c.units)[0];
    if (g && g.members.length >= 2) {
      const idx = new Map();
      g.per.forEach((p, i) => p.forEach((u) => idx.set(u, i)));
      units = c.units.map((u) => ({ ...pub(u), list: idx.has(u) ? 0 : null, item: idx.has(u) ? idx.get(u) : null }));
      lists.push({ literal: true, items: g.per.map((p) => ({ units: p.map((u) => ({ ...pub(u), list: 0 })), images: [], bullets: [] })) });
    }
  }
  return {
    units,
    images: c.images.map((i) => ({ src: attrValueSrc(code, i.src), alt: attrValueSrc(code, i.alt) })),
    inputs: c.inputs.map((i) => ({ placeholder: attrValueSrc(code, i.ph) })),
    lists,
    dynamicLists: c.dynamicLists,
  };
}

/* ------------------------------------------------------------------ candidate */

function findComponentFn(ast, exp) {
  const byName = {};
  for (const st of ast.program.body) {
    const d = st.type === 'ExportNamedDeclaration' || st.type === 'ExportDefaultDeclaration' ? st.declaration : st;
    if (!d) continue;
    if (d.type === 'FunctionDeclaration' && d.id) byName[d.id.name] = d;
    if (d.type === 'VariableDeclaration') for (const v of d.declarations) {
      if (!v.id.name || !v.init) continue;
      if (/Function/.test(v.init.type)) byName[v.id.name] = v.init;
      else if (v.init.type === 'CallExpression' && v.init.arguments[0] && /Function/.test(v.init.arguments[0].type)) byName[v.id.name] = v.init.arguments[0];
    }
  }
  if (exp.kind === 'default') {
    const st = ast.program.body.find((s) => s.type === 'ExportDefaultDeclaration');
    if (!st) return null;
    const d = st.declaration;
    if (/Function/.test(d.type)) return d;
    if (d.type === 'Identifier') return byName[d.name] || null;
    if (d.type === 'CallExpression' && d.arguments[0] && /Function/.test(d.arguments[0].type)) return d.arguments[0];
    return null;
  }
  return byName[exp.name] || null;
}

function returnedJsx(fn) {
  const out = [];
  if (fn.body.type !== 'BlockStatement') {
    walk(fn.body, (n) => { if (n.type === 'JSXElement' || n.type === 'JSXFragment') { out.push(n); return false; } return true; });
    return out;
  }
  walk(fn.body, (n) => {
    if (n !== fn.body && /Function/.test(n.type)) return false;
    if (n.type === 'ReturnStatement' && n.argument) {
      walk(n.argument, (m) => { if (m.type === 'JSXElement' || m.type === 'JSXFragment') { out.push(m); return false; } return true; });
      return false;
    }
    return true;
  });
  return out;
}

const CHROME = /(^|\.)(\w*Header|\w*Navbar|\w*NavBar|\w*Nav)$/;

/**
 * Parameterize the candidate entry file -> { code, slots[], lists[], prop, removed[] }.
 * opts.stripChrome: drop header/navbar components a block embeds (the site has its own) and
 * turn a nested <main> into a <div>.
 */
export function parameterize(file, code, exp, opts = {}) {
  const ast = parse(file, code);
  const fn = exp ? findComponentFn(ast, exp) : null;
  if (!fn) return { code, slots: [], lists: [], reason: 'NO_COMPONENT_FUNCTION' };
  const roots = returnedJsx(fn);
  const prop = /\bcontent\b/.test(code) ? 'dhContent' : 'content';
  const tsFile = /\.tsx?$/.test(file);
  const edits = [];
  const slots = [];
  const counters = {};
  const key = (role) => { counters[role] = (counters[role] || 0) + 1; return role + counters[role]; };

  const p0 = fn.params[0];
  const typeLit = `{ ${prop}?: Record<string, any> }`;
  let acc;
  if (!p0) {
    const open = code.indexOf('(', fn.id ? fn.id.end : (fn.typeParameters ? fn.typeParameters.end : fn.start));
    edits.push({ start: open + 1, end: open + 1, text: tsFile ? `{ ${prop} = {} }: ${typeLit} = {}` : `{ ${prop} = {} } = {}` });
    acc = (k) => `${prop}.${k}`;
  } else if (p0.type === 'ObjectPattern' || (p0.type === 'AssignmentPattern' && p0.left.type === 'ObjectPattern')) {
    const pat = p0.type === 'ObjectPattern' ? p0 : p0.left;
    edits.push({ start: pat.start + 1, end: pat.start + 1, text: ` ${prop} = {},` });
    if (pat.typeAnnotation && tsFile) edits.push({ start: pat.typeAnnotation.end, end: pat.typeAnnotation.end, text: ` & ${typeLit}` });
    acc = (k) => `${prop}.${k}`;
  } else if (p0.type === 'Identifier') {
    if (p0.typeAnnotation && tsFile) edits.push({ start: p0.typeAnnotation.end, end: p0.typeAnnotation.end, text: ` & ${typeLit}` });
    acc = (k) => `${p0.name}.${prop}?.${k}`;
  } else {
    return { code, slots: [], lists: [], reason: 'UNSUPPORTED_SIGNATURE' };
  }

  const removed = [];
  const lists = [];
  const groups = [];
  const logoRows = [];
  const conds = new Map();
  const cut = [];
  for (const root of roots) {
    if (opts.stripChrome) {
      walk(root, (n) => {
        if (n.type !== 'JSXElement') return true;
        const nm = jsxName(n.openingElement.name);
        if (/^[A-Z]/.test(nm) && CHROME.test(nm)) { cut.push({ start: n.start, end: n.end }); removed.push(nm); return false; }
        if (nm === 'main') {
          edits.push({ start: n.openingElement.name.start, end: n.openingElement.name.end, text: 'div' });
          if (n.closingElement) edits.push({ start: n.closingElement.name.start, end: n.closingElement.name.end, text: 'div' });
        }
        return true;
      });
    }
    const c = collect(code, root, ast, 'candidate');
    const inCut = (node) => cut.some((x) => x.start <= node.start && node.end <= x.end);
    const parents = new Map();
    walk(root, (n, parent) => { if (n.type === 'JSXElement') parents.set(n, parent); return true; });
    const inChildren = (n) => { const p = parents.get(n); return p && (p.type === 'JSXElement' || p.type === 'JSXFragment') && (p.children || []).includes(n); };
    // one wrapper per element, conditions AND-ed: `{a !== false && b === true && (<el/>)}`
    const addCond = (node, cond) => { if (!conds.has(node)) conds.set(node, []); conds.get(node).push(cond); };
    // 1. third-party brand logos (a registry's demo "trusted by" row) are hidden unless asked for
    if (opts.logoLocals && opts.logoLocals.length) {
      const rows = new Set();
      const logos = [];
      walk(root, (n) => {
        if (n.type === 'JSXElement' && opts.logoLocals.includes(jsxName(n.openingElement.name))) { logos.push(n); return false; }
        return true;
      });
      const chain = (n) => { const ch = []; for (let p = parents.get(n); p; p = parents.get(p)) if (p.type === 'JSXElement') ch.unshift(p); return ch; };
      if (logos.length) {
        // the lowest common ancestor of every logo = the row; plus its label when the row's parent
        // holds only label + row
        const chains = logos.map(chain);
        let lca = null;
        for (let i = 0; i < chains[0].length; i++) { if (chains.every((ch) => ch[i] === chains[0][i])) lca = chains[0][i]; else break; }
        if (lca && lca !== root) {
          const up = parents.get(lca);
          const sib = up && up.type === 'JSXElement' ? (up.children || []).filter((x) => x.type === 'JSXElement') : [];
          rows.add(sib.length <= 2 && up !== root && inChildren(up) ? up : lca);
        } else {
          for (const lg of logos) { const p = chain(lg).pop(); if (p && p !== root) rows.add(p); }
        }
      }
      for (const r of rows) {
        if (!inChildren(r) || inCut(r)) continue;
        const k = 'logos' + (logoRows.length + 1);
        addCond(r, `${acc(k + 'Show')} === true`);
        logoRows.push(k);
        cut.push({ start: r.start + 0.5, end: r.end - 0.5, hidden: true });
      }
    }
    // 2. repeated cards (tiers, features) — the owner's items fill them in order; extras hide
    const g = groups.length ? null : siblingGroups(root, c.units.filter((u) => !inCut(u.el)))[0];
    const memberOf = new Map();
    if (g) {
      const gk = 'group' + (groups.length + 1);
      g.per.forEach((p, i) => p.forEach((u) => memberOf.set(u, i)));
      g.members.forEach((m, i) => { if (inChildren(m)) addCond(m, `${acc(gk + 'Show' + (i + 1))} !== false`); });
      groups.push({ key: gk, count: g.members.length });
    }
    for (const u of c.units) {
      if (inCut(u.el)) continue;
      const k = key(u.role);
      if (u.role === 'action' && u.outer && inChildren(u.outer) && !u.outer.__dhWrapped) {
        u.outer.__dhWrapped = true;
        addCond(u.outer, `${acc(k + 'Show')} !== false`);
      }
      edits.push({ start: u.childrenStart, end: u.childrenEnd, text: `{${acc(k)} ?? <span data-dh-demo="">${code.slice(u.childrenStart, u.childrenEnd)}</span>}` });
      const slot = { key: k, role: u.role, level: u.level, demo: u.text, hideable: u.role === 'action' && !!(u.outer && u.outer.__dhWrapped) };
      if (memberOf.has(u)) { slot.group = groups[groups.length - 1].key; slot.member = memberOf.get(u); }
      const hv = u.hrefAttr && u.hrefAttr.value;
      if (u.role === 'action' && hv && hv.type === 'StringLiteral') {
        edits.push({ start: hv.start, end: hv.end, text: `{${acc(k + 'Href')} ?? ${JSON.stringify(hv.value)}}` });
        slot.href = true;
      }
      slots.push(slot);
    }
    for (const im of c.images) {
      if (inCut(im.el)) continue;
      const k = key('image');
      const sv = im.src.value;
      if (sv.type !== 'StringLiteral') continue;
      edits.push({ start: sv.start, end: sv.end, text: `{${acc(k)} ?? ${JSON.stringify(sv.value)}}` });
      if (im.alt && im.alt.value && im.alt.value.type === 'StringLiteral') edits.push({ start: im.alt.value.start, end: im.alt.value.end, text: `{${acc(k + 'Alt')} ?? ${JSON.stringify(im.alt.value.value)}}` });
      slots.push({ key: k, role: 'image', demo: sv.value, localDemo: /^(\/|https?:)/.test(sv.value) });
    }
    for (const inp of c.inputs) {
      if (inCut(inp.el) || inp.ph.value.type !== 'StringLiteral') continue;
      const k = key('placeholder');
      edits.push({ start: inp.ph.value.start, end: inp.ph.value.end, text: `{${acc(k)} ?? ${JSON.stringify(inp.ph.value.value)}}` });
      slots.push({ key: k, role: 'placeholder', demo: inp.ph.value.value });
    }
    for (const b of c.bullets) {
      if (inCut(b.node)) continue;
      const k = key('bullets');
      edits.push({ start: b.node.start, end: b.node.end, text: tsFile ? `((${acc(k)} ?? ${code.slice(b.node.start, b.node.end)}) as string[])` : `(${acc(k)} ?? ${code.slice(b.node.start, b.node.end)})` });
      const slot = { key: k, role: 'bullets', demo: `${b.count} demo bullets` };
      if (g) { const mi = g.members.findIndex((m) => m.start <= b.node.start && b.node.end <= m.end); if (mi >= 0) { slot.group = groups[groups.length - 1].key; slot.member = mi; } }
      slots.push(slot);
    }
    for (const l of c.lists) {
      if (inCut(l.object) || !l.fields.some((f) => CONTENT_ROLES.includes(f.role))) continue;
      const k = key('list');
      const a = acc(k);
      const merge = tsFile ? `${a}.map((o: any, i: number) => ({ ...${l.name}[i % ${l.name}.length], ...o }))` : `${a}.map((o, i) => ({ ...${l.name}[i % ${l.name}.length], ...o }))`;
      edits.push({ start: l.object.start, end: l.object.end, text: tsFile ? `((${a} ? ${merge} : ${l.name}) as typeof ${l.name})` : `(${a} ? ${merge} : ${l.name})` });
      lists.push({ key: k, fields: l.fields, demoCount: l.demoCount });
    }
  }
  for (const [node, cs] of conds) {
    if (cut.some((x) => !x.hidden && x.start <= node.start && node.end <= x.end)) continue;
    edits.push({ start: node.start, end: node.start, text: `{${cs.join(' && ')} && (` }, { start: node.end, end: node.end, text: ')}' });
  }
  for (const x of cut) if (!x.hidden) edits.push({ ...x, text: '' });
  const kept = edits.filter((e) => (e.text === '' && !e.hidden) || !cut.some((x) => x.start <= e.start && e.end <= x.end));
  kept.sort((a, b) => b.start - a.start || b.end - a.end);
  let out = code;
  for (const e of kept) out = out.slice(0, e.start) + e.text + out.slice(e.end);
  if (!opts.noVerify) parse(file, out);                        // must still parse — throws otherwise (noVerify: debugging only)
  return { code: out, slots, lists, groups, logoRows, prop, removed };
}

/* ------------------------------------------------------------------ binding */

/**
 * Pair original content with candidate slots -> { props: [[key, src]], carried[], dropped[], demo[] }.
 * When both sides have lists, list items travel as data; otherwise unrolled items pair flat.
 */
export function bind(orig, cand, opts = {}) {
  const slots = cand.slots || cand;
  const candLists = cand.lists || [];
  const props = [], carried = [], dropped = [], demo = [], hidden = [];
  const candGroups = cand.groups || [];
  const useLists = candLists.length && orig.lists.length;
  const useGroup = !useLists && candGroups.length && orig.lists.length;
  const flat = orig.units.filter((u) => !((useLists && u.list !== null && u.list < candLists.length) || (useGroup && u.list === 0)));
  const byRole = (arr, r) => arr.filter((x) => x.role === r);
  const flatSlots = useGroup ? slots.filter((x) => x.group !== candGroups[0].key) : slots;

  if (useGroup) {
    const gk = candGroups[0].key;
    const items = orig.lists[0].items;
    for (let i = 0; i < candGroups[0].count; i++) {
      const ms = slots.filter((x) => x.group === gk && x.member === i);
      if (i >= items.length) { props.push([gk + 'Show' + (i + 1), 'false']); continue; }
      // inside a card, headings and body text pair in document order (a tier name may be an h3 on
      // one side and a styled span on the other); actions and list items pair among themselves
      for (const cls of ITEM_CLASSES) {
        const o = items[i].units.filter((u) => cls.includes(u.role)), sl = ms.filter((x) => cls.includes(x.role));
        const n = Math.min(o.length, sl.length);
        for (let k = 0; k < n; k++) {
          props.push([sl[k].key, `<>${o[k].src}</>`]);
          if (sl[k].href && o[k].href) props.push([sl[k].key + 'Href', o[k].href]);
          carried.push({ role: o[k].role, text: o[k].text });
        }
        for (let k = n; k < o.length; k++) dropped.push({ role: o[k].role, text: o[k].text });
        for (let k = n; k < sl.length; k++) demo.push({ role: sl[k].role, key: sl[k].key, text: sl[k].demo });
      }
      const bs = ms.find((x) => x.role === 'bullets');
      if (bs) {
        // the owner's bullets, or none — a design's demo feature list is never presented as theirs
        props.push([bs.key, JSON.stringify(items[i].bullets)]);
        if (items[i].bullets.length) carried.push({ role: 'item', text: items[i].bullets.join(', ') });
      } else if (items[i].bullets.length) dropped.push({ role: 'item', text: items[i].bullets.join(', ') });
    }
    for (let i = candGroups[0].count; i < items.length; i++) for (const u of items[i].units) dropped.push({ role: u.role, text: u.text });
  }

  for (const role of CONTENT_ROLES) {
    const o = byRole(flat, role), s = byRole(flatSlots, role);
    const n = Math.min(o.length, s.length);
    for (let i = 0; i < n; i++) {
      props.push([s[i].key, `<>${o[i].src}</>`]);
      if (s[i].href && o[i].href) props.push([s[i].key + 'Href', o[i].href]);
      carried.push({ role, text: o[i].text });
    }
    for (let i = n; i < o.length; i++) dropped.push({ role, text: o[i].text });
    for (let i = n; i < s.length; i++) {
      // a design's extra demo button ("Get a Demo" -> "#") is hidden, never shown as the owner's offer
      if (s[i].hideable && !opts.keepDemoActions) { props.push([s[i].key + 'Show', 'false']); hidden.push(s[i].demo); continue; }
      demo.push({ role, key: s[i].key, text: s[i].demo });
    }
  }
  if ((cand.logoRows || []).length) hidden.push(`${cand.logoRows.length} row(s) of demo brand logos`);

  if (useLists) {
    candLists.forEach((cl, li) => {
      const ol = orig.lists[li];
      if (!ol) return;
      const items = ol.items.map((it) => {
        const obj = {};
        for (const role of CONTENT_ROLES) {
          const fields = cl.fields.filter((f) => f.role === role);
          const vals = it.units.filter((u) => u.role === role);
          fields.forEach((f, k) => { if (vals[k]) { obj[f.field] = vals[k].text; carried.push({ role, text: vals[k].text }); } });
          for (let k = fields.length; k < vals.length; k++) dropped.push({ role, text: vals[k].text });
        }
        const hrefF = cl.fields.find((f) => f.role === 'href');
        const act = it.units.find((u) => u.role === 'action' && u.href);
        if (hrefF && act) obj[hrefF.field] = JSON.parse(act.href);
        const bulletsF = cl.fields.find((f) => f.role === 'bullets');
        if (bulletsF && it.bullets.length) { obj[bulletsF.field] = it.bullets; carried.push({ role: 'item', text: it.bullets.join(', ') }); }
        const imgF = cl.fields.find((f) => f.role === 'image');
        if (imgF && it.images[0] && it.images[0].src) obj[imgF.field] = JSON.parse(it.images[0].src);
        return obj;
      });
      props.push([cl.key, JSON.stringify(items)]);
      if (ol.items.length !== cl.demoCount) demo.push({ role: 'list', key: cl.key, text: `${ol.items.length} of your items (design shows ${cl.demoCount})` });
    });
  }

  const oi = orig.images, si = slots.filter((x) => x.role === 'image');
  for (let i = 0; i < Math.min(oi.length, si.length); i++) {
    if (oi[i].src) props.push([si[i].key, oi[i].src]);
    if (oi[i].alt) props.push([si[i].key + 'Alt', oi[i].alt]);
    carried.push({ role: 'image', text: oi[i].alt || oi[i].src });
  }
  for (let i = si.length; i < oi.length; i++) dropped.push({ role: 'image', text: oi[i].alt || oi[i].src });
  for (let i = oi.length; i < si.length; i++) {
    if (si[i].localDemo && opts.placeholder) {
      props.push([si[i].key, JSON.stringify(opts.placeholder)]);
      demo.push({ role: 'image', key: si[i].key, text: 'image placeholder — add your own' });
    }
  }
  const op = orig.inputs, sp = slots.filter((x) => x.role === 'placeholder');
  for (let i = 0; i < Math.min(op.length, sp.length); i++) if (op[i].placeholder) props.push([sp[i].key, op[i].placeholder]);
  return { props, carried, dropped, demo, hidden };
}

export function contentProp(prop, props) {
  if (!props.length) return '';
  return ` ${prop}={{ ${props.map(([k, v]) => `${k}: ${v}`).join(', ')} }}`;
}

/** How much content the original holds (the fit denominator). */
export function contentCount(orig) {
  return orig.units.length + orig.images.length + orig.lists.reduce((n, l) => n + l.items.reduce((m, it) => m + it.bullets.length, 0), 0);
}

export function shapeOf(u) {
  const c = (r) => u.units.filter((x) => x.role === r).length;
  return { heading: c('heading'), text: c('text'), action: c('action'), item: c('item'), image: u.images.length, lists: u.lists.length };
}
