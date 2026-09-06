// Automated accessibility scan (Step 9.5), re-run as part of a UI Audit & Refinement pass.
// Runs @axe-core/playwright against every primary route (including /analytics, Feature 18,
// and the Threshold Simulator's expanded state, Feature 17) and prints critical/serious
// violations. This does not replace the manual Step 9 checklist (keyboard order, focus
// indicators, meaningful labels) - it's the separate mechanical check per
// docs/ui-audit-refinement.md §4.
//
// Usage (must run with cwd = frontend/, so playwright-core/@axe-core/playwright resolve):
//   cd frontend && node ../.claude/skills/check-axe.mjs

import { createRequire } from 'node:module'
import path from 'node:path'

const require = createRequire(path.join(process.cwd(), 'noop.cjs'))
const { chromium } = require('playwright-core')
const { AxeBuilder } = require('@axe-core/playwright')

const BASE_URL = process.env.CAPTURE_BASE_URL ?? 'http://localhost:5173'
const API_URL = process.env.API_BASE_URL ?? 'http://localhost:8000'

async function fetchJson(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} -> ${res.status}`)
  return res.json()
}

async function run() {
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
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } })
  const page = await ctx.newPage()

  let totalCritical = 0
  let totalSerious = 0
  const allResults = []

  for (const route of routes) {
    await page.goto(`${BASE_URL}${route.path}`)
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
    const results = await new AxeBuilder({ page }).analyze()
    const critical = results.violations.filter((v) => v.impact === 'critical')
    const serious = results.violations.filter((v) => v.impact === 'serious')
    totalCritical += critical.length
    totalSerious += serious.length
    allResults.push({ route: route.label, violations: results.violations })
    console.log(`\n=== ${route.label} (${route.path}) ===`)
    if (results.violations.length === 0) {
      console.log('  No violations.')
    } else {
      for (const v of results.violations) {
        console.log(`  [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} node(s))`)
      }
    }
  }

  await browser.close()

  console.log('\n\nSUMMARY')
  console.log('=======')
  console.log(`Total critical violations: ${totalCritical}`)
  console.log(`Total serious violations: ${totalSerious}`)
}

run().catch((err) => {
  console.error(err)
  process.exit(1)
})
