// Portfolio screenshot capture script (Step 10).
// Launches the app in a real browser and navigates via in-app links (not page.goto)
// so client-side/reactive state behaves as it would for a real user, then saves PNGs
// to ./portfolio-screenshots/. Extend this script in place in later sessions rather
// than writing a new one — see .claude/skills/README.md.
//
// Requires: frontend dev server running at BASE_URL, backend running with realistic
// seed data (see .claude/seed-data.md). Uses playwright-core against whatever
// Chromium revision is already installed locally (see .claude/portfolio-reference.md's
// Step 8/9 notes on Playwright availability in this environment).
//
// Usage (must run with cwd = frontend/, so playwright-core resolves from its node_modules):
//   cd frontend && node ../.claude/skills/capture-screenshots.mjs

import { mkdirSync } from 'node:fs'
import { createRequire } from 'node:module'
import path from 'node:path'

const require = createRequire(path.join(process.cwd(), 'noop.cjs'))
const { chromium } = require('playwright-core')

const BASE_URL = process.env.CAPTURE_BASE_URL ?? 'http://localhost:5173'
// project root = parent of frontend/, which is this script's required cwd (see Usage above)
const OUT_DIR = path.resolve(process.cwd(), '..', 'portfolio-screenshots')
const DESKTOP = { width: 1920, height: 1080 }
const MOBILE = { width: 390, height: 844 }

mkdirSync(OUT_DIR, { recursive: true })

function nav(page) {
  return page.getByRole('navigation')
}

// IMPORTANT: page.waitForLoadState('networkidle') is not sufficient on its own after a
// client-side (React Router) navigation click — there can be a brief gap between the click
// resolving and the destination page's own useEffect firing its data fetch, during which no
// network request is in flight yet. networkidle can resolve in that gap, before the fetch
// even starts, causing a screenshot of the *previous* page's stale content even though the
// URL has already changed. Always wait for the destination page's own <h1> text (a real
// content signal) before treating a navigation as complete.
// Some pages (e.g. Lead List) fire a second, independent effect for summary stat
// cards alongside the main table fetch - networkidle can resolve in the gap between
// the two, before the second effect's own request has even started. A short settle
// delay after networkidle is cheaper and more robust than tracking every page's own
// number of concurrent effects here.
async function waitForPage(page, headingText) {
  await page.locator('main').getByRole('heading', { level: 1 }).filter({ hasText: headingText }).waitFor({ timeout: 10000 })
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(400)
}

async function shot(page, name) {
  const file = path.join(OUT_DIR, `${name}.png`)
  await page.screenshot({ path: file, fullPage: true })
  console.log(`captured ${name}.png`)
}

async function run() {
  const browser = await chromium.launch()

  // --- Desktop pass: full page-by-page tour via in-app navigation ---
  const desktopCtx = await browser.newContext({ viewport: DESKTOP })
  const page = await desktopCtx.newPage()

  await page.goto(BASE_URL)
  await waitForPage(page, 'Automated classification, routing, and review')
  await shot(page, '01-home')

  await nav(page).getByRole('link', { name: 'Observability', exact: true }).click()
  await waitForPage(page, 'Leads')
  await shot(page, '02-lead-list')

  await page.locator('main table tbody tr:first-child a').click()
  await waitForPage(page, /^Lead [0-9a-f]+/)
  await shot(page, '03-lead-detail')

  await page.locator('main').getByRole('link', { name: /View Full History/i }).click()
  await waitForPage(page, /^Full history/)
  await shot(page, '04-lead-history')

  await nav(page).getByRole('link', { name: 'Review Queue', exact: true }).click()
  await waitForPage(page, 'Review Queue')
  await shot(page, '05-review-queue')

  await page.locator('main table tbody tr:first-child a').click()
  await waitForPage(page, /^Review lead/)
  await shot(page, '06-review-detail')

  await nav(page).getByRole('link', { name: 'Benchmark', exact: true }).click()
  await waitForPage(page, 'Classification Accuracy Benchmark')
  // Trend chart's line-draw animation (see index.css's .chart-line, 900ms) runs on mount;
  // wait for it to finish so the screenshot doesn't capture a partially-drawn line.
  await page.waitForTimeout(1000)
  await shot(page, '07-benchmark')

  await desktopCtx.close()

  // --- Mobile pass: a couple of representative pages showing the responsive layout ---
  const mobileCtx = await browser.newContext({ viewport: MOBILE })
  const mobilePage = await mobileCtx.newPage()

  await mobilePage.goto(BASE_URL)
  await waitForPage(mobilePage, 'Automated classification, routing, and review')
  await shot(mobilePage, '08-mobile-home')

  await nav(mobilePage).getByRole('link', { name: 'Observability', exact: true }).click()
  await waitForPage(mobilePage, 'Leads')
  await shot(mobilePage, '09-mobile-lead-list')

  await mobileCtx.close()
  await browser.close()
}

run().catch((err) => {
  console.error(err)
  process.exit(1)
})
