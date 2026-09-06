# QA Report — Lead Intake Triage Agent

## Executive Summary
Overall Status: **PASS**
Date: 2026-09-05

Comprehensive black-box QA of all 7 routes plus the automated Step 9.5 scans, run against the real backend (SQLite + local `llama3.2:3b`), not mocks. Discovery surfaced two functional defects (one high, one medium) and two accessibility defects (one critical, one serious, both systemic) — all four were root-caused and fixed this session, then re-verified live. No regressions: full test suites, build, and lint re-confirmed after every fix; the Step 8 no-scroll invariant re-checked across all 28 page×viewport combinations plus the two new routes this session touched.

## Scope Covered
- Application areas explored: all 7 routes (Home, Lead List, Lead Detail, Lead History, Review Queue, Review Detail, Benchmark) plus one previously-nonexistent route class (unmatched URLs)
- Total features discovered: 7 pages / workflows (intake→triage observability, filtering/sorting/pagination, human review approve/reject/edit, per-lead history, benchmark run)
- Total defects found: 4confirmed (2 functional, 2 accessibility) + 1 dependency-audit finding (moderate, logged not fixed)
- Total defects fixed: 4
- Defects remaining: 0 critical/high; 1 moderate (dependency audit, documented below)

## Tested Workflows
- Home → linked-card navigation to Observability/Review Queue/Benchmark: ✅
- Lead List: status/channel filter, sort, pagination, row→detail navigation, **filter state across back-navigation**: ✅ (after fix)
- Lead Detail: stage timeline, collapsible stage output, failed-stage banner, link to History: ✅
- Lead History: chronological merge of pipeline runs + actioned review: ✅
- Review Queue → Review Detail: Approve, Reject, and the already-actioned 409 conflict path, live end-to-end through `crm_write`/`notify` resume: ✅
- Benchmark: page loads, "Run Benchmark" control present (full 66-call live run already verified in Step 7 Gate 2 re-pass this same day; not re-run here to avoid redundant load on the local model) : ✅
- Not-found handling: nonexistent lead id, nonexistent review run id (both already had correct in-app messaging), and **any unmatched URL** (previously blank, now fixed): ✅

## Defects Fixed

| Defect ID | Severity | Description | Fix | Status |
|---|---|---|---|---|
| QA-1 | High | Empty `HUBSPOT_ACCESS_TOKEN` produced `Authorization: Bearer ` (trailing-space header), which httpx/h11 rejects at send-time as `httpx.LocalProtocolError("Illegal header value b'Bearer '")` — a transport-level exception never caught by `write_contact`'s `except httpx.HTTPStatusError`, so it propagated verbatim into the pipeline run's FAILED status and the outcome notification text. Affected 21 of 25 seeded pipeline runs (84%) with a message indistinguishable from a raw crash. | Added `_require_token()` in `backend/app/orchestrator/tools/hubspot_tools.py`, called at the top of both `search_contact` and `write_contact`, raising `HubSpotWriteError("HubSpot access token is not configured...")` when the token is falsy. Preserves the existing "halt the run on write failure" architecture decision (Feature 05) — only the message quality changed. 2 new tests added (`test_orchestrator_tools.py`). | Fixed, live-verified |
| QA-2 | High | Navigating to any URL not matching a declared route (mistyped path, stale bookmark, browser back/forward edge case) rendered a completely blank page — no sidebar, no message, `document.body.innerText === ''`. `App.tsx` had no catch-all route. This is the same failure class as the already-fixed RB-002 (dead `/review` link), but unbounded — any unknown path, not just one known dead link. | Added `frontend/src/pages/NotFoundPage.tsx` (styled consistent with the existing not-found patterns in `LeadDetailPage`/`ReviewDetailPage`) and wired `<Route path="*" element={<NotFoundPage />}>` inside the `Layout` route in `App.tsx`, so the sidebar/nav persists and a friendly "This page doesn't exist" message with a link home is shown. | Fixed, live-verified |
| QA-3 | Medium | `LeadListPage`'s status/channel/sort/page filters lived in local `useState`, not the URL. Filtering to e.g. "Failed", opening a lead, then using the browser Back button silently reset to the default unfiltered view — a natural, common workflow losing user state. | Refactored `LeadListPage.tsx` to derive filter/sort/page state from `useSearchParams` (React Router, already a dependency) instead of local `useState`, via a small `updateParams()` helper. Filters now round-trip through the URL, so Back/Forward and page reload preserve them. | Fixed, live-verified |
| QA-4 | Critical (accessibility) | axe-core flagged `select-name`: all 3 filter `<select>` elements on `LeadListPage` (status, channel, sort) had no accessible name — no `<label>`, `aria-label`, `aria-labelledby`, or `title`. Screen-reader users could not tell what each control filtered/sorted by. | Added `aria-label` ("Filter by status" / "Filter by channel" / "Sort by") to each `<select>`. | Fixed, verified via re-run axe-core scan (0 violations) |
| QA-5 | Serious (accessibility) | axe-core flagged `color-contrast` on every one of the 6 scanned pages. Root cause: `text-slate-400` (#90a1b9) was used app-wide as the "muted label" color for `<dt>` field labels, empty-state table text, timestamp spans, and the dev build-time watermark — against white/near-white backgrounds this measures 2.51–2.63:1, well under the WCAG AA 4.5:1 minimum. A related near-miss (4.35:1) was found on the stage-status badge text against its red "Failed" background. | Replaced all 11 `text-slate-400` occurrences across `BuildIndicator.tsx`, `LeadDetailPage.tsx`, `LeadHistoryPage.tsx`, `LeadListPage.tsx`, `ReviewDetailPage.tsx`, `ReviewQueuePage.tsx`, `BenchmarkPage.tsx` with `text-slate-500` (≈4.6:1, verified via manual luminance calculation before applying). Bumped the stage-status badge span from `text-slate-500` to `text-slate-600` to clear its red-background near-miss safely. Also marked the decorative build-time watermark `aria-hidden="true"` (see QA-6). | Fixed, verified via re-run axe-core scan (0 violations) |
| QA-6 | Moderate (accessibility) | axe-core flagged `region` on every page: the fixed-position `BuildIndicator` "Updated: [timestamp]" dev watermark rendered outside any landmark (`<main>`/`<nav>`), and as non-essential decorative content had no reason to be exposed to assistive tech in the first place. | Added `aria-hidden="true"` to `BuildIndicator.tsx`'s root `div` — correct fix for decorative auxiliary content, rather than forcing it into a landmark. | Fixed, verified via re-run axe-core scan (0 violations) |

## Remaining Issues

### 1. Dependency audit: RESOLVED (2026-09-06 dependency-upgrade round)
- **Original finding:** 19 (later 26, per Continual Refinement Round 2's re-scan) known vulnerabilities across 6-7 transitive backend packages — `starlette 0.38.6`, `langgraph-checkpoint 2.1.2`, `langgraph 0.2.34`, `langchain-core 0.3.86`, `python-dotenv 1.0.1`, `pytest 8.3.3` (plus `pip` itself, a packaging tool not a shipped dependency). All assessed Moderate and non-exploitable as this project was actually deployed (no custom cache backend, no proxy-based Host-header trust logic, single local user) — see the prior version of this entry (git history) for the full CVSS/exploit-path verification that justified deferring the fix.
- **Resolution:** Ran the dedicated compatibility-verification pass this finding's own "Recommended action" called for. Upgraded `python-dotenv` 1.0.1→1.2.2, `pytest` 8.3.3→9.0.3 (+ `pytest-asyncio` 0.24.0→1.4.0 for compatibility), `langgraph` 0.2.34→1.2.11 (pulling in `langgraph-checkpoint` 4.1.1 and `langchain-core` 1.6.2 transitively — both exceed every advisory's fix-version requirement), and `fastapi` 0.115.0→0.141.1 (pulling in `starlette` 1.6.0 transitively — likewise exceeds every advisory's fix-version requirement). No code in this project imports `langchain_core` directly (grep-confirmed) — it's a pure transitive dependency of `langgraph`, which significantly limited the breaking-change surface.
- **Verification:** Upgraded incrementally on a branch, running the full backend suite after each step. Final state: 171/171 backend tests passing, 98% coverage (unchanged), `pip check` clean, zero `tsc`/lint impact (backend-only change, no frontend files touched). `pip-audit` now reports **0 known vulnerabilities** (was 26 across 7 packages, including `pip` itself after a venv `pip` upgrade). Live-verified beyond the test suite: started a real `uvicorn` instance against the accumulated dev database, submitted a real lead through `POST /leads/webform`, and confirmed the full `LangGraph` `StateGraph` executed correctly end-to-end under the new major versions — `intake_parsing`→`intent_classification` (a real Ollama call)→`data_enrichment` all `COMPLETED`, `hubspot_crm_write` `FAILED` with the expected placeholder-token message (the same known dev-environment limitation every prior session's live verification has hit, not a new defect), `outcome_notification` correctly firing on the failure path — then confirmed `GET /leads/{lead_id}` rendered the full stage timeline correctly. This is the same live-verification bar every Continued Development round in this project uses, not just a green test suite.
- **User impact:** None — this was a proactive fix of a non-exploitable-as-deployed finding, done specifically because the advisory count had grown across two Continual Refinement rounds and the pipeline's own guidance was to weigh it more seriously once idle with nothing else queued.

### 2. Pre-existing lint warning: `react(set-state-in-effect)` in 5 pages (Low)
- Confirmed pre-existing (not introduced this session) via `git stash` comparison against the last commit — same 5 warnings, same files, present before any Step 9 changes. `LeadDetailPage.tsx`, `LeadHistoryPage.tsx`, `LeadListPage.tsx`, `ReviewDetailPage.tsx`, `ReviewQueuePage.tsx` all call `setLoading(true)` synchronously inside their data-fetch `useEffect` — a completely standard fetch pattern that a stricter oxlint rule (apparently newly active — Step 8's session recorded `npm run lint` clean) now flags as a style nit, not a functional issue.
- **Reason not fixed:** Refactoring the fetch pattern across 5 files is a broader style change outside this session's contained-defect scope; no functional impact.
- **Recommended action:** A future Continual Refinement round, Testing/Reliability or code-quality dimension.

## Validation Results
- Backend Unit Tests: ✅ PASS (138/138 — 136 baseline + 2 new for the HubSpot token fix)
- Frontend Unit Tests: ✅ PASS (15/15, unchanged)
- Responsive (Desktop 1920×1080 / 1440×900 / 1366×768): ✅ 0 overflow across all 7 routes
- Responsive (Tablet 768×1024): ✅ 0 overflow (spot-checked new/changed routes)
- Responsive (Mobile 390×844): ✅ 0 overflow across all 7 routes + the new not-found route
- Keyboard Navigation: ✅ Tab order reaches nav links correctly; no `outline-none`/focus-suppression anywhere in the codebase (grep-verified)
- Accessibility (axe-core, all 6 primary routes): ✅ 0 critical/serious/moderate/minor violations (after fixes; started at 1 critical + 1 serious + 1 moderate per page)
- Console Errors: ✅ none across all tested workflows (404 lookups for intentionally-nonexistent ids correctly log an expected fetch-404 to console — not a JS exception, not a defect)
- Network Failures: ✅ none unexpected
- Dependency Audit: ✅ 0 vulnerabilities (backend and frontend), resolved 2026-09-06 — see Remaining Issues §1
- Automated Accessibility Scan: ✅ 0 critical/serious after fixes (axe-core via `@axe-core/playwright`, all 6 primary routes)
- Performance Baseline (frontend bundle size, no prior baseline existed): **307.21 kB / 97.89 kB gzip** (`vite build` output) — recorded as this project's baseline; no regression gate applies until a future comparison point exists (a >15% increase or Lighthouse drop >5 points would be material per `docs/continued-development.md` CD-4's default)
- Document-processing anti-pattern check: N/A — `project-definition.md` records Document Processing: NONE

## Final Verdict
**PASS.** All discovered functional and accessibility defects were root-caused, fixed, and live-verified with no regressions (full test suites, build, lint, and the Step 8 no-scroll invariant all re-confirmed). The one dependency-audit finding, originally documented and deferred with an explicit, verified non-exploitability rationale, was itself resolved in a later dedicated compatibility-verification round (2026-09-06) — see Remaining Issues §1.

**Note for Step 10:** both `AWAITING_REVIEW`/`PENDING` review-queue items present at session start were consumed during live QA testing of the Approve/Reject workflow (one approved, one rejected) — Step 10 will need to seed at least one fresh pending review item to demonstrate that state in screenshots, consistent with `seed-data.md`'s own role of constructing the screenshot dataset fresh. Two additional `FAILED` test leads (`10b276d9…`, `de7bd1d6…`) were created live via `/leads/webform` to verify the QA-1 fix — left in place rather than manually deleted via raw SQL (no delete-lead API exists, and direct DB deletion risks orphaning related `stage_trace`/`notification` rows); Step 10 can reset/reseed as needed per its own dataset-construction process.
