// qa/cdp.mjs — dependency-free CDP driver (node 22+: built-in fetch + WebSocket).
//
// Why this beats `chrome --screenshot` and iframe harnesses:
//   * Emulation.setDeviceMetricsOverride gives a TRUE layout width (Chrome clamps
//     --window-size to a 500px minimum on Windows).
//   * The script runs in the PAGE's own context: no same-origin iframe needed, no
//     rebuild to publish a harness into public/, and the page's React state is real.
//   * Page.captureScreenshot returns true-width PNGs.
//
// usage: chrome --headless=new --disable-gpu --remote-debugging-port=9222 --user-data-dir=<tmp> about:blank &
//        node qa/cdp.mjs <url> <width> <height> <scriptFile.js> [out.png]
//
import { readFileSync, writeFileSync } from 'node:fs';

const [url, wStr, hStr, scriptFile, shotPath] = process.argv.slice(2);
const W = +wStr, H = +hStr, PORT = 9222;

const created = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(created.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
await new Promise(res => ws.addEventListener('open', res, { once: true }));

await send('Page.enable');
await send('Runtime.enable');
await send('Network.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: W < 700 });
const net = [];
ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.method === 'Network.responseReceived') net.push({ url: m.params.response.url, status: m.params.response.status }); });
await send('Page.navigate', { url });
await new Promise(r => setTimeout(r, 2500));

const qaInjected = await send('Runtime.evaluate', {
  expression: `globalThis.__QA = ${JSON.stringify({
    formSel: process.env.QA_FORM_SEL || null,
    receiptRe: process.env.QA_RECEIPT_RE || null,
    submitRe: process.env.QA_SUBMIT_RE || null,
  })};`,
  returnByValue: true,
});
const r = await send('Runtime.evaluate', { expression: readFileSync(scriptFile, 'utf8'), awaitPromise: true, returnByValue: true, userGesture: true });
console.log('RESULT ' + JSON.stringify({
  viewport: `${W}x${H}`,
  apiCalls: net.filter(n => n.url.includes('/api/')).map(n => n.status),
  result: r?.result?.result?.value ?? r?.result?.exceptionDetails ?? r?.result,
}));
if (shotPath) {
  const s = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  writeFileSync(shotPath, Buffer.from(s.result.data, 'base64'));
  console.log('SHOT ' + shotPath);
}
ws.close();
process.exit(0);
