// lib/email/send.ts — the ONLY send path in the app (auth + product mail).
// Multi-provider failover across free tiers. HTTP APIs only — no vendor SDKs.
// Postgres is the quota authority. Chain order + caps come from env (vps-ops ref 70).
// Template: copy to lib/email/send.ts · run schema.sql · fill .env.example rows.
import { sql } from "./db"; // your Postgres client, tagged-template SQL

type Mail = { to: string; subject: string; html: string; text: string; from?: string };
type Adapter = { id: string; cap: number; from: string; send(m: Mail, key: string): Promise<void> };

const APP_ORIGIN = new URL(process.env.APP_URL!).origin;
const OWNER = process.env.OWNER_ALERT_EMAIL!;
const TIMEOUT_MS = Number(process.env.EMAIL_TIMEOUT_MS ?? 8000);

// ---------- adapters (~12 lines each; a 4th provider = one adapter + one env row) ----------
const parseFrom = (s: string) => { const m = s.match(/^(.*)<(.+)>$/); return m ? { name: m[1].trim(), email: m[2].trim() } : { name: "", email: s.trim() }; };
async function postJson(url: string, headers: Record<string, string>, body: unknown, key: string) {
  const res = await fetch(url, { method: "POST", headers: { "content-type": "application/json", "Idempotency-Key": key, ...headers },
    body: JSON.stringify(body), signal: AbortSignal.timeout(TIMEOUT_MS) });
  if (!res.ok) throw Object.assign(new Error(`http ${res.status}`), { status: res.status, body: await res.text() });
}
const ADAPTERS: Record<string, Adapter["send"]> = {
  resend: (m, key) => postJson("https://api.resend.com/emails", { authorization: `Bearer ${process.env.RESEND_API_KEY}` },
    { from: m.from, to: [m.to], subject: m.subject, html: m.html, text: m.text }, key),
  mailgun: async (m, key) => {
    const form = new URLSearchParams({ from: m.from!, to: m.to, subject: m.subject, text: m.text, html: m.html, "o:tracking": "no" });
    const res = await fetch(`https://api.mailgun.net/v3/${process.env.MAILGUN_DOMAIN}/messages`, { method: "POST",
      headers: { authorization: "Basic " + Buffer.from(`api:${process.env.MAILGUN_API_KEY}`).toString("base64"), "Idempotency-Key": key },
      body: form, signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (!res.ok) throw Object.assign(new Error(`http ${res.status}`), { status: res.status, body: await res.text() });
  },
  brevo: (m, key) => { const f = parseFrom(m.from!); return postJson("https://api.brevo.com/v3/smtp/email", { "api-key": process.env.BREVO_API_KEY! },
    { sender: f.name ? f : { email: f.email }, to: [{ email: m.to }], subject: m.subject, htmlContent: m.html, textContent: m.text }, key); },
};

const CHAIN: Adapter[] = (process.env.EMAIL_CHAIN ?? "resend,mailgun,brevo").split(",").map((id) => ({
  id, cap: Number(process.env[`${id.toUpperCase()}_DAILY_CAP`]!), from: process.env[`${id.toUpperCase()}_FROM`]!, send: ADAPTERS[id] }));

const log = (k: string, p: string, o: string, e: string) =>
  sql`INSERT INTO email_attempt (message_key, provider, outcome, error) VALUES (${k}, ${p}, ${o}, ${e.slice(0, 500)})`;

// Link integrity: every URL in the body must be ours — providers must never rewrite auth links.
function assertLinks(m: Mail) {
  const urls = [...`${m.html} ${m.text}`.matchAll(/https?:\/\/[^\s"'<>)\]]+/g)].map((x) => x[0]);
  if (!urls.length) throw new Error("email: body has no link");
  for (const u of urls) if (new URL(u).origin !== APP_ORIGIN) throw new Error(`email: foreign link ${u}`);
}

// Atomic per-provider / per-UTC-day quota claim; no row back ⇒ provider exhausted today → next in chain.
const claim = async (p: Adapter) => (await sql`INSERT INTO email_quota (provider, utc_day, sent)
  VALUES (${p.id}, ${new Date().toISOString().slice(0, 10)}, 1)
  ON CONFLICT (provider, utc_day) DO UPDATE SET sent = email_quota.sent + 1
  WHERE email_quota.sent < ${p.cap} RETURNING sent`).length === 1;

// Throttle/quota (failover + alert) vs message-level (terminal — never burn provider B's quota).
const degraded = (s: number, b: string) => s === 429 || s === 402 || (s === 403 && /quota|limit|credit/i.test(b)) ||
  /daily_quota_exceeded|monthly_quota_exceeded|not_enough_credits|limit exceeded|throttl/i.test(b);
const permanent = (s: number, b: string) => s === 400 || s === 422 || /invalid[_ ](to|recipient|email)|no such user|suppress/i.test(b);

export async function sendEmail(mail: Mail, ctx: { key: string }) {
  assertLinks(mail);
  let lastErr: unknown;
  for (const p of CHAIN) {
    if (!(await claim(p))) { void alert(p, "local daily cap reached"); continue; }
    try {
      await p.send({ ...mail, from: p.from }, ctx.key); // adapters forward Idempotency-Key: ctx.key
      await log(ctx.key, p.id, "sent", "");
      return { provider: p.id };
    } catch (e: any) {
      lastErr = e;
      const s = e.status ?? 0, body = String(e.body ?? e.message);
      await log(ctx.key, p.id, permanent(s, body) ? "permanent" : "fail", body);
      if (permanent(s, body)) throw e; // bad recipient: terminal, never retry on the next provider
      void alert(p, degraded(s, body) ? "throttled/quota" : `transport ${s || "timeout"}`);
    }
  }
  throw lastErr ?? new Error("email: chain exhausted"); // caller falls back to its normal retry UX
}

// Edge-triggered: one alert per (provider, reason) per 6 h; owner mail goes via the NEXT healthy provider.
async function alert(p: Adapter, reason: string) {
  try {
    const first = (await sql`INSERT INTO email_alert_state (provider, reason, at) VALUES (${p.id}, ${reason}, now())
      ON CONFLICT (provider, reason) DO UPDATE SET at = now()
      WHERE email_alert_state.at < now() - interval '6 hours' RETURNING at`).length > 0;
    console.warn(`EMAIL_ALERT provider=${p.id} reason=${reason}`); // greppable line, always
    if (process.env.ALERT_WEBHOOK_URL) void fetch(process.env.ALERT_WEBHOOK_URL, { method: "POST", body: JSON.stringify({ provider: p.id, reason }) }).catch(() => {});
    if (!first) return; // inside cooldown
    for (const q of CHAIN.slice(CHAIN.indexOf(p) + 1)) { // never through the failed provider
      try { await q.send({ to: OWNER, subject: `[email] ${p.id}: ${reason}`, text: `Provider ${p.id}: ${reason}\n${new Date().toISOString()}` }, `alert/${p.id}/${Date.now()}`); return; } catch {}
    }
    console.error("EMAIL_ALERT no healthy provider left"); // last resort: log + /api/health
  } catch { /* alerts must never break sends */ }
}
