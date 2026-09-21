// design-audit — Lighthouse pass over the KEY routes (routes.json: "key": true).
// Runs ONLY in the `lh` project (grep /@lh/), whose chromium exposes CDP on :9222.
// Budget: AUDIT_PERF_BUDGET (default 0.9).
import { test, expect } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';
import lighthouse from 'lighthouse';

type Route = { name: string; path: string; key?: boolean };
const cfg: { routes: Route[] } = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', 'routes.json'), 'utf-8'),
);
const BASE = process.env.AUDIT_BASE_URL ?? `http://127.0.0.1:${process.env.AUDIT_PORT ?? '3000'}`;
if (!/^https?:\/\/(127\.0\.0\.1|localhost|\[::1\])(:|\/|$)/.test(BASE)) {
  // eslint-disable-next-line no-console
  console.warn(
    `[design-audit] lighthouse origin is not localhost (${BASE}) — is-on-https/uses-http2 fail for ` +
      `non-localhost HTTP origins by construction, so best-practices reads low (~0.78) on purpose. ` +
      `Run the lh project where the app is localhost or HTTPS.`,
  );
}

for (const route of cfg.routes.filter((r) => r.key)) {
  test(`lighthouse @lh: ${route.name}`, async ({ page }, testInfo) => {
    await page.goto(route.path); // warm the server so Lighthouse isn't measuring a cold start
    const result = await lighthouse(new URL(route.path, BASE).toString(), {
      port: 9222,
      output: 'json',
      logLevel: 'error',
      onlyCategories: ['performance', 'seo', 'best-practices'],
    });
    if (!result) throw new Error('lighthouse returned no result');
    const lhr = result.lhr;
    const p = testInfo.outputPath(`lighthouse-${route.name}.json`);
    fs.writeFileSync(p, JSON.stringify(lhr));
    await testInfo.attach(`lighthouse-${route.name}.json`, { path: p, contentType: 'application/json' });

    const min = Number(process.env.AUDIT_PERF_BUDGET ?? '0.9');
    const perf = lhr.categories.performance?.score ?? null;
    expect.soft(perf, `performance budget (>= ${min})`).not.toBeNull();
    if (perf !== null) expect.soft(perf).toBeGreaterThanOrEqual(min);
    for (const cat of ['seo', 'best-practices'] as const) {
      const score = lhr.categories[cat]?.score ?? null;
      if (score !== null) expect.soft(score, `${cat} budget (>= ${min})`).toBeGreaterThanOrEqual(min);
    }
  });
}
