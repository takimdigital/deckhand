// design-audit — copy this file to your repo ROOT as `playwright.config.ts`.
// Runner for the design-audit gate: one command runs visual baselines, the device matrix,
// a11y (axe), console/network checks, layout checks, screenshots and Lighthouse.
// The CLI gates (links / HTML / CSS / lint) are separate npm scripts — see design-audit/README.md.
//
// Env knobs: AUDIT_PORT (default 3000) · AUDIT_START_CMD (default 'pnpm build && pnpm start')
//            AUDIT_NO_SERVER=1 to use an already-running server and skip webServer.
//            AUDIT_BASE_URL — full base-URL override; e.g. http://host.docker.internal:3000 when
//            the gate runs in a container and the app runs on the host (pair with AUDIT_NO_SERVER=1).
// Pin overrides per invocation — a STALE ambient AUDIT_* value silently retargets the whole gate
// (live-hit); whenever an override is active this config prints the resolved values.

import { defineConfig, devices } from '@playwright/test';

const PORT = process.env.AUDIT_PORT ?? '3000';
const START_CMD = process.env.AUDIT_START_CMD ?? 'pnpm build && pnpm start';
const BASE_URL = process.env.AUDIT_BASE_URL ?? `http://127.0.0.1:${PORT}`;

if (process.env.AUDIT_PORT || process.env.AUDIT_START_CMD || process.env.AUDIT_BASE_URL) {
  console.error(`[design-audit] env override active — baseURL=${BASE_URL} start="${START_CMD}"`);
}

export default defineConfig({
  testDir: './design-audit/tests',
  outputDir: './design-audit/artifacts',
  timeout: 60_000,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  fullyParallel: false, // serial per file: keeps the audit cheap and snapshots stable
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'design-audit/report' }],
    ['playwright-ctrf-json-reporter', { outputFile: 'ctrf-report.json', outputDir: 'design-audit/ctrf' }],
  ],
  expect: {
    timeout: 10_000,
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01,
      animations: 'disabled',
      caret: 'hide',
      scale: 'css',
    },
  },
  snapshotPathTemplate: '{testDir}/__screenshots__/{platform}{/projectName}/{testFilePath}/{arg}{ext}',
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'desktop-chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
      grepInvert: /@lh/,
    },
    {
      name: 'desktop-dark',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 }, colorScheme: 'dark' },
      grepInvert: /@lh/,
    },
    { name: 'mobile-chromium', use: { ...devices['Pixel 5'] }, grepInvert: /@lh/ },
    { name: 'mobile-webkit', use: { ...devices['iPhone 14'] }, grepInvert: /@lh/ },
    { name: 'smoke-firefox', use: { ...devices['Desktop Firefox'] }, grep: /@smoke/ },
    {
      name: 'lh',
      use: { ...devices['Desktop Chrome'], launchOptions: { args: ['--remote-debugging-port=9222'] } },
      grep: /@lh/,
    },
  ],
  webServer:
    process.env.AUDIT_NO_SERVER === '1'
      ? undefined
      : {
          command: START_CMD,
          url: BASE_URL,
          reuseExistingServer: true,
          timeout: 240_000,
        },
});
