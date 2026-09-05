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
- **Status:** OPEN
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
- **Implementation notes:** _(pending)_
