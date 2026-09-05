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
- **Status:** OPEN
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
- **Implementation notes:** [pending]
