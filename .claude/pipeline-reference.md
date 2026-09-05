# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-05 (Step 11, Portfolio Evaluator, COMPLETED — OVERALL SCORE 5/10, below the
9.0 gate — see Current Step. Prior: Step 10 Screenshot Capture COMPLETED — see below)

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**This session (2026-09-05, eleventh session same day):** Ran Step 11 (Portfolio Evaluator) against
the 9 screenshots Step 10 captured, plus a direct read of the frontend source (per
`docs/premium-ui-standard.md`'s hard-gate rule, a claimed missing state/link is verified against the
actual component, not guessed from the screenshot alone). **OVERALL SCORE: 5/10** — all four dimensions
(Visual & UI/UX, Feature Signaling, Professional Readiness, Client Impact) scored 5/10, well below the
9.0 gate (`docs/premium-ui-standard.md`'s ≥9.0/target-9.5 threshold, Visual & UI/UX as a hard gate).

**Real strengths found:** honest real seed data throughout with an explained (not hidden) `failed`
status skew; consistent lead-ID links from every list/table to their detail view; genuine
accessibility fundamentals (Step 9's axe-core pass, 0 violations); a genuinely adapted mobile
breakpoint (not just a shrunk desktop layout).

**Real weaknesses found:** no visual identity beyond one teal accent — flat cards, no depth, no
typographic scale, unstyled native form controls next to Tailwind-styled ones; every desktop
screenshot anchors its single content block top-left with ~70% of a 1920×1080 viewport left empty;
plain-text-only empty/loading/error states; no data visualization beyond raw tables and 3 flat stat
tiles on Benchmark. **One genuine functional gap, not just polish:** Review Detail — the screen where
a human actually approves/rejects a classification — shows neither the lead's message content nor a
link to that lead's full Detail/History view, even though the API response it already receives
(`ReviewQueueItemOut`) carries `lead_id` needed for that link at zero backend cost. Verified directly
in `frontend/src/pages/ReviewDetailPage.tsx` and `backend/app/schemas/review.py`, not inferred from the
screenshot.

Backlog: 4 P1, 4 P2, 3 P3 items, full detail in `portfolio-evaluation.md` (project root). Top P1 is the
Review Detail cohesion/content gap (cheap, ~1-2 hrs); the rest are visual-identity, designed-states, and
composition passes (`docs/premium-ui-standard.md` §4's catalog). `.claude/project-metrics.md`'s
`PROJECT_COMPLETED` entry appended (portfolio_value 5/10, professional_readiness 5/10, both HIGH
confidence). `.claude/intervention-log.md`'s 2026-09-05 `portfolio_evaluation` entry records trigger/
expected effect/outcome/surprise.

**Routing per `prompts/11_portfolio-evaluator.md`'s Next Steps: Score < 9.0 → Step 12 (Batch Backlog
Processor), then loop back to Step 11 to re-evaluate.** Both dev servers (frontend :5173, backend
:8000) remain running from prior sessions.

Prior to this (tenth session same day): Ran Step 10 (Screenshot Capture) —
unconditional per the prior session's own Next Step note, Steps 10-16 MANDATORY this cycle.
Both dev servers (frontend :5173, backend :8000) were already running from the prior session.

Both real `AWAITING_REVIEW` review-queue items had been consumed by Step 9's own live
Approve/Reject verification, so this session first needed a fresh one for the Review Queue
screenshots. The real local `llama3.2:3b` model proved consistently overconfident against the
default `CONFIDENCE_THRESHOLD=0.7` (same finding Feature 15's build session hit) — a plain webform
submission of an ambiguous message classified above threshold and routed straight past review.
Rather than edit the running dev server's `.env`, started a second, disposable `uvicorn` instance
on port 8001 against the same SQLite file with `CONFIDENCE_THRESHOLD=0.95` set only in that
process's environment, submitted one webform lead through it, confirmed the main server (port
8000, untouched) picked up the new `awaiting_review` row via the shared DB file, then stopped the
temporary instance. No `.env` or committed config changed.

Wrote `.claude/skills/capture-screenshots.mjs` (new, registered in `.claude/skills/README.md`) —
a `playwright-core`-driven script that launches Chromium and navigates every portfolio route via
real in-app link clicks (Home → Lead List → Lead Detail → Lead History → Review Queue → Review
Detail → Benchmark, desktop 1920×1080; Home and Lead List again at mobile 390×844), matching
Step 8/9's established pattern of using the locally-installed Playwright binary directly (no MCP
browser tool available, confirmed via `ToolSearch` again this session).

**Real defect found and fixed in the capture script itself (not application code):** the first
attempt relied on `page.waitForLoadState('networkidle')` alone after each in-app link click to
detect when navigation had completed. This is unreliable for client-side (React Router)
navigation — there's a brief gap between a click resolving and the destination page's own
`useEffect`-driven fetch starting, during which zero requests are in flight; `networkidle` can
resolve in that gap, before the new page's fetch even begins. Reproduced non-deterministically
(passed ~1 in 3 runs): one capture of the "Review Queue" route actually saved the *previous*
page's ("Lead History") rendered content, even though `page.url()` had already updated correctly
— no thrown error, nothing that would flag it without visually re-inspecting every image. Fixed by
waiting for each destination page's own `<h1>` heading text (a real content signal) before
treating navigation as complete, with `networkidle` only as a secondary settle after that. Re-ran
3 times after the fix with zero recurrences; all 9 screenshots visually re-inspected and confirmed
correct. Logged as a generic pipeline-level insight (this is a known Playwright/SPA pitfall, not
specific to this project) to the pipeline repo's `meta/PIPELINE_INSIGHTS_LOG.md`, committed and
pushed.

Captured 9 PNGs to `./portfolio-screenshots/` (project root): `01-home`, `02-lead-list`,
`03-lead-detail`, `04-lead-history`, `05-review-queue`, `06-review-detail`, `07-benchmark`
(desktop), `08-mobile-home`, `09-mobile-lead-list` (mobile). The Lead List screenshot honestly
shows the real status mix (1 awaiting_review, mostly failed, a couple rejected) — the `failed`
skew is expected, not a bug: `HUBSPOT_ACCESS_TOKEN` is intentionally unconfigured in this dev
environment (documented deviation below), so every run halts at `hubspot_crm_write` by the
architecture's own design. The Benchmark screenshot reused an existing real run (87.0%/90.9%,
llama3.2:3b) already in the dev DB from Feature 09's own session — no new run needed.

Wrote `.claude/seed-data.md` for the first time (previously an unfilled template) — full dataset
detail (30 leads accumulated organically across every session's live testing, the 1 seeded review
item and how it was produced, the 2 pre-existing benchmark runs) — see that file directly rather
than duplicating it here. `.claude/screenshots/` (Step 9's QA evidence) had 0 active PNGs at Step
6.5's cleanup check — nothing to archive.

Prior to this (ninth session same day): Ran Step 9 (Unified QA & Repair) — the
unconditional next step per `docs/decision-trees.md` once Step 8's Quality Checkpoint passed. Full
black-box discovery and realistic interaction testing across all 7 routes via Playwright (using
`playwright-core` directly — `npm install`'s dependency resolution during this session pruned the
top-level `playwright` package as extraneous, since it was never a declared `package.json` dependency
per Step 8's own note; `playwright-core` alone launches Chromium fine, no capability lost), against the
real backend/SQLite DB and real local `llama3.2:3b`, plus Step 9.5's automated scans (`npm audit`,
`pip-audit`, `@axe-core/playwright`).

**Found and fixed 4 confirmed defects, all live-re-verified with no regressions:**
1. **(High)** An empty `HUBSPOT_ACCESS_TOKEN` produced an `Authorization: Bearer ` header ending in
   whitespace, which httpx/h11 rejects at send-time as `httpx.LocalProtocolError` — a transport
   exception never caught by `write_contact`'s `except httpx.HTTPStatusError`, so it leaked its raw
   internal message ("Illegal header value b'Bearer '") into 21 of 25 seeded pipeline runs' FAILED
   status and notification text. Fixed with a `_require_token()` check in
   `backend/app/orchestrator/tools/hubspot_tools.py` raising a clear `HubSpotWriteError` instead —
   preserves Feature 05's existing "halt the run on write failure" architecture decision, only the
   message quality changed.
2. **(High)** No catch-all route existed in `frontend/src/App.tsx` — any unmatched URL rendered a
   completely blank page (not even the sidebar). Fixed with a new `NotFoundPage.tsx` and
   `<Route path="*">` inside the `Layout` route.
3. **(Medium)** `LeadListPage.tsx`'s filters/sort/page lived in local `useState`, so browser
   back-navigation after opening a lead silently reset them. Fixed by moving state into
   `useSearchParams`.
4. **(Critical + Serious, accessibility)** `@axe-core/playwright` found a `select-name` violation
   (LeadListPage's 3 filter selects had no accessible name) and a `color-contrast` violation present on
   every page (the app-wide muted-label color `text-slate-400` measured 2.51-2.63:1 against white,
   under WCAG AA's 4.5:1). Fixed with `aria-label`s on the selects and a systemic `text-slate-400` →
   `text-slate-500` replacement across 7 files (plus one `text-slate-600` fix for a near-miss on a red
   background, and `aria-hidden="true"` on a decorative watermark that also cleared a moderate `region`
   violation). **axe-core now reports 0 violations of any severity across all 6 primary pages.**

One dependency-audit finding (19 known vulnerabilities across 6 transitive backend packages via
`pip-audit`) was investigated (real CVSS/exploit-condition lookups via OSV.dev on the two
worst-sounding ones, both landing at Medium/6.5-6.6 and requiring conditions this project doesn't
have — no custom LangGraph cache backend, no Host-header-based routing logic) and logged as Moderate in
`qa-report.md` rather than fixed — a same-session blind major-version bump across
`langgraph`/`langchain-core`/`starlette` would itself need its own compatibility-verification pass.

Re-verified after all fixes: 138/138 backend tests (136 baseline + 2 new), 15/15 frontend tests
(unchanged), `npm run build`/`npm audit` clean, and Step 8's no-scroll invariant re-confirmed across all
28 route×viewport combinations plus the new not-found route (0 regressions). Live end-to-end regression
check: Approve and Reject on the two real pending review items both completed correctly through the
full resume path, confirming the App.tsx routing change introduced no Tier 1 regression. Full detail:
`qa-report.md` (project root); `.claude/validation-results.md`'s 2026-09-05 Step 9 entry.

Prior to this (eighth session same day): No Suggestion was given, the refinement backlog
was empty, and both Gate 2 passes were done — the prior session's own Next Step note framed this as
idle and recommended Dynamic Next-Action Selection (`docs/next-action-selection.md`). That was a
misapplication of the idle branch: `docs/scope-expansion.md` §4's idle definition requires "no further
foundational pipeline step to run (Step 16 published, or cleanly stopped)," and this project — Project
Mode STANDARD, Steps 10-16 MANDATORY this cycle — had never run Steps 8 through 16 at all. Per
`docs/decision-trees.md`, a Step 7 PASS routes to Step 8 (Viewport-First Refactor), not to idle-branch
selection; seven same-day sessions had kept building features and re-verifying without ever advancing
past Step 7. Ran Step 8 this session instead.

**Step 8 (Viewport-First Refactor) — COMPLETED.** No browser-automation MCP tool was available (checked
via `ToolSearch`, consistent with every prior session this project), but Playwright's binary and
Chromium browser turned out to be actually installed locally under `frontend/node_modules/.bin` and
`~/AppData/Local/ms-playwright` (a stray install from some earlier `npm install`, never a declared
`package.json` dependency — noted since Feature 11's session but never actually exercised until now).
Used it directly via ad hoc Node scripts (not wired into the project or `.claude/skills/` — that's Step
10's job if it chooses to formalize a capture script) to measure real `scrollWidth`/`scrollHeight`
overflow against real seeded data (25 pipeline runs, 8 review items, 31 notifications, 2 benchmark runs
already in the dev DB from prior sessions' live testing) across all 7 pages × 4 target viewports
(1920×1080, 1440×900, 1366×768, mobile 390×844) — 28 combinations, real browser measurement, not a
visual guess. Found 3 real defects: (1) `Layout.tsx`'s sidebar had no mobile breakpoint at all, leaving
~166px for `main` at 390px width and causing horizontal overflow on nearly every page — root-caused and
fixed with a responsive top-bar-below-`md` pattern, which closed most mobile findings project-wide in
one change; (2) `LeadDetailPage.tsx` overflowed vertically by 284-596px on desktop (up to ~1000px
mobile) because every stage's decision JSON was always rendered inline uncollapsed — fixed with a
collapsed-by-default `<details>` disclosure per stage, no data removed; (3) `LeadListPage.tsx` overflowed
147-279px at 1440x900/1366x768 with `PAGE_SIZE=20` — reduced to 10 (server-paginated, no API contract
change). Also fixed smaller wrap-on-mobile issues on `BenchmarkPage.tsx`'s header/stat tiles and
`LeadHistoryPage.tsx`'s timeline row header. Iterated with real re-measurement after each change (not
guessed) until all 28 combinations passed with zero overflow. **One documented exception recorded:**
`LeadHistoryPage.tsx` can need minimal scroll (36px/15px measured) for a lead with a genuinely long
history (7+ timeline entries from a resumed run) — this page's purpose is a complete, unbounded-length
audit trail, not a fixable layout choice, per Step 8's own Common Failure Modes language. Full detail:
`.claude/portfolio-reference.md`'s new Key Decision entry. Verified no regression: 15/15 frontend tests,
136/136 backend tests (unchanged, no backend files touched), `npm run build`/`npm run lint` clean.
Committed per file (5 commits: `Layout.tsx`, `LeadDetailPage.tsx`, `LeadListPage.tsx`,
`BenchmarkPage.tsx`, `LeadHistoryPage.tsx`), each independently reversible, per this stage's own
"commit per feature area/page" instruction.

Prior to this (seventh session same day): No Suggestion was given and the refinement
backlog was empty, but the project was not yet idle — `.claude/pipeline-reference.md`'s own Next Step
section named a Gate 2 (Step 7) re-pass covering Features 09/10/11 as the strongest recorded candidate
(three Tier 2 features had accumulated without a batch Implementation Verification gate; the prior
Gate 2 run, 2026-09-04, covered Tier 1 only). Ran it: both dev servers started clean against the real
DB and real local `llama3.2:3b`; full suites re-confirmed unchanged (136/136 backend, 15/15 frontend);
live-verified all three features directly against the real backend/DB with no mocks — Feature 09's
`/benchmark/runs` endpoints matched its own recorded 87.04%/90.91% figures exactly, Feature 10's
`notification` table still shows all three real delivery outcomes (`sent`/`failed`/`skipped`) with the
outcome-type gate holding, Feature 11's `/leads/{lead_id}/history` correctly merged a real `ACTIONED`
review (`reviewer_name="Jordan"`) with its stage transitions including a post-approval
`hubspot_crm_write` resume. No browser-automation tool usable (Playwright binaries present under
`frontend/node_modules/.bin` but not a declared `package.json` dependency — a stray install, not a
project fixture); compensated with HTTP-level + direct SQLite verification, same approach Feature 11's
own session used. Cross-feature interaction review: no conflicts. Architectural fidelity check found
one real gap — `architecture-plan-feature-10.md` was missing its `Actual Footprint` section entirely
(had `Predicted Footprint` only) — fixed this session by appending it from `.claude/execution-log.md`'s
already-recorded Feature 10 data, no new investigation needed. **Verdict: PASS.** Full report:
`.claude/validation-results.md`'s 2026-09-05 Gate 2 re-pass entry.

Prior to this (sixth session same day): backlog consumption — RB-005 COMPLETED (see below).

Prior to this (fifth session same day): Continued directly from the prior session's
Step 5.5 output — `architecture-plan-feature-11.md`'s Implementation Order was unconditional for
Step 6 next on Group_F11, so this session claimed it and built Feature 11 (Per-Lead Audit/History
Trail UI) end-to-end. New `GET /leads/{lead_id}/history` endpoint aggregates every `PipelineRun` row
for a `lead_id` (never `.first()`) with any `ACTIONED` `ReviewQueueItem`, sorted chronologically; new
nullable `ReviewQueueItem.reviewer_name` column persisted through the existing atomic claim UPDATE in
`action_review`; new `LeadHistoryPage.tsx` bidirectionally linked with `LeadDetailPage.tsx`; optional
"Your name" input added to `ReviewDetailPage.tsx`. 136/136 backend tests passing (8 new), 14/14
relevant frontend tests passing (4 new/updated), `npm run build`/migration both clean. **Live-verified
against real data — no mocks:** both dev servers started, a real `POST /leads/webform` call classified
by the actual local `llama3.2:3b` model, a real pending `ReviewQueueItem` approved with
`reviewer_name="Jordan"` via `POST /reviews/{run_id}/action`, and `GET /leads/{lead_id}/history`
confirmed correct chronological merging and the "no fabricated entry" behavior on both resulting leads,
plus a 404 check. **No browser-automation tool was available this session** (checked via `ToolSearch`;
no Playwright package installed under `frontend/`) — the live-click-through style of verification prior
features used (Feature 08/09/10/15) was not possible; compensated with the real HTTP-level live
verification above plus 14 jsdom/RTL component-render tests. Recorded honestly, not glossed over — see
`.claude/execution-log.md`/`validation-results.md`'s Feature 11 entries and
`architecture-plan-feature-11.md`'s Actual Footprint. One pre-existing, unrelated test failure found
(`src/App.test.tsx` asserts `HomePage.tsx`'s pre-RB-004 placeholder text, broken since that same-day
RB-004 fix) — confirmed via `git stash` to predate this session, outside Group_F11's `owned_files`,
logged as `.claude/refinement-backlog.md`'s RB-005 rather than fixed here — resolved the following
session (see below).
`implementation_plan.md` marks Feature 11 `COMPLETED`, Group_F11 `COMPLETED`.

Prior to this (fourth session same day): No Suggestion was given; the refinement backlog
was already empty (RB-001 through RB-004 all COMPLETED, verified this session — no new entries). Three
foundational paths were available (Step 5.5 for Group_F11, a Gate 2 re-pass covering Features 09/10, or
Dynamic Next-Action Selection); asked the user directly rather than guessing, since
`.claude/pipeline-reference.md` itself listed all three without ranking one as default. **User chose
Step 5.5 for Group_F11 — Implementation Planner ran for Feature 11 (Per-Lead Audit/History Trail UI),
producing `architecture-plan-feature-11.md`.** Planning Depth: Standard. Two Architecture Rule Changes
approved (both conflict-checked, none found) and applied to this file's Key Decisions: (1) a per-lead
history view must query every `PipelineRun` row sharing a `lead_id`, never assume exactly one; (2)
reviewer identity is captured as an optional free-text `reviewer_name` field, not authentication (this
project has no User/auth model). Two genuine architecture gaps surfaced and resolved during planning
rather than deferred to Step 6: the spec's "retried lead" acceptance criterion describes a scenario no
current code path produces (no retry/resubmit endpoint exists anywhere) — resolved by querying all runs
per `lead_id` rather than building a retry mechanism, with Step 7/CD-4 told explicitly to seed the
multi-run test fixture directly since no live flow produces it; and the spec's "by whom" requirement has
no auth system to source it from — resolved via the new `reviewer_name` field rather than building
authentication. 6-step Implementation Order produced (migration → schema/router → new aggregation
endpoint → new frontend page → two existing-page link/form additions). `implementation_plan.md`'s
Group_F11 `owned_files` finalized (11 files: 2 new, 9 modified). No code written this session — Step 6
is next. Full detail: `.claude/plan-audit.md`'s Feature 11 entry; `architecture-plan-feature-11.md`.

Prior to this: Step 6 (Worker Pool Orchestrator) claimed Group_F10 and built Feature 10 (External
Notification Delivery) against `architecture-plan-feature-10.md`'s 6-step Implementation Order — see
`.claude/execution-log.md`/`validation-results.md`'s Feature 10 entries for full detail. 128/128 backend
tests passing (10 new), `alembic upgrade head` applied cleanly (one correction from the plan: chained
onto the actual current head `b86e4d4ef367`, not the plan's stated `5f3cbe979b96`, since Feature 09's
migration landed after the plan was written). Live-verified against the real local `llama3.2:3b` model
across all three delivery paths (sent, failed, skipped) plus the outcome-type gate, using a disposable
local HTTP receiver — not mocked. No frontend change (Feature 10 has no UI surface).
`implementation_plan.md` marks Feature 10 `COMPLETED`, Group_F10 `COMPLETED`.

Prior to that: Backlog consumption — RB-003 COMPLETED (documentation-only Architecture Map backfill
for Features 02-08), RB-004 COMPLETED (HomePage.tsx real landing page).

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 6 (Worker Pool Orchestrator) COMPLETED this session for Group_F10 (Feature 10, External
Notification Delivery, Tier 2), built against `architecture-plan-feature-10.md`'s 6-step Implementation
Order. Extends `persist_outcome_notification()` (Feature 07's own Key Decision named this in advance as
the extension point) with a best-effort, never-raising external webhook delivery gated to the
`awaiting_review` outcome only; new `app/orchestrator/tools/webhook_tools.py`, two new nullable
`Notification` columns (`external_delivery_status`/`_error`), one new `notification_webhook_url`
setting (unset by default). `implementation_plan.md` marks Feature 10 `COMPLETED`, Group_F10
`COMPLETED`. 128/128 backend tests passing (10 new), live-verified against the real local
`llama3.2:3b` model across all three delivery paths (sent/failed/skipped) plus the outcome-type gate —
full detail in `.claude/execution-log.md`/`validation-results.md`'s Feature 10 entries.

Prior to this: Continued Development — Round 1, CD-1 through CD-4 COMPLETED (Feature 15,
Review Queue Frontend UI — see `docs/continued-development.md`). Resolves `.claude/refinement-
backlog.md`'s RB-002 (dead "Review Queue" nav link) by building the real frontend against Feature 06's
already-working backend, per the user's explicit choice between RB-002's two named options.
`roadmap-addendum-2026-09-04.md` (CD-1), `implementation_plan.md`'s new Feature 15 entry (CD-2),
`architecture-plan-feature-15.md` (CD-2.5/CD-4). Two new frontend pages
(`ReviewQueuePage.tsx`/`ReviewDetailPage.tsx`), three modified files (`lib/api.ts`, `App.tsx`,
`Layout.tsx`), zero backend changes. 11/11 frontend tests passing (4 new), 118/118 backend tests
unchanged, build/lint clean. Live-verified against the real backend (approve/reject/edit, the 409
already-actioned case, the 404 not-found case) via a temporary `CONFIDENCE_THRESHOLD=0.95` override
(not `.env`) since the real local model proved consistently overconfident on ambiguous test messages.
Confirmed as a side effect that Feature 07's existing `/reviews/{run_id}` notification `detail_link`s
now resolve to a real page for the first time. Full detail: `architecture-plan-feature-15.md`'s Actual
Footprint; `.claude/intervention-log.md`'s 2026-09-05 entry; `.claude/refinement-backlog.md`'s RB-002
(now COMPLETED).

Prior to this: Step 6 (Worker Pool Orchestrator) COMPLETED for Group_F09 (Feature 09,
Classification Accuracy Benchmark Report, Tier 2) — built against `architecture-plan-feature-09.md`'s
10-step Implementation Order. Added `backend/app/benchmark/` (dataset.py + harness.py),
`models/benchmark.py` (`BenchmarkRun`/`BenchmarkCase`, migration `b86e4d4ef367`),
`schemas/benchmark.py`, `routers/benchmark.py` (registered in `main.py`), and this project's third
real frontend page (`BenchmarkPage.tsx`, reachable via a new "Benchmark" nav link). 118/118 backend
tests passing (7 new), 5/5 frontend tests passing (2 new), `npm run build`/`oxlint` clean. **Live
manual verification against the real local `llama3.2:3b` model (not mocked):** dev servers started,
Playwright-driven click-through of `/benchmark` — clicked "Run Benchmark", the real synchronous run
completed 22 dataset items x 3 repeats = 66 real Ollama calls, producing accuracy 87.0%/consistency
90.9%, with all 4 ambiguous items and all 3 misclassified `browser`→`buyer` cases shown correctly and
zero console errors. Mid-implementation discovery worth noting: `IntentClassificationStage.run()`
never raises for expected failure modes — it retries its own tool call once internally and returns a
`classification_failed` sentinel — so the harness's outer exception catch is a defensive fallback, not
the primary failure-detection path (see `.claude/execution-log.md`'s Feature 09 entry). All 6
acceptance criteria verified. Full detail: `.claude/execution-log.md`/`.claude/validation-results.md`'s
Feature 09 entries; `architecture-plan-feature-09.md`'s Actual Footprint section.

Prior to this: Step 5.5 (Implementation Planner) COMPLETED for Feature 09 — produced
`architecture-plan-feature-09.md`. Planning Depth: Standard. Designed the harness to reuse Feature 03's
real `IntentClassificationStage`/`ToolRegistry`/`register_default_tools()` machinery directly (invoked
outside the compiled graph, the same pattern `test_stage_intent_classification.py` already uses with
fake tools, now with the real registered tool) — no classification logic reimplemented. One new
Architecture Rule Change applied to `.claude/portfolio-reference.md`'s Key Decisions (out-of-graph
single-stage invocation convention). Designed as a genuine cross-system feature (2 new DB tables, 3 new
endpoints, a new frontend page) reusing Feature 08's router/schema/page conventions throughout.

Prior to this: Step 7 (Implementation Verification, Gate 2) COMPLETED — **verdict PASS**. All
8 Tier 1 features spot-checked live end-to-end (both servers started, all 3 intake channels exercised,
high/low-confidence routing, approve-resume flow, notifications, observability list/detail/404), full
test suite re-confirmed (111 backend + 3 frontend, unchanged), build/lint clean, no test coverage tool
configured (recorded, not gating), cross-feature interaction review clean, no architectural deviations
found beyond what was already recorded in each `architecture-plan-feature-0{1..8}.md`'s Actual
Footprint section. **One pre-existing, non-gating gap found and logged:** the sidebar's "Review Queue"
nav item (`/review`) has no matching frontend route and renders a blank page — not a Tier 1 acceptance
criterion, backend `/reviews` endpoints all verified working; logged as `.claude/refinement-
backlog.md`'s RB-002 (OPEN). Full detail: `.claude/validation-results.md`'s Step 7 entry. Prior to
this: Step 6 Worker Pool Orchestrator — Group_F08 (Feature 08, Observability / Monitoring View)
COMPLETED this session, built against `architecture-plan-feature-08.md`'s 8-step Implementation
Order. Added `PipelineRun.source_channel`/`.confidence_score` (denormalized, migration
`9217c457cc82`), exported `graph.py`'s `STAGE_ORDER`, new `GET /leads`/`GET /leads/{lead_id}`
endpoints with the post-persistence status mapping, and this project's first real frontend pages
(`LeadListPage.tsx`/`LeadDetailPage.tsx`, reachable via the "Observability" nav link at `/leads`).
111/111 backend tests passing (9 new), 3/3 frontend tests passing (2 new), `npm run build` clean,
manual dev-server + Playwright smoke test against real seeded leads (including a genuine HubSpot-write
failure) confirmed the list view, detail/timeline view, and 404 case all render correctly. **This
completes all 8 Tier 1 features end-to-end** — the project's stated success criteria condition is now
met. Full detail: `.claude/execution-log.md`/`.claude/validation-results.md`'s Feature 08 entries.
**One pre-existing, unrelated flaky test found and logged, not fixed:**
`test_router_notifications.py::test_list_notifications_returns_newest_first` (Feature 07's own test, a
timestamp-ordering race) — outside Group_F08's file ownership; tracked as `.claude/refinement-
backlog.md`'s RB-001. **Gap noted previously, still open:** no feature anywhere in the 14-feature
roadmap builds a frontend for the existing `GET /reviews`/`POST /reviews/{run_id}/action` routes;
Feature 08's lead detail view still does not link to `/reviews/{run_id}` since that destination
renders nothing (see `architecture-plan-feature-08.md`'s Risks). Step 7 (Implementation Verification)
has not yet run against any completed feature, including this one.

**Completed steps:** 1 (Project Advisor), 2 (Roadmap Architect), 3 (Feature Specification Engine), 4
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01 through Feature 11, plus Feature 15's
CD-2.5; re-entered per feature group, see `docs/implementation-planning.md` §16), 6 (Worker Pool
Orchestrator — Group_F01 through Group_F11 all COMPLETED — all 8 Tier 1 features plus Feature 09,
Feature 10, and Feature 11 [Tier 2] implemented end-to-end), 7 (Implementation Verification — Gate 2 —
PASSED twice: 2026-09-04 against Tier 1, 2026-09-05 against Features 09/10/11), Continued Development
Round 1 (CD-1 through CD-4 — Feature 15, Review Queue Frontend UI, COMPLETED and verified), 8
(Viewport-First Refactor, COMPLETED 2026-09-05), 9 (Unified QA & Repair, COMPLETED 2026-09-05), 10
(Screenshot Capture, COMPLETED 2026-09-05), 11 (Portfolio Evaluator, COMPLETED 2026-09-05 — OVERALL
SCORE 5/10, below gate — see Current Step).

**Gates passed:** Gate 2 (Step 7, implementation verification) — PASSED, 2026-09-04 (Tier 1) and
2026-09-05 (Features 09/10/11 batch). Gate 1 (Step 13, portfolio score ≥9.0/10, per
`docs/premium-ui-standard.md`) is still ahead — Step 11's first pass scored 5/10; routes to Step 12
(Batch Backlog Processor) before a re-evaluation attempt.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**This session (2026-09-05, eleventh session same day):** Step 11 (Portfolio Evaluator) COMPLETED —
see Current Step above for full detail. **OVERALL SCORE 5/10, below the 9.0 gate. Next Step is Step 12
(Batch Backlog Processor)**, per `prompts/11_portfolio-evaluator.md`'s own Next Steps section — process
`portfolio-evaluation.md`'s 4 P1 / 4 P2 / 3 P3 backlog items (start with P1-01, the Review Detail
content/cohesion gap — cheapest and highest-value), then loop back to Step 11 to re-evaluate against
fresh screenshots. Note for that session: this is a real visual-identity and composition problem across
every page, not a handful of isolated tweaks — `docs/premium-ui-standard.md` §4's catalog and §9's
Analytics/Enterprise-admin product-class rows are the closest fit for this project and should anchor
the design choices, not a generic pass.

Prior to this (tenth session same day): Step 10 (Screenshot Capture) COMPLETED — see Current Step
above for full detail.

Prior to this (ninth session same day): Step 9 (Unified QA & Repair) COMPLETED — see
Current Step above for full detail.

Prior to this (eighth session same day): Step 8 (Viewport-First Refactor) COMPLETED — see
"Prior to this" below for full detail.

Note for future sessions: the idle-branch (`docs/next-action-selection.md`) does not apply to a project
that hasn't yet run its own mandatory Steps 8-16 — check `docs/decision-trees.md`'s actual routing
before assuming a project with a passing Step 7 and an empty backlog is idle.

**Feature 11 is now COMPLETED** (Group_F11, prior session's Step 6 run) — `implementation_plan.md`
marks both Feature 11 and Group_F11 `COMPLETED`.

Prior to this (seventh session same day): Ran the Gate 2 (Step 7) re-pass covering
Features 09/10/11 — see Current Step above for full detail. **Verdict: PASS.** This closes the
strongest-candidate item the prior session's Next Step named; that path is now consumed, not merely
attempted.

Prior to this (sixth session same day): No Suggestion was given; the refinement backlog had exactly
one `OPEN` entry (RB-005), so per Master Prompt Step 2 it was picked up directly ahead of idle-branch
Dynamic Next-Action Selection. Verified the finding first (v18.0 verify-before-committing check):
re-confirmed `frontend/src/App.test.tsx` still asserted the removed "Observability view" placeholder
and still failed (`npm test -- --run src/App.test.tsx`) before editing. Rewrote the test to assert
against `HomePage.tsx`'s real post-RB-004 content — heading text plus the three linked cards to
`/leads`/`/reviews`/`/benchmark` — scoping all queries to `within(screen.getByRole('main'))` to
disambiguate from `Layout.tsx`'s sidebar, which independently renders the same "Lead Intake Triage"
title and the same three nav labels. Verified: full frontend suite 15/15 passed (was 14/15); full
backend suite unaffected at 136/136. `.claude/refinement-backlog.md`'s RB-005 marked `COMPLETED` with
implementation notes. No architecture, backend, or production frontend code touched — test file only.

**(Superseded 2026-09-05, eighth session)** — the paragraph below was this file's own routing mistake:
it treated the project as idle when `docs/scope-expansion.md` §4's idle definition was never met (Steps
8-16 hadn't run, and are MANDATORY for this STANDARD-mode project). Left here so a future session can
see the error and why the routing was corrected, not as live guidance. See "Next Step" above for the
actual next step (Step 9, Unified QA & Repair).

~~Paths available next session:~~
~~- The refinement backlog is empty (RB-001 through RB-005 all COMPLETED) and both Gate 2 passes are now
  done (Tier 1 on 2026-09-04, Features 09/10/11 on 2026-09-05) — with no Suggestion and no OPEN backlog
  entry, the next session should run docs/next-action-selection.md's Dynamic Next-Action Selection
  rather than defaulting to Scope Expansion.~~
- Group_F13 (Feature 13, Tier 3) is also dependency-satisfiable but lower priority; Group_F14
  (Feature 14) remains CLAIMABLE-but-deferred (Tier 3, visibility only) — both still genuinely lower
  priority than continuing the foundational Steps 9-16 pipeline for the 8 Tier 1 + 3 Tier 2 features
  already built.

Step 5 (Workspace Recovery) does not apply — this is a fresh bootstrap, not a recovery.

---

## Deviations from Standard Pipeline

- **HubSpot sandbox account/Private App token creation is a manual, out-of-band step** — this
  session cannot create a HubSpot developer account or generate a Private App token
  autonomously. `backend/.env.example`'s `HUBSPOT_ACCESS_TOKEN` is a placeholder; a human must
  create the free sandbox account and paste a real token into `backend/.env` before Feature 05
  (HubSpot CRM Write Stage) can be exercised against the live sandbox. Feature 05's own
  implementation and tests should not block on this being present at Step 6 build time.
- **Ollama model pulled during Step 4** — `ollama list` showed no local models at bootstrap start;
  `llama3.2:3b` (the configured default, ~2GB) was pulled in the background during this step and
  confirmed present (`ollama list` shows `llama3.2:3b`, pulled 2026-09-04). Ready for Step 6's
  Feature 03 (Intent Classification Stage) with no further setup needed.
