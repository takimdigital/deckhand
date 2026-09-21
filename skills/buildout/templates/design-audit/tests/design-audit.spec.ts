// design-audit — the unified per-route check. ONE page load per route per project:
// console/network listeners → axe (WCAG) → layout (overflow / touch targets / dir) →
// meta+OG → screenshot baseline → HTML dump for the html-validate CLI gate.
// Everything is a SOFT assertion: one page still reports every problem it found.
import { test, expect, type Page, type TestInfo } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import * as fs from 'node:fs';
import * as path from 'node:path';

type Route = { name: string; path: string; key?: boolean; smoke?: boolean; visual?: boolean };
type Allow = { console?: string[]; network?: string[] };
const cfg: { allow?: Allow; routes: Route[] } = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', 'routes.json'), 'utf-8'),
);
const ALLOW_CONSOLE = cfg.allow?.console ?? [];
const ALLOW_NETWORK = cfg.allow?.network ?? [];
const HTML_DIR = path.resolve(__dirname, '..', 'artifacts', 'html');

const allowed = (list: string[], text: string) => list.some((s) => text.includes(s));

async function attachJson(testInfo: TestInfo, name: string, data: unknown) {
  const p = testInfo.outputPath(name);
  fs.writeFileSync(p, JSON.stringify(data, null, 2));
  await testInfo.attach(name, { path: p, contentType: 'application/json' });
}

async function layout(page: Page) {
  return page.evaluate(() => {
    const de = document.documentElement;
    const smallTargets = Array.from(
      document.querySelectorAll('a,button,input,select,textarea,summary,[role="button"]'),
    )
      .filter((el) => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && (r.width < 24 || r.height < 24);
      })
      .slice(0, 20)
      .map((el) => ({
        tag: el.tagName.toLowerCase(),
        text: (el.textContent ?? '').trim().slice(0, 40),
      }));
    return {
      url: location.href,
      viewport: { w: window.innerWidth, h: window.innerHeight },
      scrollWidth: de.scrollWidth,
      clientWidth: de.clientWidth,
      overflowX: de.scrollWidth > de.clientWidth + 1,
      dir: de.getAttribute('dir') ?? document.body?.getAttribute('dir') ?? 'ltr',
      smallTargets,
    };
  });
}

async function seo(page: Page) {
  return page.evaluate(() => {
    const get = (sel: string) => document.querySelector(sel)?.getAttribute('content') ?? null;
    return {
      title: document.title,
      description: get('meta[name="description"]'),
      ogTitle: get('meta[property="og:title"]'),
      ogImage: get('meta[property="og:image"]'),
      lang: document.documentElement.getAttribute('lang'),
    };
  });
}

for (const route of cfg.routes) {
  const title = `design: ${route.name}${route.smoke ? ' @smoke' : ''}`;
  test(title, async ({ page }, testInfo) => {
    const events = {
      console: [] as string[],
      pageError: [] as string[],
      requestFailed: [] as { url: string; error: string }[],
      badResponses: [] as { url: string; status: number }[],
    };
    page.on('console', (m) => {
      if (m.type() === 'error') events.console.push(m.text().slice(0, 300));
    });
    page.on('pageerror', (e) => events.pageError.push(String(e.message).slice(0, 300)));
    page.on('requestfailed', (r) => {
      const error = r.failure()?.errorText ?? '';
      if (!error.includes('ERR_ABORTED')) events.requestFailed.push({ url: r.url(), error });
    });
    page.on('response', (r) => {
      if (r.status() >= 400) events.badResponses.push({ url: r.url(), status: r.status() });
    });

    await page.goto(route.path, { waitUntil: 'load' });
    await page.waitForLoadState('networkidle', { timeout: 5_000 }).catch(() => {});

    // 1) accessibility — WCAG 2.2 A/AA
    const axe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze();

    // 2) layout at the project viewport
    const layoutReport = await layout(page);

    // 2b) narrow-width reflow probe (desktop project only — WCAG 1.4.10)
    let narrow320: { width: number; overflowX: boolean } | null = null;
    if (testInfo.project.name === 'desktop-chromium') {
      const restore = page.viewportSize();
      await page.setViewportSize({ width: 320, height: 900 });
      narrow320 = { width: 320, overflowX: (await layout(page)).overflowX };
      if (restore) await page.setViewportSize(restore);
    }

    // 3) meta/OG + collect the full audit payload (ONE attachment per route)
    const seoReport = await seo(page);
    await attachJson(testInfo, `audit-${route.name}.json`, {
      route: route.path,
      project: testInfo.project.name,
      axeViolations: axe.violations,
      layout: layoutReport,
      narrow320,
      seo: seoReport,
      console: events.console,
      pageErrors: events.pageError,
      requestFailed: events.requestFailed,
      badResponses: events.badResponses,
    });

    // 4) visual baseline
    if (route.visual !== false) {
      await expect(page).toHaveScreenshot(`${route.name}.png`, { fullPage: true });
    }

    // 5) HTML dump for the html-validate CLI gate
    fs.mkdirSync(HTML_DIR, { recursive: true });
    fs.writeFileSync(
      path.join(HTML_DIR, `${testInfo.project.name}-${route.name}.html`),
      await page.content(),
    );

    // soft asserts — the test fails if anything is wrong, but reports ALL findings
    const consoleNoise = events.console.filter((t) => !allowed(ALLOW_CONSOLE, t));
    const failedReqs = events.requestFailed.filter((r) => !allowed(ALLOW_NETWORK, r.url));
    const badResps = events.badResponses.filter((r) => !allowed(ALLOW_NETWORK, r.url));
    expect.soft(axe.violations, `axe violations on ${route.path}`).toEqual([]);
    expect.soft(consoleNoise, `console errors on ${route.path}`).toEqual([]);
    expect.soft(events.pageError, `page errors on ${route.path}`).toEqual([]);
    expect.soft(failedReqs, `failed requests on ${route.path}`).toEqual([]);
    expect.soft(badResps, `4xx/5xx responses on ${route.path}`).toEqual([]);
    expect.soft(layoutReport.overflowX, `horizontal overflow at ${layoutReport.viewport.w}px`).toBe(false);
    if (narrow320) expect.soft(narrow320.overflowX, 'horizontal overflow at 320px').toBe(false);
    if (route.key) {
      expect.soft(seoReport.title, 'missing <title>').toBeTruthy();
      expect.soft(seoReport.description, 'missing meta description').toBeTruthy();
      expect.soft(seoReport.ogTitle, 'missing og:title').toBeTruthy();
      expect.soft(seoReport.ogImage, 'missing og:image').toBeTruthy();
    }
  });
}
