/**
 * try-on overlay — the picker the owner uses (vanilla JS, shadow DOM, dev-only).
 * Served by tryon_server.py with a `window.__TRYON__ = {port, token, project}` prelude.
 *
 * Flow: click Try-On -> hover outlines -> click an element -> panel with REAL candidates from the
 * measured MIT registry -> Try -> the agent installs + swaps -> Keep / Revert.
 * Nothing here edits the page: previews arrive via the dev server's own HMR (the agent does the write).
 *
 * Honesty rules (learned live):
 *  - never present a fallback as an answer: no match -> placeholder option, Try stays disabled
 *  - a section (block) is never swappable in v1: say so and point at the pieces inside it
 *  - the request carries what the element IS and whether the owner confirmed a re-scope
 *  - while a request is in flight no control is clickable twice; Keep/Revert act on the last tried
 *    component, never on "whatever is under the cursor"
 */
(function () {
  if (window.__TRYON_LOADED__) return;
  window.__TRYON_LOADED__ = true;
  var CFG = window.__TRYON__ || { port: 7799, token: '', project: '?' };
  var BASE = 'http://127.0.0.1:' + CFG.port;

  /* ------------------------------------------------------------------ shadow UI */
  var host = document.createElement('div');
  host.setAttribute('data-tryon-ui', '1');
  host.style.cssText = 'position:fixed;z-index:2147483646;top:0;left:0;width:0;height:0;';
  var root = host.attachShadow ? host.attachShadow({ mode: 'open' }) : host;
  (document.body || document.documentElement).appendChild(host);

  var css = document.createElement('style');
  css.textContent = [
    ':host, * { box-sizing: border-box; font: 13px/1.45 ui-sans-serif, system-ui, Segoe UI, sans-serif; }',
    '.pill{position:fixed;right:16px;bottom:16px;padding:8px 14px;border-radius:999px;background:#111;color:#fff;',
    'cursor:pointer;box-shadow:0 6px 24px rgba(0,0,0,.28);user-select:none;letter-spacing:.2px}',
    '.pill.on{background:#3b82f6}',
    '.outline{position:fixed;pointer-events:none;border:2px solid #3b82f6;border-radius:4px;',
    'background:rgba(59,130,246,.08);transition:all .04s linear}',
    '.tag{position:fixed;pointer-events:none;background:#111;color:#fff;border-radius:6px;padding:4px 8px;',
    'max-width:560px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;opacity:.95}',
    '.panel{position:fixed;right:16px;bottom:64px;width:440px;max-height:72vh;overflow:auto;background:#fff;color:#111;',
    'border:1px solid #d4d4d8;border-radius:12px;box-shadow:0 18px 50px rgba(0,0,0,.22);padding:12px 14px}',
    '.row{display:flex;gap:8px;align-items:center;justify-content:space-between;padding:6px 0;border-top:1px solid #eee}',
    '.row:first-child{border-top:0}',
    '.muted{color:#71717a}.small{font-size:12px}',
    '.note{margin:8px 0;padding:8px;border-radius:8px;background:#fffbeb;color:#78350f;white-space:pre-wrap}',
    '.scope{margin:4px 0;color:#52525b}',
    'select,button{font:inherit;border:1px solid #d4d4d8;border-radius:8px;padding:4px 8px;background:#fff;cursor:pointer}',
    'button.primary{background:#111;color:#fff;border-color:#111}',
    'button.ghost{background:transparent}',
    'button[disabled]{opacity:.45;cursor:not-allowed}',
    'a{color:#3b82f6;text-decoration:none}',
    '.status{margin-top:8px;padding:8px;border-radius:8px;background:#f4f4f5;white-space:pre-wrap}',
    '.status.err{background:#fef2f2;color:#991b1b}',
    '.foot{position:sticky;bottom:-12px;margin:0 -14px;padding:2px 14px 12px;background:#fff}',
    'code{background:#f4f4f5;border-radius:4px;padding:1px 4px}',
    'label.chk{display:flex;gap:6px;align-items:center;margin:6px 0;cursor:pointer}',
  ].join('');
  root.appendChild(css);

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  /* ------------------------------------------------------------------ state */
  var on = false, frozen = null, outline = null, tagLabel = null, panel = null;
  var elementInfo = null, slots = [], candidates = [];
  var lastRequest = null;      // {candidate, slot, elementSlot, rescope, element, id, saveId, answered, saved, reverted}
  var inFlight = false;        // a request is with the agent: no control may fire twice
  var pending = null;          // {id, kind, timer} — the ONE request this panel waits on a reply for

  var pill = el('div', 'pill', 'Try-On');
  pill.title = 'Try real components on this page (dev-only)';
  root.appendChild(pill);

  function cssPath(node) {
    var parts = [];
    while (node && node.nodeType === 1 && parts.length < 6) {
      var s = node.tagName.toLowerCase();
      if (node.id) { parts.unshift(s + '#' + node.id); break; }
      var cls = (node.getAttribute('class') || '').split(/\s+/).filter(Boolean).slice(0, 2);
      if (cls.length) s += '.' + cls.join('.');
      parts.unshift(s);
      node = node.parentElement;
    }
    return parts.join(' > ');
  }

  function srcOf(node) {
    var n = node;
    while (n && n.getAttribute) {
      var v = n.getAttribute('data-tryon-src');
      if (v) return v;
      n = n.parentElement;
    }
    return null;
  }

  /* LADDER-START
   * Slot inference: what could be swapped here. First hit wins; pure DOM (the node, its ancestors,
   * its data-tryon-src) so it is testable without a browser (templates/tryon/test-ladder.cjs extracts
   * THIS block). Order: declared identity -> interactive -> outward landmark -> FAQ list -> priced
   * card -> pricing grid -> source file -> class conventions -> honest null (never a default).
   * Measured on a real app: pricing grid -> pricing, tier card -> card, CTA button -> button,
   * header -> navbar, header button -> button, FAQ list -> faq, footer -> footer (7/7).
   */
  var BLOCK_SLOTS = ['cta', 'faq', 'footer', 'hero', 'login', 'navbar', 'pricing', 'signup', 'testimonials'];

  function ttag(n) { return (n.tagName || '').toLowerCase(); }
  function tattr(n, a) { return (n.getAttribute ? (n.getAttribute(a) || '') : ''); }
  function tclass(n) { return tattr(n, 'class').toLowerCase(); }
  function ladderSrc(n) {
    var up = n;
    while (up && up.getAttribute) { var v = up.getAttribute('data-tryon-src'); if (v) return v; up = up.parentElement; }
    return null;
  }
  function that(n) { return (tclass(n) + ' ' + tattr(n, 'role') + ' ' + tattr(n, 'aria-label')).toLowerCase(); }
  function tkids(n) { var out = []; if (n && n.children) for (var i = 0; i < n.children.length; i++) out.push(n.children[i]); return out; }
  function ttext(n) { return ((n && n.textContent) || '').toLowerCase().replace(/\s+/g, ' ').trim(); }

  function anyDesc(n, fn, depth) {
    depth = depth || 0;
    if (depth > 4) return false;
    var k = tkids(n);
    for (var i = 0; i < k.length; i++) { if (fn(k[i])) return true; if (anyDesc(k[i], fn, depth + 1)) return true; }
    return false;
  }
  function isActionNode(x) { var t = ttag(x); return t === 'button' || t === 'a' || t === 'input' || tattr(x, 'role') === 'button'; }
  function isHeadingNode(x) { var t = ttag(x); if (/^h[1-6]$/.test(t)) return true; return /\bfont-semibold\b|\bfont-bold\b|\bfont-medium\b/.test(tclass(x)) && ttext(x).length > 1; }
  function hasHeading(n) { return anyDesc(n, isHeadingNode, 1); }
  function hasAction(n) { return anyDesc(n, isActionNode, 0); }
  function hasPrice(n) {
    // a real price token only: "Free"-style words appear in ordinary copy and would miscall cards
    return /([$€£]\s?\d)|(\d+\s?[$€£])/.test(ttext(n));
  }
  function pricedCard(n) {
    if (!/^(div|section|article|li|aside)$/.test(ttag(n))) return false;
    if (!hasHeading(n) || !hasPrice(n) || !hasAction(n)) return false;
    // innermost wins: any node CONTAINING a priced card is the container, not a card
    if (containsPricedCard(n, 0)) return false;
    return true;
  }
  function containsPricedCard(n, depth) {
    if (depth > 3) return false;
    var k = tkids(n);
    for (var i = 0; i < k.length; i++) {
      if (pricedCard(k[i])) return true;
      if (containsPricedCard(k[i], depth + 1)) return true;
    }
    return false;
  }
  function qaGroup(n) {
    var k = tkids(n);
    if (k.length < 2) return false;
    var q = 0;
    for (var i = 0; i < k.length; i++) {
      var t = ttag(k[i]);
      if ((t === 'dt' || t === 'summary' || /^h[1-6]$/.test(t)) && /\?\s*$/.test((k[i].textContent || '').trim())) q++;
    }
    if (q >= 2) return true;                                     // dt/summary pairs directly
    var groups = 0;                                              // wrapped pairs: question node + answer node
    for (var j = 0; j < k.length; j++) {
      var kk = tkids(k[j]);
      if (kk.length < 2) continue;
      var hasQ = false, hasA = false;
      for (var m = 0; m < kk.length; m++) {
        var tt = ttag(kk[m]);
        if ((tt === 'dt' || tt === 'summary' || /^h[1-6]$/.test(tt)) && /\?\s*$/.test((kk[m].textContent || '').trim())) hasQ = true;
        else hasA = true;
      }
      if (hasQ && hasA) groups++;
    }
    return groups >= 2;
  }
  function pricingGrid(n) {
    var k = tkids(n), cards = 0;
    for (var i = 0; i < k.length; i++) if (pricedCard(k[i])) cards++;
    return cards >= 2;
  }

  // the source file an element was rendered from — kept BELOW the structural rules (a basename lies)
  function pathSlot(p) {
    if (!p) return null;
    var f = p.split('/').pop().toLowerCase();
    var map = [['siteheader', 'navbar'], ['header', 'navbar'], ['navbar', 'navbar'], ['sidenav', 'navbar'],
      ['footer', 'footer'], ['hero', 'hero'], ['faq', 'faq'], ['pricing', 'pricing'],
      ['testimonial', 'testimonials'], ['signin', 'login'], ['sign-in', 'login'], ['login', 'login'],
      ['signup', 'signup'], ['sign-up', 'signup'], ['register', 'signup'], ['dialog', 'dialog'],
      ['modal', 'dialog'], ['accordion', 'accordion'], ['card', 'card'], ['button', 'button'],
      ['badge', 'badge'], ['input', 'input'], ['field', 'input'], ['avatar', 'avatar'], ['table', 'table'],
      ['pagination', 'pagination'], ['dropdown', 'dropdown-menu'], ['tabs', 'tabs']];
    for (var i = 0; i < map.length; i++) if (f.indexOf(map[i][0]) !== -1) return map[i][1];
    return null;
  }

  function classSlot(n) {
    var h = that(n);
    if (/\bcta\b|\bbtn\b|button/.test(h)) return { slot: 'cta', why: 'the CSS class says cta/button' };
    if (/\bcard\b/.test(h)) return { slot: 'card', why: 'the CSS class says card' };
    if (/\bhero\b/.test(h)) return { slot: 'hero', why: 'the CSS class says hero' };
    if (/pricing/.test(h)) return { slot: 'pricing', why: 'the CSS class says pricing' };
    if (/testimonial/.test(h)) return { slot: 'testimonials', why: 'the CSS class says testimonials' };
    if (/faq/.test(h)) return { slot: 'faq', why: 'the CSS class says faq' };
    if (/accordion/.test(h)) return { slot: 'accordion', why: 'the CSS class says accordion' };
    if (/sign-?in|log-?in/.test(h)) return { slot: 'login', why: 'the CSS class says login' };
    if (/sign-?up|register/.test(h)) return { slot: 'signup', why: 'the CSS class says signup' };
    return null;
  }

  function guessSlot(node) {
    if (!node || node.nodeType !== 1) return null;
    // R3 target: the OUTERMOST landmark within 8 ancestors, used only if nothing nearer fires
    var landmark = null, up = node, d = 0;
    while (up && up.getAttribute && d < 8) {
      var t = ttag(up);
      if (t === 'footer') landmark = { slot: 'footer', why: 'this sits in the footer' };
      else if (t === 'header' || t === 'nav' || tattr(up, 'role') === 'navigation') landmark = { slot: 'navbar', why: 'this sits in the site header navigation' };
      up = up.parentElement; d++;
    }
    var n = node, depth = 0;
    while (n && n.getAttribute && depth < 6) {
      // R1 declared identity — the strongest, cheapest signal
      var slotAttr = tattr(n, 'data-slot');
      if (slotAttr) {
        var s = slotAttr.toLowerCase().replace(/[-_ ]/g, '-');
        return { slot: s, why: 'this component declares data-slot="' + slotAttr + '"' };
      }
      // R2 interactive element
      var tag = ttag(n);
      if (tag === 'button' || tattr(n, 'role') === 'button') return { slot: 'button', why: 'it is a button' };
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return { slot: 'input', why: 'it is an input field' };
      if (tag === 'a' && /\b(btn|button)\b/.test(tclass(n))) return { slot: 'button', why: 'it is a link styled as a button' };
      // R4 FAQ list
      if (qaGroup(n)) return { slot: 'faq', why: 'it is a list of questions and answers' };
      // R6 priced plan card (innermost) — before R5 so a card inside a grid is a card
      if (pricedCard(n)) return { slot: 'card', why: 'it is a plan card with a price and an action' };
      // R5 pricing grid
      if (pricingGrid(n)) return { slot: 'pricing', why: 'it is a grid of priced plans' };
      n = n.parentElement;
      depth++;
    }
    if (landmark) return landmark;
    var src = ladderSrc(node);
    var ps = pathSlot(src);
    if (ps) return { slot: ps, why: 'it comes from ' + src.split('/').pop() };
    var n2 = node, d2 = 0;
    while (n2 && n2.getAttribute && d2 < 4) {
      var cs = classSlot(n2);
      if (cs) return cs;
      n2 = n2.parentElement;
      d2++;
    }
    return null;   // R9 — an honest null; the panel must ask, never default
  }
  /* LADDER-END */

  /* ------------------------------------------------------------------ hover */
  function draw(node) {
    var r = node.getBoundingClientRect();
    if (!outline) { outline = el('div', 'outline'); root.appendChild(outline); }
    outline.style.left = r.left + 'px';
    outline.style.top = r.top + 'px';
    outline.style.width = r.width + 'px';
    outline.style.height = r.height + 'px';
    if (!tagLabel) { tagLabel = el('div', 'tag'); root.appendChild(tagLabel); }
    var src = srcOf(node);
    tagLabel.textContent = node.tagName.toLowerCase() + (src ? '  ' + src : '  (source unknown — the agent will locate it)');
    tagLabel.style.left = r.left + 'px';
    tagLabel.style.top = Math.max(0, r.top - 26) + 'px';
  }

  function clearDraw() {
    if (outline) outline.remove();
    if (tagLabel) tagLabel.remove();
    outline = tagLabel = null;
  }

  function isOwnEvent(e) {
    // composed path first: catches clicks with no coordinates (keyboard, .click()) and shadow retargeting
    if (e.composedPath) {
      var p = e.composedPath();
      for (var i = 0; i < p.length; i++) if (p[i] === host) return true;
    }
    var n = document.elementFromPoint(e.clientX, e.clientY);
    return !!(n && (n === host || (n.getAttribute && n.getAttribute('data-tryon-ui'))));
  }

  function onMove(e) {
    if (!on || frozen) return;
    if (isOwnEvent(e)) return;
    var n = document.elementFromPoint(e.clientX, e.clientY);
    if (!n) return;
    draw(n);
  }

  function onClick(e) {
    if (!on) return;
    if (isOwnEvent(e)) return;
    var n = document.elementFromPoint(e.clientX, e.clientY);
    if (!n) return;
    e.preventDefault();
    e.stopPropagation();
    frozen = n;
    elementInfo = {
      file: null, line: null,
      tag: n.tagName.toLowerCase(),
      text: (n.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120),
      selector: cssPath(n),
      src: srcOf(n) || null,
    };
    if (elementInfo.src) {
      var m = elementInfo.src.match(/^(.*):(\d+)$/);
      if (m) { elementInfo.file = m[1]; elementInfo.line = Number(m[2]); }
    }
    openPanel(n);
  }

  /* ------------------------------------------------------------------ panel */
  var HUMAN = {
    cta: 'Call-to-action section', faq: 'Questions & answers list', footer: 'Footer',
    hero: 'Hero / top banner', login: 'Login form', navbar: 'Top navigation', pricing: 'Pricing section',
    signup: 'Sign-up form', testimonials: 'Testimonials', accordion: 'Accordion', avatar: 'Avatar',
    badge: 'Badge', breadcrumb: 'Breadcrumb', button: 'Button', card: 'Card', checkbox: 'Checkbox',
    command: 'Command palette', dialog: 'Dialog', 'dropdown-menu': 'Dropdown menu', input: 'Input field',
    pagination: 'Pagination', popover: 'Popover', table: 'Table', tabs: 'Tabs',
  };
  function humanSlot(s) { return HUMAN[s] || s.replace(/-/g, ' ').replace(/^\w/, function (c) { return c.toUpperCase(); }); }
  function kindOf(s) {
    for (var i = 0; i < slots.length; i++) if (slots[i].slot === s && slots[i].slot_kind) return slots[i].slot_kind;
    return BLOCK_SLOTS.indexOf(s) !== -1 ? 'block' : 'primitive';
  }
  var TYPE_WORDS = { 'registry:ui': 'component', 'registry:example': 'demo example', 'registry:block': 'section demo' };

  function post(type, extra) {
    var body = Object.assign({
      type: type,
      element: elementInfo,
      slot: sel.value,
      elementSlot: sel.__g ? sel.__g.slot : null,
      rescope: !!(sel.__rescope && sel.__rescope.checked),
    }, extra || {});
    // text/plain keeps this a "simple" request: no preflight, no CORS surprises in any browser
    return fetch(BASE + '/event?token=' + encodeURIComponent(CFG.token), {
      method: 'POST', headers: { 'content-type': 'text/plain;charset=UTF-8' }, body: JSON.stringify(body),
    }).then(function (r) { return r.json(); });
  }

  function busy(state) {
    inFlight = !!state;
    if (!panel) return;
    if (state) {
      var bs = panel.querySelectorAll('button');
      for (var i = 0; i < bs.length; i++) if (bs[i] !== panel.__x) bs[i].setAttribute('disabled', '');
    } else refresh();
  }

  function postOr(type, extra, okMsg, kind) {
    if (inFlight) return;
    status('sending…');
    busy(true);
    return post(type, extra)
      .then(function (r) {
        if (!r || r.id == null) { busy(false); status('the helper answered without a request id — nothing was sent', true); return null; }
        status(okMsg.replace('%N%', r.id));
        // The reply for THIS id is what clears busy (any reply used to, and a replayed reply could
        // release the panel early). If none arrives, free the panel after 2 min and say what to check
        // (measured: an async agent's turn — polling loop wake, guard, fetch, stage, reply — can take
        // ~1 min, so the old 45s window expired before the first real answer landed)
        // instead of sitting on “sending…” forever. Past 2 min the request is still PENDING on the
        // server, so the panel must not claim the swap failed: the timeout says only what is true, and
        // a late answer (measured at 642s and 17767s) re-arms the buttons in the SSE handler below.
        pending = { id: r.id, kind: kind || type, timer: setTimeout(function () {
          if (pending && pending.id === r.id) {
            pending = null;
            busy(false);
            status('no answer for request #' + r.id + ' after 2 min — the agent may still be working on it. ' +
              'If an answer arrives later it will show here and Undo will work. Check: ' +
              'py scripts/tryon_server.py status --project .', true);
          }
        }, 120000) };
        return r.id;
      })
      .catch(function (e) { busy(false); status('could not reach the helper on 127.0.0.1:' + CFG.port + ' — ' + e.message, true); return null; });
  }

  var sel = document.createElement('select');
  sel.onchange = function () { refresh(); };

  function status(msg, isErr) {
    if (!panel) return;
    var s = panel.querySelector('.status');
    s.textContent = msg;
    s.className = 'status' + (isErr ? ' err' : '');
  }

  function plainMeta(c) {
    var bits = [c.registry.charAt(0).toUpperCase() + c.registry.slice(1), TYPE_WORDS[c.type] || c.type];
    if (c.base && c.base !== 'none') bits.push('base: ' + c.base);
    else bits.push('no shared base');
    if (c.compat === 'different base') bits.push('different base — needs setup');
    return bits.join(' · ');
  }

  function scopeLine(scope, n) {
    if (!scope) return '';
    if (scope.base && scope.base !== 'unknown') {
      var s = 'Matching your setup: ' + (scope.base_label || scope.base) +
        (scope.lineage ? ' · ' + scope.lineage : '') + ' — ' + n + ' ready to try';
      if (scope.hidden) s += ', ' + scope.hidden + ' hidden' +
        (scope.hidden_bases && scope.hidden_bases.length ? ' (they need ' + scope.hidden_bases.join('/') + ')' : '');
      // demo rows the server's scope kept out of THIS list (T09): only a POSITIVE count renders —
      // an absent or 0 hidden_demos must add nothing at all
      if (scope.hidden_demos > 0) s += ' + ' + scope.hidden_demos + ' demos hidden';
      return s;
    }
    return 'We could not read your project setup — candidates are unscoped; the agent verifies before writing.';
  }

  function loadCandidates(slot) {
    if (!panel) return;
    var list = panel.querySelector('.cands');
    var scopeEl = panel.querySelector('.scope');
    var asked = slot;
    list.textContent = 'loading…';
    var u = BASE + '/catalog?slot=' + encodeURIComponent(slot);
    if (elementInfo && elementInfo.file) {
      u += '&file=' + encodeURIComponent(elementInfo.file) + '&line=' + encodeURIComponent(elementInfo.line || 0);
    }
    fetch(u)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (sel.value !== asked) return;               // the owner moved on: stale rows never show
        var rows = Array.isArray(data) ? data : (data.items || []);
        if (scopeEl) scopeEl.textContent = Array.isArray(data) ? '' : scopeLine(data.scope, rows.length);
        candidates = rows;
        list.textContent = '';
        if (!rows.length) { list.textContent = 'Nothing to try for this part yet.'; return; }
        rows.forEach(function (c) {
          var row = el('div', 'row');
          var left = el('div');
          left.appendChild(el('div', null, c.item));
          left.appendChild(el('div', 'muted small', plainMeta(c)));
          var right = el('div');
          var t = el('button', 'primary', 'Try');
          t.onclick = function () {
            lastRequest = { candidate: c, slot: sel.value, elementSlot: sel.__g ? sel.__g.slot : null, rescope: !!sel.__rescope && sel.__rescope.checked, element: elementInfo, id: null, saveId: null, answered: false, saved: false, reverted: false };
            postOr('preview', { candidate: c }, 'request #%N% sent — trying "' + c.item + '" in place of ' +
              (elementInfo.file ? elementInfo.file.split('/').pop() + ':' + elementInfo.line : elementInfo.tag) +
              '. Keep or Undo below when you see it.', 'preview').then(function (id) {
              if (id != null && lastRequest && lastRequest.candidate === c) lastRequest.id = id;
            });
          };
          var link = el('a', null, 'source');
          link.href = c.item_url; link.target = '_blank';
          link.title = 'open this component on the registry site';
          right.appendChild(t);
          right.appendChild(link);
          row.appendChild(left);
          row.appendChild(right);
          list.appendChild(row);
        });
      })
      .catch(function (e) { list.textContent = 'catalog error: ' + e.message; });
  }

  function refresh() {
    if (!panel) return;
    var list = panel.querySelector('.cands');
    var note = panel.querySelector('.note');
    var g = sel.__g, rescope = sel.__rescope;
    var chosen = sel.value;
    var k = chosen ? kindOf(chosen) : null;

    // what the list may show, and whether Try is allowed at all
    var allow = false;
    if (!chosen) {
      note.textContent = 'We could not work out what this part of your page is.\nChoose it from the list — nothing changes until you press Try.';
    } else if (g && kindOf(g.slot) === 'block') {
      note.textContent = 'This is a whole section of your page (' + humanSlot(g.slot) + ').\nSwapping whole sections is not ready yet — nothing here will change. Click a single piece inside it instead: a card, a button, a link.';
    } else if (k === 'block') {
      note.textContent = '“' + humanSlot(chosen) + '” is a whole section. Whole-section swaps are not ready yet, so nothing will be sent.\nPick the single piece you want to change — a card, a button, a field.';
    } else if (!g) {
      note.textContent = 'You picked “' + humanSlot(chosen) + '”.\nNothing changes until you press Try — and before writing anything the agent checks it against this element.';
      allow = true;
    } else if (chosen === g.slot) {
      note.textContent = 'Looks like: ' + humanSlot(g.slot) + ' — ' + g.why + '.';
      allow = true;
    } else {
      note.textContent = 'You picked “' + humanSlot(chosen) + '”, but this element is a ' + humanSlot(g.slot) + '.\nNothing will be sent unless you confirm it below.';
      allow = !!rescope.checked;
    }

    if (rescope) rescope.parentNode.style.display = (g && chosen && chosen !== g.slot && kindOf(g.slot) !== 'block') ? 'flex' : 'none';
    if (rescope) rescope.checked = rescope.checked && !!(g && chosen && chosen !== g.slot);

    // candidates load once per chosen slot — refresh never re-fetches what is already listed
    if (allow && sel.__loaded !== chosen) { sel.__loaded = chosen; loadCandidates(chosen); }
    if (!allow) { sel.__loaded = null; if (list.textContent) list.textContent = ''; var sc = panel.querySelector('.scope'); if (sc) sc.textContent = ''; }

    var tbs = list.querySelectorAll ? list.querySelectorAll('button') : [];
    for (var i = 0; i < tbs.length; i++) {
      if (allow && !inFlight) tbs[i].removeAttribute('disabled'); else tbs[i].setAttribute('disabled', '');
    }
    var keep = panel.__keep, rev = panel.__revert, sav = panel.__save;
    var act = !!(lastRequest && !inFlight);
    if (keep) { if (act) keep.removeAttribute('disabled'); else keep.setAttribute('disabled', ''); }
    if (rev) { if (act) rev.removeAttribute('disabled'); else rev.setAttribute('disabled', ''); }
    // Save unlocks only once the try was ANSWERED (staged files exist then), and locks again after
    // a Save or after Revert (there is nothing to copy from a reverted preview).
    if (sav) {
      var canSave = !!(lastRequest && lastRequest.id != null && lastRequest.answered &&
                       !lastRequest.saved && !lastRequest.reverted && !inFlight);
      if (canSave) sav.removeAttribute('disabled'); else sav.setAttribute('disabled', '');
      sav.textContent = (lastRequest && lastRequest.saved) ? 'Saved ✓' : 'Save to my library';
    }
    if (!status.__touched) status('Pick a component below — nothing changes until you press Try.');
  }

  function openPanel(node) {
    if (panel) panel.remove();
    panel = el('div', 'panel');
    panel.style.pointerEvents = 'auto';
    // BUBBLE phase: keeps the app from also reacting to clicks without eating the panel's own.
    // (a capture-phase stopPropagation here silently killed Try / Keep / Revert / Close)
    panel.addEventListener('click', function (e) { e.stopPropagation(); });

    var head = el('div', 'row');
    var headText = el('div');
    headText.appendChild(el('b', null, 'Try a component in place of this element'));
    headText.appendChild(el('div', 'muted small', elementInfo.selector));
    headText.appendChild(el('div', 'small', elementInfo.src || 'source unknown — the agent will locate it by text'));
    if (elementInfo.text) headText.appendChild(el('div', 'muted small', '“' + elementInfo.text.slice(0, 80) + (elementInfo.text.length > 80 ? '…' : '') + '”'));
    var x = el('button', 'ghost', '✕');
    x.title = 'Close (Esc)';
    x.onclick = closePanel;
    panel.__x = x;
    head.appendChild(headText);
    head.appendChild(x);
    panel.appendChild(head);

    var g = guessSlot(node);
    sel.__g = g;
    var slotRow = el('div', 'row');
    slotRow.appendChild(el('span', 'muted small', 'What this is'));
    sel.textContent = '';
    var ph = document.createElement('option');
    ph.value = '';
    ph.textContent = g ? '' : 'Choose what this part is…';
    if (g) ph.textContent = humanSlot(g.slot) + ' (matched)';
    sel.appendChild(ph);
    if (g) { ph.value = g.slot; }
    var list = slots.slice();
    if (g && !list.some(function (s) { return s.slot === g.slot; })) list.unshift({ slot: g.slot, slot_kind: kindOf(g.slot) });
    list.forEach(function (s) {
      if (g && s.slot === g.slot) return;                       // the matched option is the placeholder row
      var o = document.createElement('option');
      o.value = s.slot;
      o.textContent = humanSlot(s.slot) + (s.n_free ? ' — ' + s.n_free + ' ready to try' : '') + (kindOf(s.slot) === 'block' ? ' (whole section)' : '');
      sel.appendChild(o);
    });
    sel.value = g ? g.slot : '';
    slotRow.appendChild(sel);
    panel.appendChild(slotRow);

    var note = el('div', 'note');
    panel.appendChild(note);

    var rescope = document.createElement('input');
    rescope.type = 'checkbox';
    var rescopeLbl = el('label', 'chk');
    rescopeLbl.appendChild(rescope);
    var rescopeTxt = el('span', 'small', '');
    rescopeLbl.appendChild(rescopeTxt);
    panel.appendChild(rescopeLbl);
    sel.__rescope = rescope;
    rescope.onchange = function () {
      if (g) rescopeTxt.textContent = 'Yes, try it anyway in place of this ' + humanSlot(g.slot) + ' — I know it is a different kind.';
      refresh();
    };
    if (g) rescopeTxt.textContent = 'Yes, try it anyway in place of this ' + humanSlot(g.slot) + ' — I know it is a different kind.';

    var scope = el('div', 'scope');
    panel.appendChild(scope);
    var cands = el('div', 'cands');
    panel.appendChild(cands);
    var st = el('div', 'status', 'Pick a component below — nothing changes until you press Try.');
    panel.appendChild(st);

    // Save lives in its own row ABOVE Keep/Undo/Close: it is a different destination (his own
    // library, for other projects) and folding it into the Keep row read as one action.
    var saveRow = el('div', 'row');
    var save = el('button', 'primary', 'Save to my library');
    save.title = 'keeps a copy of the tried component (with everything it needs) in your own component library for other projects';
    save.setAttribute('disabled', '');
    save.onclick = function () {
      if (!lastRequest || inFlight || !lastRequest.answered || lastRequest.saved || lastRequest.reverted) return;
      var forTry = lastRequest;      // identity guard: the panel may be closed/reopened mid-flight
      postOr('save', { request: forTry.id, element: forTry.element, candidate: forTry.candidate,
                       slot: forTry.slot, elementSlot: forTry.elementSlot },
        'saving request #%N% — the agent copies the exact staged files into your library and answers here.', 'save')
        .then(function (id) {
          // the save's OWN request id (it is a new request, not the preview): an ok answer that lands
          // after the 2-min timeout must still find this try — the SSE late-answer branch matches on it
          if (id != null && lastRequest === forTry) forTry.saveId = id;
        });
    };
    panel.__save = save;
    saveRow.appendChild(save);
    // Save/Keep/Undo/Close live in a sticky footer: with a long candidate list they used to end up
    // below the fold — the owner had to scroll the panel past every candidate to answer a try.
    var foot = el('div', 'foot');
    foot.appendChild(saveRow);

    var actions = el('div', 'row');
    var keep = el('button', 'primary', 'Keep this version');
    keep.title = 'keeps the last one you tried and deletes the other candidates staged for it';
    keep.onclick = function () {
      if (!lastRequest || inFlight) return;
      postOr('accept', { element: lastRequest.element, candidate: lastRequest.candidate, elementSlot: lastRequest.elementSlot, rescope: lastRequest.rescope },
        'kept — request #%N% sent. The other candidates staged for it will be cleaned up.', 'accept');
    };
    panel.__keep = keep;
    var revert = el('button', 'ghost', 'Undo the last change');
    revert.title = 'restores the file exactly as it was before the last change';
    revert.onclick = function () {
      if (!lastRequest || inFlight) return;
      postOr('revert', { element: lastRequest.element, candidate: lastRequest.candidate, elementSlot: lastRequest.elementSlot },
        'undo asked — request #%N% sent. The file goes back exactly as it was.', 'revert').then(function (id) {
        if (id != null && lastRequest) lastRequest.reverted = true;   // Save locks: nothing staged anymore
      });
    };
    panel.__revert = revert;
    var close = el('button', 'ghost', 'Close');
    close.onclick = closePanel;
    actions.appendChild(keep); actions.appendChild(revert); actions.appendChild(close);
    foot.appendChild(actions);
    panel.appendChild(foot);

    root.appendChild(panel);
    status.__touched = false;
    refresh();
  }

  function closePanel() {
    if (panel) panel.remove();
    panel = null;
    frozen = null;
    clearDraw();
  }

  /* ------------------------------------------------------------------ toggle + sse */
  pill.onclick = function () {
    on = !on;
    pill.className = 'pill' + (on ? ' on' : '');
    pill.textContent = on ? 'Try-On ● pick an element' : 'Try-On';
    if (!on) closePanel();
  };

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { if (panel || frozen) closePanel(); else if (on) pill.click(); }
  }, true);

  fetch(BASE + '/slots').then(function (r) { return r.json(); }).then(function (rows) { slots = rows; }).catch(function () {});

  try {
    var es = new EventSource(BASE + '/events');
    es.onmessage = function (ev) {
      try {
        var m = JSON.parse(ev.data);
        if (!panel) return;
        status.__touched = true;
        var msg = (m.status === 'error' ? 'error: ' : '') + (m.message || JSON.stringify(m));
        if (!(pending && m.id === pending.id)) {
          // a replayed or foreign reply (the stream re-sends history on every reconnect): shown as
          // history with its #N prefix, but it never touches this panel's buttons or busy state.
          // The ONE exception: an ok answer to the panel's own last request that arrived after the
          // 2-min timeout — the swap (or save) it reports may well have landed, so it sets the same
          // flags the pending path sets and refreshes the buttons that act on them.
          var lateKind = null;
          if (lastRequest && m.status === 'ok' && m.id != null) {
            if (m.id === lastRequest.id) lateKind = 'preview';
            else if (lastRequest.saveId != null && m.id === lastRequest.saveId) lateKind = 'save';
          }
          if (lateKind) {
            if (lateKind === 'save') lastRequest.saved = true; else lastRequest.answered = true;
            refresh();
          }
          status((lateKind ? '(late answer for #' + m.id + ') ' : '(request #' + m.id + ') ') + msg, m.status === 'error');
          return;
        }
        if (pending.timer) clearTimeout(pending.timer);
        var kind = pending.kind;
        pending = null;
        if (kind === 'preview' && m.status === 'ok' && lastRequest) lastRequest.answered = true;
        if (kind === 'save' && m.status === 'ok' && lastRequest) lastRequest.saved = true;
        busy(false);
        status(msg, m.status === 'error');
      } catch (e) {}
    };
  } catch (e) {}

  document.addEventListener('mousemove', onMove, true);
  document.addEventListener('click', onClick, true);
})();
