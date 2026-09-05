# Refinement Backlog — [PROJECT_NAME]

Persistent, cross-round record of every actionable finding `docs/continual-refinement.md`'s audit loop
has produced. Distinct from `refinement-audit.md` (project root): that file is the historical, per-round
score record; this file is the current, individually-addressable view of unresolved (and resolved) work.
Full schema and lifecycle rules: `docs/continual-refinement.md`'s "Persistent Refinement Backlog" section
— don't restate the rules here, just follow them.

**Read by:** the Master Prompt's Step 0/Step 2, whenever this file exists — an `OPEN`/`IN_PROGRESS`
entry is existing project work, not a new suggestion to independently rediscover.
**Written by:** any Continual Refinement round — every actionable finding gets an entry the same session
it's found, not only the findings that round implements.

---

## Backlog

[Append-only, ordered by ID. Never delete an entry — mark it `COMPLETED` or `DEFERRED` instead. Never
renumber.]

### RB-001 — Flaky notification-ordering test
- **Status:** COMPLETED
- **Dimension:** 6 (Testing/Reliability, per `docs/continual-refinement.md`'s Eight Dimensions)
- **Priority:** P3
- **Discovered:** Step 6 (Group_F08, Feature 08), 2026-09-04 — not a Continual Refinement round, but
  logged here per the same backlog mechanism since it surfaced mid-implementation and is out of scope
  for the group that found it.
- **Finding:** `backend/app/tests/test_router_notifications.py::test_list_notifications_returns_
  newest_first` fails intermittently (observed 2 failures in 5 reruns in isolation) — it asserts
  `GET /notifications` returns rows ordered by `created_at` descending, but two `Notification` rows
  created back-to-back in the same test can land on the same (or out-of-order) timestamp on this
  platform's clock resolution, making the assertion's expected order nondeterministic.
- **Rationale / Evidence:** Reproduced by re-running the single test in isolation 5 times (2 failed, 3
  passed) — unrelated to any Feature 08 change (Feature 08 touches no file this test or the
  `notifications` router depends on). Not a regression introduced this round; pre-existing since
  Feature 07 (`architecture-plan-feature-07.md`).
- **Routes to:** A scoped Step 6→7 re-entry against `backend/app/routers/notifications.py`'s query
  (add a stable tiebreaker, e.g. `ORDER BY created_at DESC, id DESC`, or the test fixture (assign
  strictly increasing timestamps to the two seeded notifications instead of relying on wall-clock
  ordering) — per `docs/continual-refinement.md`'s routing table for a contained, single-file
  correctness fix.
- **Implementation notes:** Fixed 2026-09-04, no Suggestion queued this session (Master Prompt Step 2
  routes an OPEN backlog entry ahead of idle-branch selection when no Suggestion is given). Chose the
  test-fixture option from the two named in this entry's "Routes to" (not the `ORDER BY ..., id DESC`
  DB tiebreaker) — `Notification.id` is a random UUID (`backend/app/models/notification.py`), so
  ordering by it would not actually produce a stable insertion-order tiebreak. Instead
  `backend/app/tests/test_router_notifications.py`'s `_seed_run_and_notifications` now assigns
  explicit, strictly increasing `created_at` timestamps (1s apart) to the two seeded notifications
  instead of relying on wall-clock ordering between two back-to-back commits. Verified: 5/5 isolated
  reruns passed (previously ~2/5 failed), full backend suite 111/111 passed (no regressions from the
  fixture change). No production code touched — `backend/app/routers/notifications.py`'s query is
  unchanged.

### RB-002 — Dead "Review Queue" nav item renders a blank page
- **Status:** COMPLETED
- **Dimension:** In-App Cohesion (`docs/in-app-cohesion.md`) / Feature Signaling
- **Priority:** P3
- **Discovered:** Step 7 (Implementation Verification), 2026-09-04, during the mandatory "can navigate
  all main routes" / "no obvious broken states" scan — not a Continual Refinement round, logged here
  per the same backlog mechanism as RB-001.
- **Finding:** `frontend/src/components/Layout.tsx`'s sidebar has always shipped a "Review Queue" nav
  item (`to: '/review'`) since Step 4's bootstrap scaffold. No route named `review` has ever been
  registered in `frontend/src/App.tsx` (only `leads` and `leads/:leadId`, added by Feature 08). Since
  the parent `<Routes>` has no matching child and no catch-all route, navigating to `/review` renders a
  completely blank page — not even the sidebar/Layout persists, no error message, no 404 state.
  Confirmed live via Playwright: `document.body.innerText` is empty string at that URL.
- **Rationale / Evidence:** Not a regression from any specific feature — `architecture-plan-
  feature-08.md`'s own Actual Footprint section already names this explicitly ("`Layout.tsx`'s 'Review
  Queue' nav item were deliberately left as-is (not in `owned_files`)"), and `.claude/pipeline-
  reference.md` has separately tracked the underlying gap since Feature 08 ("no feature anywhere in
  the 14-feature roadmap builds a frontend for the existing `GET /reviews`/`POST /reviews/{run_id}/
  action` routes"). Step 7 is the first verification pass to actually click the link and confirm the
  concrete failure mode (silent blank page, not merely "unbuilt"). The backend routes themselves work
  correctly — verified live this session: `GET /reviews`, `GET /reviews/{run_id}`, and `POST /reviews/
  {run_id}/action` (approve) all functioned correctly against a real queued review, resuming the run
  through `crm_write`/`notify` with one `PipelineRun` row and appended `StageTrace` rows, exactly as
  Feature 06's tests already assert.
- **Routes to:** A product decision, not something Step 7 should make unilaterally — either (a) a
  small, scoped Step 6-style fix removing the dead nav item until a real destination exists, or (b) a
  Scope Expansion / explicit Suggestion round to build a Review Queue frontend page against the
  already-working backend routes (this is the more valuable fix — the backend has supported this
  entire workflow since Feature 06). Surface at the next idle-session Dynamic Next-Action Selection
  (`docs/next-action-selection.md`) or the next In-App Cohesion Audit, whichever comes first.
- **Implementation notes:** Resolved 2026-09-05 via Continued Development (CD-1 through CD-4),
  option (b) from this entry's own "Routes to" — built the real frontend against the already-working
  backend rather than removing the nav link. Asked the user directly which option to take; "build the
  page" was chosen. Added as a new addendum feature, Feature 15 (Review Queue Frontend UI):
  `roadmap-addendum-2026-09-04.md` (CD-1), `implementation_plan.md`'s Feature 15 entry (CD-2),
  `architecture-plan-feature-15.md` (CD-2.5/CD-4 — see its Actual Footprint for full verification
  detail). Two new pages (`ReviewQueuePage.tsx`, `ReviewDetailPage.tsx`), three modified files
  (`api.ts`, `App.tsx`, `Layout.tsx` — nav `to` repointed from `/review` to `/reviews`), zero backend
  changes. Verified live against the real backend (all three reviewer actions, the 409
  already-actioned case, and the 404 not-found case) — not just component tests. As a side effect,
  this also makes Feature 07's existing `/reviews/{run_id}` notification `detail_link`s resolve to a
  real page for the first time.

### RB-003 — `.claude/portfolio-reference.md`'s Architecture Map was never backfilled for Features 02-08
- **Status:** COMPLETED
- **Dimension:** Documentation / Onboarding Accuracy (not one of `docs/continual-refinement.md`'s
  Eight Dimensions directly, but affects every future session's Step 0 orientation read)
- **Priority:** P3
- **Discovered:** Step 6 (Group_F09, Feature 09), 2026-09-04 — not a Continual Refinement round, but
  logged here per the same backlog mechanism as RB-001/RB-002 since it surfaced while adding Feature
  09's own rows and is out of scope for this group to fix.
- **Finding:** `.claude/portfolio-reference.md`'s Architecture Map table still has generic placeholder
  rows for `backend/app/models/`, `backend/app/schemas/`, `backend/app/routers/`,
  `frontend/src/pages/`, `frontend/src/lib/` (e.g. "populated in Step 6" / "added as their own Step 6
  groups land") even though Features 02 through 08 each landed real files in every one of those
  directories across 7 completed Step 6 groups (e.g. `routers/leads.py`, `routers/reviews.py`,
  `routers/notifications.py`, `models/pipeline_run.py`, `models/review_queue.py`,
  `models/notification.py`, `LeadListPage.tsx`, `LeadDetailPage.tsx`, `lib/api.ts`'s lead/review/
  notification helpers — none of these appear as their own row). Only Feature 09's rows (added this
  session) and the original Feature 01/03/04/05/06/07 orchestrator-stage rows (added at their own Step
  6 time) are present.
- **Rationale / Evidence:** Grep-confirmed: no occurrence of `leads.py`, `LeadListPage`,
  `LeadDetailPage`, `reviews.py`, `notifications.py`, `review_queue.py`, or `notification.py` (the
  model) anywhere in `.claude/portfolio-reference.md` prior to this session's edit. This doc is read
  first at Step 0 ("Read this before opening source files") — a future session orienting from it alone
  would not know these files exist without falling back to a full codebase scan, which is exactly what
  this doc exists to avoid.
- **Routes to:** A scoped documentation-only pass adding one row per missing file across Features
  02-08 (7 features' worth) — no code change, so it doesn't need a fresh Step 5.5 plan. Could be done
  as part of a future Continual Refinement round (Documentation dimension) or picked up directly as a
  Suggestion, whichever comes first.
- **Implementation notes:** Resolved 2026-09-05 — picked up per the Master Prompt's Step 2 routing
  (no Suggestion given this session, backlog had an OPEN entry). Added the 7 missing rows to
  `.claude/portfolio-reference.md`'s Architecture Map: `backend/app/routers/leads.py`,
  `frontend/src/pages/LeadListPage.tsx`, `frontend/src/pages/LeadDetailPage.tsx`,
  `frontend/src/pages/HomePage.tsx`, `frontend/src/lib/api.ts`, `frontend/src/lib/stageOrder.ts`, and
  the two previously-uncited migrations (`9217c457cc82`, `b86e4d4ef367`) folded into the existing
  alembic row. Also rewrote the three stale directory-level placeholder rows
  (`frontend/src/components/`, `frontend/src/pages/`, `frontend/src/lib/`) from future-tense
  ("added as their own Step 6 groups land") to present-tense, since all cited groups have already
  landed. Cross-checked every row against the actual filesystem (`ls` on `routers/`, `models/`,
  `schemas/`, `pages/`, `components/`, `lib/`, `alembic/versions/`), not just the finding's own list —
  no other gaps found. **New finding surfaced while verifying:** `frontend/src/pages/HomePage.tsx`
  (the "/" index route, per `App.tsx`) still shows its Step-4-bootstrap placeholder text
  ("Observability view — implemented in Step 6 (Feature 08)") with no link, even though Feature 08's
  real observability view landed at `/leads`, not "/" — logged separately as RB-004 rather than fixed
  here, since this ticket's own scope is documentation-only.

### RB-004 — Index route ("/") shows a stale Step-4 bootstrap placeholder, not a real landing page
- **Status:** COMPLETED
- **Dimension:** In-App Cohesion (`docs/in-app-cohesion.md`) / Feature Signaling
- **Priority:** P3
- **Discovered:** RB-003's documentation backfill pass, 2026-09-05 — while cross-checking
  `frontend/src/pages/` against `App.tsx`'s actual routes, not a Continual Refinement round; logged
  here per the same backlog mechanism as RB-001/002/003.
- **Finding:** `frontend/src/pages/HomePage.tsx` (bound to the index route `/` in `App.tsx`) still
  reads exactly as Step 4's bootstrap scaffold left it: `"Observability view — implemented in Step 6
  (Feature 08)."`, with no link anywhere on the page. Feature 08's real observability view was built
  at `/leads` (`LeadListPage.tsx`), not at `/` — `HomePage.tsx` was never updated to either redirect
  there or link to it. The persistent sidebar (`Layout.tsx`) does provide a working "Leads"/
  "Observability" nav link, so this is not a true dead end the way RB-002's blank `/review` page was —
  but the landing page itself is a stale, self-referential placeholder a first-time visitor or client
  demo would see before clicking anywhere.
- **Rationale / Evidence:** Confirmed via `App.tsx` (`<Route index element={<HomePage />} />` at line
  15, `<Route path="leads" element={<LeadListPage />} />` at line 16) and `HomePage.tsx`'s full
  contents (6 lines, unchanged since bootstrap — no feature's `architecture-plan-*.md` Actual Footprint
  section lists `HomePage.tsx` as a modified file).
- **Routes to:** A small, contained fix — either (a) redirect `/` to `/leads` (`<Navigate to="leads"
  replace />`), or (b) rewrite `HomePage.tsx`'s copy into a real landing summary with a link to
  `/leads`. Per `docs/continual-refinement.md`'s routing table this is a contained, single-file
  UI-copy/routing fix scoped small enough for a direct Step 6-style edit — doesn't need a fresh Step
  5.5 plan. Surface at the next idle-session Dynamic Next-Action Selection or the next In-App Cohesion
  Audit, whichever comes first, per the same pattern RB-002 used.
- **Implementation notes:** Resolved 2026-09-05 — picked up directly following RB-003 in the same
  session (no Suggestion given; this was the only remaining OPEN backlog entry). Chose option (b) from
  this entry's own "Routes to" (rewrite `HomePage.tsx`'s copy) over option (a) (a bare redirect to
  `/leads`) — a redirect would have hidden `/reviews` and `/benchmark` behind the sidebar with no
  landing-page signal that they exist, which is the same "reachability" concern
  `docs/in-app-cohesion.md` is meant to catch. `frontend/src/pages/HomePage.tsx` now renders a title,
  one-line product summary, and three linked cards (Observability → `/leads`, Review Queue →
  `/reviews`, Benchmark → `/benchmark`), styled consistent with `BenchmarkPage.tsx`'s existing
  `rounded-lg border border-slate-200 bg-white p-4` card convention and `Layout.tsx`'s teal-700 accent.
  Verified: `npm run build` (`tsc -b && vite build`) passed clean, no type errors. No existing test
  file covered `HomePage.tsx` (`BenchmarkPage.test.tsx`/`LeadListPage.test.tsx`/
  `ReviewDetailPage.test.tsx`/`ReviewQueuePage.test.tsx` exist, no `HomePage.test.tsx`), so none needed
  updating. No backend or routing changes — `App.tsx`'s `<Route index element={<HomePage />} />` is
  unchanged, only the component's rendered content changed. **New finding surfaced by this fix, not
  caught at the time:** `src/App.test.tsx`'s only test still asserts the old placeholder text
  (`/Observability view/i`) on the home route, so RB-004's own fix broke it — logged separately as
  RB-005 rather than fixed here, since `App.test.tsx` was outside RB-004's own scope/owned files.

### RB-005 — `App.test.tsx` asserts stale HomePage placeholder text, fails since RB-004
- **Status:** COMPLETED
- **Dimension:** 6 (Testing/Reliability, per `docs/continual-refinement.md`'s Eight Dimensions)
- **Priority:** P3
- **Discovered:** Step 6 (Group_F11, Feature 11), 2026-09-05 — not a Continual Refinement round, but
  logged here per the same backlog mechanism as RB-001/002/003/004, since it surfaced while running the
  full frontend test suite for Feature 11 and is out of scope for Group_F11's `owned_files`.
- **Finding:** `frontend/src/App.test.tsx`'s only test, `renders the observability placeholder on the
  home route`, asserts `screen.getByText(/Observability view/i)` on the `/` route. RB-004 (2026-09-05,
  same day, earlier session) rewrote `HomePage.tsx`'s content away from that exact placeholder string as
  part of its own fix, but never updated this test to match — the test's own name still describes the
  behavior RB-004 deliberately removed.
- **Rationale / Evidence:** Confirmed via `git stash` (isolating this session's Feature 11 changes) and
  re-running `npm test -- --run src/App.test.tsx` against the unmodified working tree: same failure,
  proving this predates Feature 11 and is unrelated to it. `App.test.tsx` is not in Group_F11's
  `owned_files` (`implementation_plan.md`), so this session did not fix it in place.
- **Routes to:** A contained, single-file test-fixture fix — update `App.test.tsx`'s assertion (and
  ideally its test name) to match `HomePage.tsx`'s current real landing-page copy from RB-004 (title,
  summary, and the three linked cards). Per `docs/continual-refinement.md`'s routing table this is a
  contained correctness fix, the same class of fix RB-001 used — doesn't need a fresh Step 5.5 plan.
- **Implementation notes:** Resolved 2026-09-05 — picked up per the Master Prompt's Step 2 routing
  (no Suggestion given this session, backlog had exactly one OPEN entry). Verified the finding first
  per the v18.0 verify-before-committing check: re-read `App.test.tsx` and `HomePage.tsx`, then
  reproduced the failure directly (`npm test -- --run src/App.test.tsx`) before touching anything.
  Rewrote the test to assert against `HomePage.tsx`'s actual current content (title heading plus the
  three linked cards to `/leads`, `/reviews`, `/benchmark`) instead of the removed placeholder string,
  and renamed it to describe that behavior. Two disambiguation issues surfaced while fixing, both
  resolved by scoping queries to the `<main>` region via `within()`: `Layout.tsx`'s sidebar renders the
  same "Lead Intake Triage" text (as a `div`, not a heading — fixed by asserting `getByRole('heading',
  ...)`) and the same three nav labels ("Observability", "Review Queue", "Benchmark") as `NavLink`s
  (fixed by scoping all queries to `within(screen.getByRole('main'))` so only `HomePage.tsx`'s cards are
  matched). Verified: full frontend suite 15/15 passed (previously 14/15, App.test.tsx failing); full
  backend suite unaffected at 136/136 (this was a frontend-only test fixture change, no production code
  touched).

### RB-006 — `LeadDetailPage.tsx` (the project's own named differentiator page) had zero dedicated tests
- **Status:** COMPLETED
- **Dimension:** 4 (Test Coverage, per `docs/continual-refinement.md`'s Eight Dimensions)
- **Priority:** P1
- **Discovered:** Continual Project Refinement, Round 1, 2026-09-05 — the first time any coverage tool
  has ever been run on this project (every prior Step 7/9 validation entry recorded "no coverage tool
  configured" rather than a number).
- **Finding:** After installing `pytest-cov`/`@vitest/coverage-v8` and running both suites with coverage
  for the first time, `LeadDetailPage.tsx` measured 5.55% statement coverage with zero uncovered-code
  ambiguity — it has no `LeadDetailPage.test.tsx` at all (confirmed via `ls pages/*.test.tsx`), unlike
  every sibling page. This is the exact page `portfolio-description.md`'s Screenshot Description names
  as "the project's core differentiator" (full per-stage observability into the pipeline's decisions).
- **Rationale / Evidence:** `npx vitest run --coverage` output: `LeadDetailPage.tsx` 5.55%/0%/0%/6.52%
  (stmts/branch/funcs/lines) vs. every other page's test file existing and scoring 68-95%. Backend
  coverage was a healthy 98% by contrast (`pytest --cov=app`), so this was specifically a frontend gap,
  not a project-wide testing culture problem.
- **Routes to:** Scoped re-entry to Step 6 (add tests for the untested surface) → Step 7 (verify) — per
  the Routing Table's Dimension 4 row.
- **Implementation notes:** Fixed same round. Added `frontend/src/pages/LeadDetailPage.test.tsx` (6
  tests: full stage-trace timeline render, failed-pipeline banner, in-progress banner, 404 not-found
  state, generic error state, recent-activity panel + link to the full history page). Verified: frontend
  suite 24/24 passing (was 18/18), `LeadDetailPage.tsx` coverage 5.55% → 90.74% statements, project-wide
  frontend statement coverage 70.64% → 81.65%. `tsc -b`, `vite build`, and `oxlint` all re-confirmed
  clean (same 5 pre-existing `set-state-in-effect` warnings, no new ones — see RB-009). No production
  code touched. `README.md`/`portfolio-description.md`/`linkedin-entry.md` test counts updated
  156 → 162 (138 backend + 24 frontend) to stay accurate, per Dimension 8's own cross-document
  discipline.

### RB-007 — N+1 query in `GET /leads/{lead_id}/history` (one `StageTrace` query per pipeline run)
- **Status:** COMPLETED
- **Dimension:** 6 (Performance, per `docs/continual-refinement.md`'s Eight Dimensions)
- **Priority:** P2
- **Discovered:** Continual Project Refinement, Round 1, 2026-09-05 — a reviewer-level skim of
  `backend/app/routers/leads.py` for the "obvious N+1 queries" this dimension names explicitly.
- **Finding:** The merged-history endpoint (`GET /leads/{lead_id}/history`, the one README calls out as
  merging "history across every pipeline run and human review action for that lead") ran one query for
  the lead's `PipelineRun` rows, then a separate `StageTrace` query inside a `for run_row in run_rows:`
  loop — one extra round-trip per run instead of a single batched query.
- **Rationale / Evidence:** `backend/app/routers/leads.py`, the merged-history handler, lines ~242-256
  (pre-fix): `for run_row in run_rows: db.query(StageTrace).filter(StageTrace.run_id == run_row.id)...`.
  Low real-world impact at this project's actual scale (SQLite, single local user, small per-lead run
  counts), but a textbook N+1 a senior engineer reviewing the code would flag immediately.
- **Routes to:** Scoped re-entry to Step 6 (implement the fix) → Step 7 (verify no regression) — per the
  Routing Table's Dimension 6 row.
- **Implementation notes:** Fixed same round. Replaced the per-run query with one batched
  `db.query(StageTrace).filter(StageTrace.run_id.in_(run_ids))` query, then grouped results by
  `run_id` in Python before the existing per-run iteration (ordering preserved — the batched query is
  already sorted by `created_at`, so grouping a sorted sequence keeps each run's own trace order intact).
  Verified: full backend suite 138/138 passing, no regressions.

### RB-008 — Residual frontend coverage gaps below RB-006's severity (api client layer, list page, 404 page)
- **Status:** COMPLETED
- **Dimension:** 4 (Test Coverage)
- **Priority:** P3
- **Discovered:** Continual Project Refinement, Round 1, 2026-09-05 — same coverage run that found
  RB-006.
- **Finding:** After RB-006's fix, three files remain under-covered: `frontend/src/lib/api.ts` (21%
  statements — the typed API client is exercised indirectly through every page's mocked tests, but has
  no direct unit test of its own request/response shaping), `LeadListPage.tsx` (71%, mainly untested
  filter/sort/pagination branches), and `NotFoundPage.tsx` (0%, a trivial one-line component).
- **Rationale / Evidence:** `npx vitest run --coverage` output, post-RB-006-fix. None of these are the
  project's flagship/differentiator surface the way `LeadDetailPage.tsx` was — this is routine
  incremental coverage debt, not a standout gap, which is why it's logged as P3 rather than batched into
  this round's P1/P2 work (`docs/continual-refinement.md`'s Loop Mechanics: "don't try to close every
  dimension's gaps in one session").
- **Routes to:** Scoped re-entry to Step 6 (add tests for the named files) → Step 7 (verify) — per the
  Routing Table's Dimension 4 row.
- **Implementation notes:** Resolved 2026-09-05 — picked up per the Master Prompt's Step 2 routing (no
  Suggestion given this session, backlog had two OPEN entries; chose this one over RB-009 as the
  higher-priority Test Coverage gap vs. a cosmetic lint nit). Verified the finding first per the v18.0
  check: re-ran `npx vitest run --coverage`, confirmed the same three files still at 21%/71%/0%.
  Added `frontend/src/lib/api.test.ts` (9 tests, one per exported API function, spying on the underlying
  `api.get`/`api.post` axios methods directly rather than the exported wrapper — the existing page tests
  all mock the wrapper functions themselves, which never exercises the real function bodies).
  Added `frontend/src/pages/NotFoundPage.test.tsx` (1 test). Expanded
  `frontend/src/pages/LeadListPage.test.tsx` from 2 to 8 tests, adding coverage for the error state, the
  summary-count failure path, and all three filter/sort selects plus pagination Previous/Next (the
  interactive branches `vi.spyOn` on the wrapper function had never exercised). Verified: frontend suite
  41/41 passing (was 24/24) — 17 new tests. Coverage: `api.ts` 21%→100% stmts, `LeadListPage.tsx`
  71%→97% stmts, `NotFoundPage.tsx` 0%→100% stmts; project-wide frontend statement coverage 81.65%→
  88.53%. `tsc -b`, `vite build` (337.92 kB, unchanged — test-only change), and `oxlint` all re-confirmed
  clean (same 5 pre-existing `set-state-in-effect` warnings, no new ones — see RB-009, still OPEN).
  Backend suite re-run unaffected at 138/138 (no backend files touched). `README.md`/
  `portfolio-description.md`/`linkedin-entry.md` test counts updated 162 → 179 (138 backend + 41
  frontend) and frontend coverage 82%→89%, per Dimension 8's cross-document discipline.

### RB-009 — Pre-existing `react(set-state-in-effect)` lint warning in 5 pages (Low)
- **Status:** OPEN
- **Dimension:** 3 (Architecture & Code Quality)
- **Priority:** P3
- **Discovered:** Step 9 (Unified QA & Repair), 2026-09-04 (`qa-report.md`'s Remaining Issues #2) — not
  originally a Continual Refinement finding, but that issue's own "Recommended action" named "a future
  Continual Refinement round, Testing/Reliability or code-quality dimension" as where to pick it up, so
  it's logged here now that this project has run one for the first time, rather than re-discovering it
  from scratch.
- **Finding:** `LeadDetailPage.tsx`, `LeadHistoryPage.tsx`, `LeadListPage.tsx`, `ReviewDetailPage.tsx`,
  and `ReviewQueuePage.tsx` each call `setLoading(true)`/similar synchronously inside their data-fetch
  `useEffect` — a standard fetch pattern that `oxlint`'s `react(set-state-in-effect)` rule flags as a
  style nit, not a functional defect.
- **Rationale / Evidence:** `npm run lint` output, re-confirmed this round (same 5 files, same warnings,
  no new ones — no drift since Step 9's original finding).
- **Routes to:** Scoped re-entry to Step 6 (refactor the fetch pattern across the 5 named files) →
  Step 7 (verify) — per the Routing Table's Dimension 3 row.
- **Implementation notes:** (blank — not yet started; low priority, no functional impact, deliberately
  not batched into this round's P1/P2 work.)
