// qa/form-drive.js — fill and submit a real form, then measure what a person would see.
// Run through templates/qa/cdp.mjs (page context, exact viewport). Edit FORM_SEL if needed.
//
// Reports: per-field read-back (catches silent fill failures), the API status the submit
// produced, the receipt text + its rect against the viewport AT THE MOMENT IT APPEARS,
// validation errors, occlusion hit-tests for on-screen controls (at max scroll and at
// focus), the text floor and horizontal overflow.
(async () => {
  const FORM_SEL = '#soumission form';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const txt = el => (el.textContent || '').replace(/\s+/g, ' ').trim();
  const norm = s => (s || '').toLowerCase();
  const labelOf = el => (el.getAttribute('aria-label') || (el.labels && el.labels[0] && el.labels[0].textContent) || (el.closest('label,div,li,fieldset') || {}).textContent || '');
  const key = el => norm(el.name || el.id || labelOf(el)).replace(/\s+/g, '-').slice(0, 22);
  const out = { url: location.href, viewport: innerWidth + 'x' + innerHeight };

  const form = document.querySelector(FORM_SEL) || [...document.querySelectorAll('form')].find(f => /soumission|demande|contact/i.test(f.id + f.className + txt(f).slice(0, 120))) || document.querySelector('form');
  if (!form) return { ...out, error: 'no form' };
  const sec = form.closest('section') || form.parentElement;
  const controls = [...form.querySelectorAll('input:not([type=hidden]),select,textarea')];
  out.controls = controls.length;
  out.labels = controls.map(el => key(el));
  out.attrs = controls.map(el => ({ k: key(el), required: !!(el.required || el.getAttribute('aria-required')), has_label: !!(el.labels && el.labels[0]), placeholder: el.getAttribute('placeholder'), h: Math.round(el.getBoundingClientRect().height) }));

  const setV = (el, v) => {
    el.focus();
    const d = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value');
    if (d && d.set) d.set.call(el, v); else el.value = v;
    for (const t of ['input', 'change', 'blur']) el.dispatchEvent(new Event(t, { bubbles: true }));
  };
  const snapBefore = new Set([...sec.querySelectorAll('*')].map(txt).filter(Boolean));
  const docHBefore = document.documentElement.scrollHeight;

  for (const el of controls) {
    const t = (el.type || el.tagName).toLowerCase(), k = key(el);
    if (t === 'checkbox' || t === 'radio') { if (!el.checked) el.click(); continue; }
    let v = 'QA probe';
    if (t === 'email' || /courriel|email/.test(k)) v = 'qa-probe@exemple.test';
    else if (t === 'tel' || /tel|phone/.test(k)) v = '555-000-0000';
    else if (/nom|name/.test(k)) v = 'QA probe';
    else if (/ville|quartier|adresse/.test(k)) v = 'Ville, quartier';
    else if (/type|travaux|service|sujet/.test(k)) v = el.tagName === 'SELECT' && el.options[1] ? el.options[1].value : 'Travaux';
    else if (el.tagName === 'TEXTAREA') v = 'Test de vérification : décrire le problème en une phrase claire, avec ce qui a été fait en attendant.';
    else if (el.tagName === 'SELECT') v = el.options[1] ? el.options[1].value : el.value;
    setV(el, v);
  }
  out.readback = controls.map(el => ({ k: key(el), v: (el.type === 'checkbox' || el.type === 'radio') ? String(el.checked) : String(el.value).slice(0, 22) }));
  out.unfilled = out.readback.filter(x => x.v === '' || x.v === 'false').map(x => x.k);

  const submit = [...form.querySelectorAll('button,input[type=submit]')].find(b => /envoyer|soumettre|recevoir|demande|submit/i.test(txt(b) || b.value || '')) || form.querySelector('button');
  out.submitLabel = submit ? (txt(submit) || submit.value) : null;
  submit.click();

  const newTexts = [];
  let receipt = null;
  for (let i = 0; i < 40 && !receipt; i++) {
    await sleep(250);
    const fresh = [...sec.querySelectorAll('[role=status],[aria-live],[role=alert],h2,h3,p,div,li')].filter(e => { const t = txt(e); return t && t.length < 420 && !snapBefore.has(t); });
    for (const f of fresh) { const t = txt(f); if (!newTexts.includes(t)) newTexts.push(t); }
    receipt = fresh.find(e => /re[çc]u|merci|demande (est|a été)|enregistr|dans les|prochaine/i.test(txt(e)) && txt(e).length > 40) || null;
  }
  out.new_texts = newTexts.slice(0, 6);
  out.errors = [...sec.querySelectorAll('[role=alert],[aria-invalid=true],[class*=erreur],[class*=error]')].map(txt).filter(Boolean).slice(0, 8);
  out.api = performance.getEntriesByType('resource').filter(r => r.name.includes('/api/')).map(r => r.name.split('/api/')[1]);
  if (receipt) {
    const r = receipt.getBoundingClientRect();
    out.receipt = { text: txt(receipt).slice(0, 300), top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height), inside_viewport_at_appearance: r.top >= 0 && r.bottom <= innerHeight };
    receipt.scrollIntoView({ block: 'center' });
    const r2 = receipt.getBoundingClientRect();
    out.receipt_after_scroll = { top: Math.round(r2.top), bottom: Math.round(r2.bottom) };
  } else out.receipt = { found: false };

  const test = els => {
    const res = { visible: 0, offscreen: 0, occluded: [] };
    for (const el of els) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0 || r.top < 0 || r.bottom > innerHeight) { res.offscreen++; continue; }
      res.visible++;
      const hit = document.elementFromPoint(Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2));
      if (!(hit && (hit === el || el.contains(hit) || hit.contains(el)))) res.occluded.push({ k: key(el), hit: hit ? hit.tagName + '.' + String(hit.className).split(' ')[0] : null });
    }
    return res;
  };
  scrollTo(0, document.documentElement.scrollHeight);
  await sleep(400);
  out.occlusion_at_max_scroll = test([...form.querySelectorAll('input:not([type=hidden]),select,textarea,button')]);
  scrollTo(0, 0);
  await sleep(300);
  const foc = [];
  for (const el of controls) {
    el.focus();
    await sleep(120);
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0 || r.top < 0 || r.bottom > innerHeight) { foc.push({ k: key(el), offscreen: true }); continue; }
    const hit = document.elementFromPoint(Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2));
    if (!(hit && (hit === el || el.contains(hit) || hit.contains(el)))) foc.push({ k: key(el), hit: hit ? hit.tagName + '.' + String(hit.className).split(' ')[0] : null });
  }
  out.occluded_at_focus = foc;
  const texts = [...document.querySelectorAll('body *')].filter(e => e.children.length === 0 && txt(e).length > 1 && e.getBoundingClientRect().height > 0);
  const sizes = texts.map(e => ({ t: txt(e).slice(0, 28), fs: parseFloat(getComputedStyle(e).fontSize) })).sort((a, b) => a.fs - b.fs);
  out.text_floor = sizes.slice(0, 3);
  out.under_16 = sizes.filter(s => s.fs < 16).length;
  out.overflow_px = document.documentElement.scrollWidth - innerWidth;
  out.doc_height = document.documentElement.scrollHeight;
  out.doc_height_before = docHBefore;
  return out;
})()
