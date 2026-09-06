// No-scroll invariant checker (Step 9 responsive validation / Step 11-12 re-verification).
// Measures `main`'s scrollWidth/scrollHeight against its clientWidth/clientHeight at each of
// the four target viewports (1920x1080, 1440x900, 1366x768, mobile 390x844) across every
// primary route, flagging any page/viewport combination with overflow beyond a small
// tolerance. Same method this project's prior Step 8/9/12 rounds used ad hoc (per
// .claude/portfolio-reference.md's Key Decisions) - written here as a reusable script for the
// first time.
//
// Usage (must run with cwd = frontend/, so playwright-core resolves from its node_modules):
//   cd frontend && node ../.claude/skills/check-no-scroll.mjs

import { createRequire } from 'node:module'
import path from 'node:path'

const require = createRequire(path.join(process.cwd(), 'noop.cjs'))
const { chromium } = require('playwright-core')

const BASE_URL = process.env.CAPTURE_BASE_URL ?? 'http://localhost:5173'
const API_URL = process.env.API_BASE_URL ?? 'http://localhost:8000'

const VIEWPORTS = [
  { name: '1920x1080', width: 1920, height: 1080 },
  { name: '1440x900', width: 1440, height: 900 },
  { name: '1366x768', width: 1366, height: 768 },
  { name: '390x844 (mobile)', width: 390, height: 844 },
]

async function fetchJson(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} -> ${res.status}`)
  return res.json()
}

async function measure(page) {
  return page.evaluate(() => {
    const main = document.querySelector('main')
    if (!main) return null
    return {
      scrollWidth: main.scrollWidth,
      clientWidth: main.clientWidth,
      scrollHeight: main.scrollHeight,
      clientHeight: main.clientHeight,
    }
  })
}

async function run() {
  // Discover real ids for the dynamic routes so this check exercises real content, not an
  // empty/404 state.
  const leadsPage = await fetchJson(`${API_URL}/leads?page=1&page_size=1`)
  const leadId = leadsPage.items[0]?.lead_id
  const reviews = await fetchJson(`${API_URL}/reviews`)
  const runId = reviews[0]?.run_id

  const routes = [
    { path: '/', label: 'Home' },
    { path: '/leads', label: 'Lead List' },
    ...(leadId ? [{ path: `/leads/${leadId}`, label: 'Lead Detail' }] : []),
    ...(leadId ? [{ path: `/leads/${leadId}/history`, label: 'Lead History' }] : []),
    { path: '/reviews', label: 'Review Queue' },
    ...(runId ? [{ path: `/reviews/${runId}`, label: 'Review Detail' }] : []),
    { path: '/benchmark', label: 'Benchmark' },
    { path: '/benchmark', label: 'Benchmark (Threshold Simulator expanded)', expandThreshold: true },
    { path: '/analytics', label: 'Analytics' },
  ]

  const browser = await chromium.launch()
  const results = []
  const TOLERANCE = 2 // px, rounding slack

  for (const viewport of VIEWPORTS) {
    const ctx = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } })
    const page = await ctx.newPage()
    for (const route of routes) {
      await page.goto(`${BASE_URL}${route.path}`)
      // Wait for real content rather than a fixed sleep - any h1 heading signals the page settled.
      await page.locator('main').getByRole('heading', { level: 1 }).first().waitFor({ timeout: 10000 }).catch(() => {})
      await page.waitForLoadState('networkidle').catch(() => {})
      await page.waitForTimeout(400)
      if (route.expandThreshold) {
        const summary = page.locator('main details summary', { hasText: 'Threshold Simulator' })
        if (await summary.count()) {
          await summary.click()
          await page.waitForTimeout(300)
        }
      }
      const m = await measure(page)
      if (!m) {
        results.push({ viewport: viewport.name, route: route.label, error: 'no <main> found' })
        continue
      }
      const hOverflow = m.scrollHeight - m.clientHeight
      const wOverflow = m.scrollWidth - m.clientWidth
      results.push({
        viewport: viewport.name,
        route: route.label,
        hOverflow,
        wOverflow,
        flagged: hOverflow > TOLERANCE || wOverflow > TOLERANCE,
      })
    }
    await ctx.close()
  }
  await browser.close()

  console.log('\nNO-SCROLL CHECK RESULTS')
  console.log('========================')
  for (const r of results) {
    if (r.error) {
      console.log(`[ERROR] ${r.viewport} / ${r.route}: ${r.error}`)
      continue
    }
    const flag = r.flagged ? '  <-- OVERFLOW' : ''
    console.log(
      `${r.viewport.padEnd(20)} ${r.route.padEnd(38)} vOverflow=${String(r.hOverflow).padStart(4)}px hOverflow=${String(r.wOverflow).padStart(4)}px${flag}`,
    )
  }
  const flagged = results.filter((r) => r.flagged)
  console.log(`\n${flagged.length} page/viewport combination(s) flagged out of ${results.length}.`)
}

run().catch((err) => {
  console.error(err)
  process.exit(1)
})
