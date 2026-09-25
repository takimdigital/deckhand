/**
 * Deckhand try-on overlay — injected by the local helper into the owner's dev site (never prod).
 * Pick any element -> choose what it is -> N real, licensed variants appear IN the page, wearing the
 * site's colours and the owner's own words -> ←/→ to compare (instant, client-side) -> Keep / Discard.
 * The page is never edited here: the helper writes source, the dev server's HMR re-renders.
 */
(function () {
  if (window.__DH_TRYON__) return;
  window.__DH_TRYON__ = true;
  var me = document.querySelector('script[data-dh-token]');
  var TOKEN = me ? me.getAttribute('data-dh-token') : '';
  var SS = 'dh-tryon-state';

  /* ------------------------------------------------------------ api */
  function api(name, body) {
    return fetch('/__dh/api/' + name, {
      method: body ? 'POST' : 'GET',
      headers: { 'content-type': 'application/json', 'x-dh-token': TOKEN },
      body: body ? JSON.stringify(body) : undefined,
    }).then(function (r) { return r.json(); });
  }

  /* ------------------------------------------------------------ ui shell */
  var host = document.createElement('div');
  host.setAttribute('data-dh-ui', '');
  host.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:2147483646';
  var root = host.attachShadow({ mode: 'open' });
  root.innerHTML = '<style>' + [
    ':host{all:initial}*{box-sizing:border-box;font:13px/1.45 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}',
    '.pill{pointer-events:auto;position:fixed;right:18px;bottom:18px;display:flex;align-items:center;gap:8px;padding:9px 14px;border-radius:999px;background:rgba(17,17,19,.92);color:#fff;cursor:pointer;box-shadow:0 8px 30px rgba(0,0,0,.28);user-select:none;border:1px solid rgba(255,255,255,.08)}',
    '.pill b{font-weight:600;letter-spacing:.2px}.pill.on{background:#2563eb}',
    '.dot{width:7px;height:7px;border-radius:50%;background:#34d399}',
    '.outline{position:fixed;pointer-events:none;border:2px solid #2563eb;border-radius:6px;background:rgba(37,99,235,.06);transition:all .05s}',
    '.tag{position:fixed;pointer-events:none;background:#111;color:#fff;border-radius:6px;padding:3px 8px;font-size:12px;white-space:nowrap;max-width:70vw;overflow:hidden;text-overflow:ellipsis}',
    '.panel{pointer-events:auto;position:fixed;right:18px;bottom:70px;width:380px;max-height:70vh;overflow:auto;background:#fff;color:#18181b;border:1px solid #e4e4e7;border-radius:14px;box-shadow:0 20px 60px rgba(0,0,0,.22);padding:14px}',
    '.h{font-weight:600;font-size:14px;margin:0 0 8px}.muted{color:#71717a}.small{font-size:12px}',
    '.crumb{display:flex;gap:8px;align-items:flex-start;padding:6px 8px;border-radius:8px;cursor:pointer}.crumb:hover{background:#f4f4f5}.crumb.sel{background:#eff6ff}',
    '.crumb code{font:12px ui-monospace,monospace;color:#52525b}',
    'select,button{font:inherit;border:1px solid #d4d4d8;border-radius:8px;padding:6px 10px;background:#fff;color:#18181b;cursor:pointer}',
    'button.primary{background:#18181b;color:#fff;border-color:#18181b}button.blue{background:#2563eb;color:#fff;border-color:#2563eb}',
    'button[disabled]{opacity:.45;cursor:not-allowed}.row{display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap}',
    '.err{margin-top:10px;padding:8px 10px;border-radius:8px;background:#fef2f2;color:#991b1b;white-space:pre-wrap;font-size:12px}',
    '.ok{margin-top:10px;padding:8px 10px;border-radius:8px;background:#ecfdf5;color:#065f46;font-size:12px}',
    '.bar{pointer-events:auto;position:fixed;left:50%;bottom:18px;transform:translateX(-50%);display:flex;align-items:center;gap:10px;padding:8px 10px 8px 14px;border-radius:14px;background:rgba(17,17,19,.94);color:#fff;box-shadow:0 12px 40px rgba(0,0,0,.35);max-width:min(920px,calc(100vw - 24px))}',
    '.bar button{background:rgba(255,255,255,.08);border-color:rgba(255,255,255,.14);color:#fff;padding:6px 10px}',
    '.bar button.keep{background:#16a34a;border-color:#16a34a}.bar .meta{display:flex;flex-direction:column;min-width:0}',
    '.bar .name{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bar .sub{font-size:11.5px;color:#a1a1aa;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
    '.fit{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;margin-left:6px}.fit.g{background:#14532d;color:#bbf7d0}.fit.y{background:#713f12;color:#fde68a}',
    '.count{font-variant-numeric:tabular-nums;color:#d4d4d8;min-width:44px;text-align:center}',
    '.spin{width:14px;height:14px;border:2px solid #d4d4d8;border-top-color:#2563eb;border-radius:50%;animation:s .8s linear infinite;display:inline-block;vertical-align:-2px;margin-right:6px}@keyframes s{to{transform:rotate(360deg)}}',
  ].join('') + '</style>';
  (document.body || document.documentElement).appendChild(host);
  var demoCss = document.createElement('style');
  demoCss.textContent = '[data-dh-demo]{text-decoration:underline dashed #f59e0b 1.5px;text-underline-offset:4px}';

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  var pill = el('div', 'pill');
  pill.appendChild(el('span', 'dot'));
  pill.appendChild(el('b', null, 'Try-on'));
  pill.title = 'Deckhand try-on: pick any section or component and try licensed alternatives in your own colours and words';
  root.appendChild(pill);

  var picking = false, outline = null, tag = null, panel = null, bar = null, session = null, idx = 1, state = null, busy = false;

  /* ------------------------------------------------------------ stamps + slots */
  function fiberOf(n) {
    for (var k in n) if (k.indexOf('__reactFiber$') === 0 || k.indexOf('__reactInternalInstance$') === 0) return n[k];
    return null;
  }
  function firstHost(f) {
    while (f && !(f.stateNode && f.stateNode.nodeType === 1)) f = f.child;
    return f ? f.stateNode : null;
  }
  function crumbsFor(node) {
    var out = [], seen = {};
    function add(stamp, dom, label) {
      if (!stamp || seen[stamp] || /(^|\/)(node_modules|dh-tryon)\//.test(stamp)) return;
      seen[stamp] = 1;
      out.push({ stamp: stamp, el: dom, label: label });
    }
    var f = fiberOf(node);
    if (f) {
      for (var i = 0; f && i < 200; i++, f = f.return) {
        var p = f.memoizedProps;
        if (p && typeof p === 'object' && p['data-dh']) {
          var name = typeof f.type === 'string' ? f.type : (f.type && (f.type.displayName || f.type.name)) || 'component';
          add(p['data-dh'], typeof f.type === 'string' ? f.stateNode : firstHost(f), name);
        }
      }
    }
    for (var n = node; n && n.nodeType === 1; n = n.parentElement) {
      if (n.hasAttribute && n.hasAttribute('data-dh')) add(n.getAttribute('data-dh'), n, n.tagName.toLowerCase());
    }
    out.sort(function (a, b) { return a.el && b.el && a.el !== b.el && a.el.contains(b.el) ? 1 : (a.el && b.el && b.el.contains(a.el) && a.el !== b.el ? -1 : 0); });
    return out.slice(0, 7);
  }

  var BLOCKS = ['navbar', 'hero', 'logo-cloud', 'features', 'content', 'stats', 'integrations', 'testimonials', 'pricing', 'comparison', 'team', 'faq', 'cta', 'contact', 'footer', 'login', 'signup'];
  function q(n, s) { try { return n.querySelectorAll(s).length; } catch (e) { return 0; } }
  function guessSlot(n) {
    if (!n || n.nodeType !== 1) return null;
    var t = n.tagName.toLowerCase(), cls = String(n.getAttribute('class') || '').toLowerCase();
    var txt = (n.innerText || '').slice(0, 3000);
    if (t === 'button' || n.getAttribute('role') === 'button' || (t === 'a' && /(btn|button|rounded|bg-|px-)/.test(cls) && q(n, '*') < 6)) return 'button';
    if (t === 'input') return 'input';
    if (t === 'textarea') return 'textarea';
    if (/badge|chip|pill/.test(cls) && txt.length < 40) return 'badge';
    if (t === 'nav' || (t === 'header' && q(n, 'a') >= 2)) return 'navbar';
    if (t === 'footer') return 'footer';
    if (q(n, 'input[type=password]')) return q(n, 'input') >= 3 ? 'signup' : 'login';
    if (q(n, 'form') && q(n, 'textarea')) return 'contact';
    var prices = (txt.match(/[$€£¥]\s?\d|\d[\d.,]*\s?[$€£¥]/g) || []).length;
    if (prices >= 2 && q(n, 'a,button') >= 2) return 'pricing';
    var qs = 0, heads = n.querySelectorAll('h2,h3,h4,dt,summary,button');
    for (var i = 0; i < heads.length; i++) if (/\?\s*$/.test(heads[i].textContent.trim())) qs++;
    if (qs >= 3) return 'faq';
    if (q(n, 'blockquote') >= 1 || /testimonial|review/.test(cls)) return 'testimonials';
    if (q(n, 'h1')) return 'hero';
    var kids = n.children, cards = 0;
    for (var j = 0; j < kids.length; j++) if (q(kids[j], 'h2,h3,h4') && (kids[j].innerText || '').length > 20) cards++;
    if (cards >= 3) return 'features';
    var imgs = q(n, 'img,svg');
    if (imgs >= 4 && txt.replace(/\s/g, '').length < 120) return 'logo-cloud';
    var nums = (txt.match(/\b\d[\d,.]*\s?(%|\+|k|m|x)\b/gi) || []).length;
    if (nums >= 3 && txt.length < 600) return 'stats';
    if (q(n, 'h2') >= 1 && q(n, 'a,button') >= 1 && txt.length < 500) return 'cta';
    if ((t === 'section' || t === 'article') && q(n, 'h2,h3')) return 'content';
    if (q(n, 'h3,h4') === 1 && txt.length < 500 && /(border|rounded|shadow|card)/.test(cls)) return 'card';
    return null;
  }
  function defaultCrumb(cr, clicked) {
    var ctl = clicked.closest && clicked.closest('button,a,input,textarea,[role=button]');
    if (ctl) for (var i = 0; i < cr.length; i++) if (cr[i].el === ctl || (cr[i].el && ctl.contains(cr[i].el)) || (cr[i].el && cr[i].el.contains(ctl) && guessSlot(cr[i].el) === 'button')) return i;
    for (var k = 0; k < cr.length; k++) if (BLOCKS.indexOf(guessSlot(cr[k].el)) >= 0) return k;
    return 0;
  }

  /* ------------------------------------------------------------ palette probe */
  function probe() {
    var cs = getComputedStyle(document.body), counts = {};
    var btns = document.querySelectorAll('button,a');
    for (var i = 0; i < btns.length && i < 200; i++) {
      var b = getComputedStyle(btns[i]).backgroundColor;
      var m = /rgba?\((\d+), (\d+), (\d+)(?:, ([\d.]+))?\)/.exec(b);
      if (!m || (m[4] !== undefined && Number(m[4]) < 0.5)) continue;
      var r = +m[1], g = +m[2], bl = +m[3], mx = Math.max(r, g, bl), mn = Math.min(r, g, bl);
      if (mx - mn < 24) continue;                         // neutral greys/white/black are not an accent
      counts[b] = (counts[b] || 0) + 1;
    }
    var best = null;
    for (var k in counts) if (!best || counts[k] > counts[best]) best = k;
    var bg = cs.backgroundColor;
    return { background: /rgba\(0, 0, 0, 0\)/.test(bg) ? null : bg, foreground: cs.color, primary: best, primaryForeground: best ? '#ffffff' : null };
  }

  /* ------------------------------------------------------------ picking */
  function place(box, r) { box.style.left = r.left + 'px'; box.style.top = r.top + 'px'; box.style.width = r.width + 'px'; box.style.height = r.height + 'px'; }
  function ours(e) { return e.composedPath && e.composedPath().indexOf(host) >= 0; }
  function stampOf(n) { for (; n && n.nodeType === 1; n = n.parentElement) if (n.hasAttribute('data-dh')) return n; return null; }
  function onMove(e) {
    if (!picking || ours(e)) return;
    var t = stampOf(e.target);
    if (!t) return;
    var cr = crumbsFor(e.target), d = cr[defaultCrumb(cr, e.target)] || { el: t, stamp: t.getAttribute('data-dh') };
    var target = d.el || t;
    if (!outline) { outline = el('div', 'outline'); tag = el('div', 'tag'); root.appendChild(outline); root.appendChild(tag); }
    var r = target.getBoundingClientRect();
    place(outline, r);
    tag.textContent = (guessSlot(target) || target.tagName.toLowerCase()) + ' · ' + String(d.stamp).replace(/:\d+$/, '');
    tag.style.left = Math.max(4, r.left) + 'px';
    tag.style.top = Math.max(4, r.top - 26) + 'px';
  }
  function onClick(e) {
    if (!picking || ours(e)) return;
    e.preventDefault(); e.stopPropagation();
    var cr = crumbsFor(e.target);
    if (!cr.length) return;
    stopPicking();
    openPanel(cr, defaultCrumb(cr, e.target));
  }
  function startPicking() { closePanel(); picking = true; pill.classList.add('on'); document.addEventListener('mousemove', onMove, true); document.addEventListener('click', onClick, true); }
  function stopPicking() {
    picking = false; pill.classList.remove('on');
    document.removeEventListener('mousemove', onMove, true); document.removeEventListener('click', onClick, true);
    if (outline) { outline.remove(); tag.remove(); outline = tag = null; }
  }
  pill.addEventListener('click', function () {
    if (session) return;
    picking ? stopPicking() : startPicking();
  });

  /* ------------------------------------------------------------ panel */
  function closePanel() { if (panel) { panel.remove(); panel = null; } }
  function openPanel(cr, sel) {
    closePanel();
    panel = el('div', 'panel');
    panel.appendChild(el('p', 'h', 'What do you want to swap?'));
    var list = el('div');
    var slotSel = el('select');
    var slots = (state && state.slots) || {};
    var names = Object.keys(slots).sort();
    function fillSlots(g) {
      slotSel.innerHTML = '';
      var ph = el('option', null, 'choose what this is…'); ph.value = ''; slotSel.appendChild(ph);
      names.forEach(function (s) { var o = el('option', null, s + ' (' + slots[s] + ')'); o.value = s; if (s === g) o.selected = true; slotSel.appendChild(o); });
      go.disabled = !slotSel.value;
    }
    var go = el('button', 'primary', 'Show variants');
    cr.forEach(function (c, i) {
      var row = el('div', 'crumb' + (i === sel ? ' sel' : ''));
      var g = guessSlot(c.el);
      row.appendChild(el('div', null, '●'));
      var t = el('div');
      t.appendChild(el('div', null, (g ? g : c.label) + (g ? ' — ' + c.label : '')));
      t.appendChild(el('code', null, String(c.stamp)));
      row.appendChild(t);
      row.addEventListener('click', function () {
        sel = i;
        [].forEach.call(list.children, function (x, k) { x.className = 'crumb' + (k === i ? ' sel' : ''); });
        fillSlots(guessSlot(c.el));
        flash(c.el);
      });
      list.appendChild(row);
    });
    panel.appendChild(list);
    var r1 = el('div', 'row');
    r1.appendChild(slotSel);
    var cnt = el('select');
    [3, 4, 6].forEach(function (n) { var o = el('option', null, n + ' variants'); o.value = n; if (n === 4) o.selected = true; cnt.appendChild(o); });
    r1.appendChild(cnt);
    panel.appendChild(r1);
    var r2 = el('div', 'row');
    var cancel = el('button', null, 'Cancel');
    r2.appendChild(go); r2.appendChild(cancel);
    panel.appendChild(r2);
    var msg = el('div', 'small muted');
    msg.style.marginTop = '10px';
    msg.textContent = 'Variants are real MIT-licensed components, shown in your colours with your text. Nothing ships until you keep one.';
    panel.appendChild(msg);
    root.appendChild(panel);
    fillSlots(guessSlot(cr[sel].el));
    slotSel.addEventListener('change', function () { go.disabled = !slotSel.value; });
    cancel.addEventListener('click', closePanel);
    go.addEventListener('click', function () {
      var m = /^(.*):(\d+):(\d+)$/.exec(cr[sel].stamp);
      if (!m || busy) return;
      busy = true; go.disabled = true;
      msg.className = 'small';
      msg.innerHTML = '<span class="spin"></span>Fetching, theming and filling variants with your content…';
      api('open', { file: m[1], line: +m[2], col: +m[3], slot: slotSel.value, count: +cnt.value, probe: probe() }).then(function (r) {
        busy = false;
        if (!r.ok) { go.disabled = false; msg.className = 'err'; msg.textContent = (r.code || 'ERROR') + ': ' + r.message + skippedText(r.skipped); return; }
        closePanel();
        startSession(r, 1);
      }).catch(function (e) { busy = false; go.disabled = false; msg.className = 'err'; msg.textContent = String(e); });
    });
  }
  function skippedText(sk) { return sk && sk.length ? '\n\nskipped: ' + sk.map(function (s) { return s.id + ' (' + s.why + ')'; }).join(', ') : ''; }
  function flash(n) { if (!n) return; var o = el('div', 'outline'); root.appendChild(o); place(o, n.getBoundingClientRect()); setTimeout(function () { o.remove(); }, 700); }

  /* ------------------------------------------------------------ session / variant bar */
  function wrappers() { return document.querySelectorAll('[data-dh-session="' + session.id + '"]'); }
  function apply(i) {
    idx = i;
    var ws = wrappers(), first = null;
    for (var w = 0; w < ws.length; w++) {
      var vs = ws[w].querySelectorAll(':scope > [data-dh-variant]');
      for (var k = 0; k < vs.length; k++) {
        var on = Number(vs[k].getAttribute('data-dh-variant')) === i;
        vs[k].style.display = on ? 'contents' : 'none';
        if (on && !first) first = vs[k];
      }
    }
    try { sessionStorage.setItem(SS, JSON.stringify({ id: session.id, idx: i })); } catch (e) { /* private mode */ }
    renderBar();
    if (first) {
      var t = first.firstElementChild;
      if (t) { var r = t.getBoundingClientRect(); if (r.top < 0 || r.top > innerHeight * 0.6) t.scrollIntoView({ block: 'start', behavior: 'smooth' }); }
    }
  }
  function startSession(s, i) {
    session = s; idx = i;
    document.head.appendChild(demoCss);
    renderBar('<span class="spin"></span>Waiting for your dev server to render the variants…');
    var t0 = Date.now();
    (function wait() {
      if (!session) return;
      if (wrappers().length) { apply(idx); return; }
      if (Date.now() - t0 > 45000) { renderBar('The variants were written, but the page did not update. Check the dev-server terminal for a compile error, or Discard.'); return; }
      setTimeout(wait, 250);
    })();
  }
  function renderBar(note) {
    if (!bar) { bar = el('div', 'bar'); root.appendChild(bar); }
    bar.innerHTML = '';
    var vs = session.variants, v = vs[idx] || vs[0];
    var prev = el('button', null, '◀'), next = el('button', null, '▶');
    var count = el('span', 'count', idx + ' / ' + (vs.length - 1));
    if (idx === 0) count.textContent = 'original';
    var meta = el('div', 'meta');
    var name = el('div', 'name', v.t);
    if (v.fit && v.fit.of) {
      var f = el('span', 'fit ' + (v.fit.carried >= v.fit.of ? 'g' : 'y'), 'your content ' + v.fit.carried + '/' + v.fit.of);
      name.appendChild(f);
    }
    meta.appendChild(name);
    var sub = note ? '' : (v.r === 'yours' ? 'your current version' : (v.r + ' · ' + (v.lic || 'MIT') + (v.fit && v.fit.demo && v.fit.demo.length ? ' · demo copy (dashed): ' + v.fit.demo.slice(0, 2).join(' · ') : '')));
    var subEl = el('div', 'sub'); if (note) subEl.innerHTML = note; else subEl.textContent = sub;
    meta.appendChild(subEl);
    var keep = el('button', 'keep', 'Keep'), orig = el('button', null, 'Original'), more = el('button', null, 'More'), disc = el('button', null, 'Discard');
    [prev, count, next, meta, orig, keep, more, disc].forEach(function (x) { bar.appendChild(x); });
    prev.onclick = function () { apply((idx - 1 + vs.length) % vs.length); };
    next.onclick = function () { apply((idx + 1) % vs.length); };
    orig.onclick = function () { apply(0); };
    keep.onclick = doKeep;
    disc.onclick = doDiscard;
    more.onclick = doMore;
    if (busy || note) [prev, next, orig, keep, more].forEach(function (b) { b.disabled = true; });
  }
  function endSession() {
    session = null;
    try { sessionStorage.removeItem(SS); } catch (e) { /* ignore */ }
    if (demoCss.parentNode) demoCss.remove();
    if (bar) { bar.remove(); bar = null; }
  }
  function doKeep() {
    if (busy) return;
    busy = true;
    var s = session, i = idx;
    renderBar('<span class="spin"></span>Keeping it — baking your text into the component…');
    api('keep', { id: s.id, idx: i }).then(function (r) {
      busy = false;
      if (!r.ok) { renderBar(r.code + ': ' + r.message); return; }
      endSession();
      toast('Kept “' + (r.kept || 'original') + '”' + (r.component ? ' → ' + r.component : ''), r.component ? s.id : null);
    });
  }
  function doDiscard() {
    if (busy) return;
    busy = true;
    api('discard', { id: session.id }).then(function (r) {
      busy = false;
      endSession();
      toast(r.ok ? 'Discarded — your file is restored (' + r.mode + ').' : r.code + ': ' + r.message);
    });
  }
  function doMore() {
    if (busy) return;
    busy = true;
    var sid = session.id;
    renderBar('<span class="spin"></span>Fetching more variants…');
    api('more', { id: sid, probe: probe() }).then(function (r) {
      busy = false;
      if (!r.ok) { renderBar(r.code + ': ' + r.message); return; }
      session = null;
      startSession(r, 1);
    });
  }
  function toast(text, keptId) {
    var t = el('div', 'panel');
    t.appendChild(el('div', 'ok', text));
    var row = el('div', 'row');
    if (keptId) {
      var save = el('button', 'blue', 'Save to my library');
      save.onclick = function () {
        save.disabled = true;
        api('save', { id: keptId }).then(function (r) { save.textContent = r.ok ? 'Saved — ranks first next time' : (r.code + ': ' + r.message); });
      };
      row.appendChild(save);
    }
    var done = el('button', null, 'Done');
    done.onclick = function () { t.remove(); };
    row.appendChild(done);
    t.appendChild(row);
    closePanel();
    root.appendChild(t);
    panel = t;
  }

  document.addEventListener('keydown', function (e) {
    if (!session || busy || /^(INPUT|TEXTAREA|SELECT)$/.test((e.target && e.target.tagName) || '')) return;
    var n = session.variants.length;
    if (e.key === 'ArrowRight') { apply((idx + 1) % n); e.preventDefault(); }
    else if (e.key === 'ArrowLeft') { apply((idx - 1 + n) % n); e.preventDefault(); }
    else if (e.key === 'Enter') { doKeep(); e.preventDefault(); }
    else if (e.key === 'Escape') { doDiscard(); e.preventDefault(); }
  });

  /* ------------------------------------------------------------ boot: resume an open session */
  api('state').then(function (r) {
    state = r;
    var saved = null;
    try { saved = JSON.parse(sessionStorage.getItem(SS) || 'null'); } catch (e) { /* ignore */ }
    var open = (r.open || [])[0];
    if (open) startSession(open, saved && saved.id === open.id ? saved.idx : open.shown || 1);
  });
  window.__dhTryon = { api: api, crumbsFor: crumbsFor, guessSlot: guessSlot, probe: probe };
})();
