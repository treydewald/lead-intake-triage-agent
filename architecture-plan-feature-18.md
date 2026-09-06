IMPLEMENTATION PLAN
====================

Feature / Round: Feature 18 (Aggregate Lead Funnel & Reviewer Throughput Dashboard)
Classification: New feature, Cross-system integration (aggregates across `PipelineRun` and
`ReviewQueueItem`, two systems no existing endpoint reads jointly)
Planning Depth: Standard — touches 2-3 existing systems (`PipelineRun`, `ReviewQueueItem`, and
`Layout.tsx`/`HomePage.tsx`'s navigation surface) plus one new page; no new data model, no new
external integration, no architecture change.

Objective
Give a sales-manager persona (`project-definition.md` Use Case 4) a single view answering "how is
the whole pipeline performing across every lead," computed entirely from `PipelineRun`/
`ReviewQueueItem` rows the project already persists — a distinct question from every existing page's
per-lead or point-in-time-accuracy framing.

Existing Systems Analysis
- Reusable: `PipelineRun.status`/`.source_channel`/`.confidence_score`/`.created_at`/`.updated_at`
  (Feature 08's denormalized columns, already indexed for list/filter use — this feature is a second,
  purely additive consumer of the same columns, not a new derivation path).
  `ReviewQueueItem.status`/`.reviewer_name`/`.created_at`/`.actioned_at` (Feature 06/11) — throughput
  is a direct read of fields that already exist for the review workflow's own purposes.
  `display_status_for()` (`backend/app/schemas/pipeline.py`) — the existing `PipelineRun.status` →
  display-status mapping every other read view already uses; this feature's `by_status` breakdown
  must use the exact same mapping, not a third, independently-invented status vocabulary. The
  existing `ui/` component kit (`PageHeader`/`StatCard`/`Card`/`SectionLabel`/`EmptyState`) — every
  other page already builds its layout from these, this page does the same, no new shared component
  needed. `HomePage.tsx`'s existing `sections` array + card-grid pattern (RB-004) — the fourth card
  this feature adds follows that exact existing shape, not a new card style.
- Duplication Risk Flagged: **does an existing endpoint already compute any of this?** `GET /leads`
  supports filtering/sorting but never aggregates (returns rows, not counts); `GET /reviews` lists
  `PENDING` items only, never actioned ones, and computes no throughput. No existing endpoint groups
  by status, channel, or reviewer, or computes an average duration. No duplication found — this is
  genuinely new aggregation, not a restatement of an existing read path.
- Modify: `backend/main.py` (register one new router); `frontend/src/App.tsx` (one new route);
  `frontend/src/components/Layout.tsx` (one new nav item); `frontend/src/pages/HomePage.tsx` (one
  new section card).
- New: `backend/app/routers/analytics.py`, `backend/app/schemas/analytics.py` — a new router/schema
  pair is justified here (unlike, say, adding a route to `leads.py`) because this feature's data
  spans two existing routers' domains (`PipelineRun` from `leads.py`'s area, `ReviewQueueItem` from
  `reviews.py`'s area) and answers a genuinely different kind of question (aggregate, not per-entity)
  than either existing router does — forcing it into one of the two existing routers would make that
  router responsible for a domain it doesn't own. `frontend/src/pages/FunnelDashboardPage.tsx` — new
  page, justified the same way (Existing Systems Analysis above found no page or panel that already
  answers this cross-lead question).
- Navigation Relationships Flagged: **this page earns a persistent `Layout.tsx` nav entry**, unlike
  `LeadHistoryPage.tsx`/`ReviewDetailPage.tsx` (both reached only via a link from a parent page) —
  those two are *drill-down* views of something else; this page is a *standalone* destination a
  sales-manager persona navigates to directly, the same reachability class as `/leads`, `/reviews`,
  and `/benchmark`. Also flagged: `HomePage.tsx`'s existing three-card section grid should gain a
  fourth card for this page, per the same in-app-cohesion pattern RB-004 established (every top-level
  destination gets both a nav entry and a HomePage card) — see `docs/in-app-cohesion.md` §2/§5. No
  reverse link is needed (this page doesn't reference one specific lead/run/review a user would want
  to jump to; it's already the "zoomed out" view).

System Impact Map

FEATURE 18 — Aggregate Lead Funnel & Reviewer Throughput Dashboard
│
├── Frontend
│   ├── `pages/FunnelDashboardPage.tsx` — new page (stat tiles + two tables)
│   ├── `lib/api.ts` — new `getFunnelDashboard()` + response types
│   ├── `App.tsx` — new `/analytics` route
│   ├── `components/Layout.tsx` — new "Analytics" nav item
│   ├── `pages/HomePage.tsx` — new fourth section card
│
├── Backend
│   ├── `app/routers/analytics.py` — new `GET /analytics/funnel`
│   ├── `app/schemas/analytics.py` — new `FunnelDashboardOut` + nested shapes
│   ├── `main.py` — register the new router
│
├── Database
│   ├── none added
│
├── Existing Systems (reused, not duplicated)
│   ├── `PipelineRun`'s denormalized `source_channel`/`confidence_score` columns (Feature 08)
│   ├── `display_status_for()` (Feature 08's status-mapping convention)
│   ├── `ReviewQueueItem.reviewer_name`/`.actioned_at` (Features 06/11)
│   ├── `ui/` component kit — `PageHeader`/`StatCard`/`Card`/`SectionLabel`/`EmptyState`
│   ├── `HomePage.tsx`'s existing card-grid pattern
│
├── Navigation
│   ├── `Layout.tsx` gains a persistent "Analytics" nav entry → `/analytics`
│   ├── `HomePage.tsx` gains a fourth section card → `/analytics`
│
└── AI
    └── N/A — no AI integration; pure aggregation over already-computed pipeline outcomes

Implementation Order (Dependency Graph)

`PipelineRun`/`ReviewQueueItem` (existing) → `FunnelDashboardOut` schema (new)
  → `GET /analytics/funnel` (new; depends on the schema)
  → `getFunnelDashboard()` in `api.ts` (new; depends on the route existing)
  → `FunnelDashboardPage.tsx` (new; depends on the above)
  → nav/route/HomePage wiring (depends on the page existing)

1. **`FunnelDashboardOut` + nested schemas** (`schemas/analytics.py`) — purpose: define the response
   shape before the route that returns it. Existing files affected: none. New files:
   `schemas/analytics.py`. Dependencies: none. Requirements: `FunnelStatusCountOut{status,count}`,
   `FunnelChannelStatOut{source_channel,count,avg_confidence}`,
   `ReviewerThroughputOut{reviewer_name,actioned_count,avg_resolution_seconds}`,
   `FunnelDashboardOut{total_leads,by_status,by_source_channel,avg_resolution_seconds,
   reviewer_throughput}`. Validation: covered by step 2's endpoint test (response-model validation).

2. **`GET /analytics/funnel`** (`routers/analytics.py`) — purpose: compute and return every
   aggregate. Existing files affected: `main.py` (router registration). New files:
   `routers/analytics.py`, `tests/test_router_analytics.py`. Dependencies: step 1;
   `display_status_for()` (existing, `schemas/pipeline.py`). Requirements: query all `PipelineRun`
   rows once, group in Python by `display_status_for(status)` for `by_status` and by
   `source_channel or "unknown"` for `by_source_channel` (count + average of non-null
   `confidence_score`); compute `avg_resolution_seconds` over rows whose raw `status` is in
   `{COMPLETED, FAILED, REJECTED}` as `(updated_at - created_at).total_seconds()`, averaged, `None`
   if the filtered set is empty; query all `ReviewQueueItem` rows once, filter to `status ==
   "ACTIONED"`, group by `reviewer_name or "Unattributed"` for `actioned_count` and average
   `(actioned_at - created_at).total_seconds()` per group. Validation: seed rows covering every
   status/channel/reviewer edge case named in the feature spec; assert every returned number by hand
   against the seeded data.

3. **`getFunnelDashboard()`** (`api.ts`) — purpose: thin GET wrapper, same shape as every other
   `api.ts` function. Existing files affected: `api.ts`. New files: none. Dependencies: step 2.
   Requirements: typed response matching `FunnelDashboardOut` exactly (snake_case fields, matching
   this project's existing convention of not re-casing backend field names in the frontend).

4. **`FunnelDashboardPage.tsx`** — purpose: user-facing entry point. Existing files affected: none.
   New files: `FunnelDashboardPage.tsx`, `FunnelDashboardPage.test.tsx`. Dependencies: step 3.
   Requirements: `PageHeader` + a 2-3-tile `StatCard` row (total leads, avg resolution time formatted
   as human-readable duration, awaiting-review count pulled from `by_status`); a `by_source_channel`
   table (channel, count, avg confidence via the existing `ConfidenceMeter` component); a
   `reviewer_throughput` table (reviewer, actioned count, avg time-to-action formatted the same way
   as the top-level average); `EmptyState` for zero leads; a separate, narrower empty message inside
   the reviewer table specifically when `reviewer_throughput` is empty but leads exist. Validation:
   component test with a mocked full response, plus a second test asserting both empty-state paths
   render correctly.

5. **Nav/route/HomePage wiring** (`App.tsx`, `Layout.tsx`, `HomePage.tsx`) — purpose: make the page
   reachable per the Navigation Relationships flagged above. Existing files affected: all three.
   New files: none. Dependencies: step 4. Requirements: `/analytics` route in `App.tsx`; a nav item
   in `Layout.tsx`'s `navItems` array (icon: `BarChart3` from `lucide-react`, label "Analytics");
   a fourth entry in `HomePage.tsx`'s `sections` array. Validation: existing `App.test.tsx`/
   `HomePage.test.tsx` navigation-region assertions (scoped via `within(screen.getByRole('main'))`,
   per RB-005's established pattern) extended to include the new item, so a broken link is a test
   failure, not a silent gap.

Architecture Rule Changes
- [ ] None proposed. This feature introduces a new router/schema pair for a genuinely new
  aggregation domain, which is an application of the existing "one router per domain" convention
  this project already follows (`leads.py`, `reviews.py`, `notifications.py`, `benchmark.py`), not a
  new rule. Conflict check: none found — no existing Key Decision addresses cross-entity aggregation
  or when a new page earns a persistent nav entry (this plan states that judgment inline in Navigation
  Relationships Flagged above, as a feature-specific decision, not a generalized rule other features
  must follow — the "does this page answer a standalone question vs. drill down from a parent" test
  is a normal in-app-cohesion judgment call, not a durable rule that changes future planning).

Feature-Specific Requirements
- Duration values (`avg_resolution_seconds` and the reviewer-throughput equivalent) are formatted
  client-side into a human-readable string (e.g. "4m 12s", "1h 03m") — this formatting lives in
  `FunnelDashboardPage.tsx` alone, not promoted to a shared utility, since no other page currently
  displays a duration; if a second page ever needs the same formatting, that repetition is the
  trigger to extract it, not before.
- Icon choice for the new nav item (`BarChart3`) follows the existing `lucide-react` convention
  already used by every other nav item (`Activity`, `ClipboardCheck`, `Gauge`).

Risks
- Risk: computing aggregates in Python (not SQL `GROUP BY`) becomes a real performance concern if
  the lead volume ever grows large. Mitigation: this project's existing scale reasoning already
  accepts Python-side computation for read endpoints with "no realistic volume concern" (see
  `.claude/portfolio-reference.md`'s `message_body` projection Key Decision) — a local-dev/portfolio-
  scale dataset is the explicit target; revisit with a real `GROUP BY` query if a future round's data
  shows this assumption no longer holds.
- Risk: adding a fourth `HomePage.tsx` section card or a fourth `Layout.tsx` nav item regresses the
  no-scroll constraint (`docs/ui-design-standards.md` §1) those pages have already passed. Mitigation:
  `HomePage.tsx`'s section grid is already responsive (`grid-cols-1 sm:grid-cols-3`) and adding a
  fourth item only requires it to reflow, not grow taller at desktop widths where 4 items still fit a
  wider grid; `Layout.tsx`'s nav list is a vertical flex column with room for more entries. CD-4/CD-5
  re-verifies via the existing Playwright no-scroll script rather than assuming this holds.
- Risk: `FunnelDashboardPage.tsx`'s own visual layout (new page, never screenshot-verified) ships
  without real browser confirmation. Mitigation: unlike Feature 17's session, this session has
  confirmed working browser automation (`playwright-core` + local Chromium) — CD-4 must actually use
  it for this new page rather than defaulting to `UNVERIFIED`.

Acceptance Criteria
- [ ] All acceptance criteria already stated in `implementation_plan.md`'s Feature 18 spec
- [ ] `by_status` counts, summed, equal `total_leads` exactly (every `PipelineRun` row falls into
  exactly one status bucket — cross-checked by a dedicated test, not just eyeballed)
- [ ] The new nav item and HomePage card are confirmed to actually navigate to `/analytics` and
  render real data, verified live against a running backend with real seeded data, not only against
  mocks

Validation Requirements
- CD-4 must confirm `avg_resolution_seconds`/reviewer averages against a hand-computed expectation
  from real (not mocked) seeded data, not just "the endpoint returns 200"
- CD-4 must use real browser automation (confirmed available this session) to visually verify
  `FunnelDashboardPage.tsx` at desktop and mobile viewports against the no-scroll constraint, closing
  the same category of gap Feature 17 left `UNVERIFIED`

Predicted Footprint
Files predicted to change: 10 (`routers/analytics.py`, `schemas/analytics.py`,
`tests/test_router_analytics.py`, `main.py`, `lib/api.ts`, `pages/FunnelDashboardPage.tsx`,
`pages/FunnelDashboardPage.test.tsx`, `App.tsx`, `components/Layout.tsx`, `pages/HomePage.tsx`, plus
this plan's own Actual Footprint appendix, plus possibly `App.test.tsx`/`HomePage.test.tsx` if their
existing nav-region assertions need extending)
Systems predicted to touch: new analytics router/schema, PipelineRun/ReviewQueueItem read paths,
frontend routing/nav/HomePage

--- filled in later, by Step 7 / CD-4, once implementation is verified ---
Actual Footprint
Files actually changed: 9 — one fewer than predicted: `backend/app/routers/analytics.py`,
`backend/app/schemas/analytics.py`, `backend/app/tests/test_router_analytics.py`, `backend/main.py`,
`frontend/src/lib/api.ts`, `frontend/src/pages/FunnelDashboardPage.tsx`,
`frontend/src/pages/FunnelDashboardPage.test.tsx`, `frontend/src/App.tsx`,
`frontend/src/components/Layout.tsx`, `frontend/src/pages/HomePage.tsx`, plus this plan's own Actual
Footprint appendix. `App.test.tsx`'s existing nav-region assertion needed one line added (predicted);
`HomePage.test.tsx` did not need touching because no such file exists (this project has never had a
dedicated HomePage test, per RB-004's own note — the nav/card assertions live in `App.test.tsx`
instead, which was already accounted for).
Deviations from plan: none of substance. `GET /analytics/funnel`'s reviewer-throughput loop was
initially written with an O(reviewers) nested re-query of `ReviewQueueItem` inside the list
comprehension (an actual N+1-shaped bug caught before committing, not shipped) — fixed to a single
pass building both the count and duration-list dictionaries together, before any test ran against it.
Rework required: none beyond that pre-commit self-catch. Full backend suite (154/154) and frontend
suite (60/60) passed; `tsc -b`, `vite build` (338.09 kB → 347.79 kB, +2.9%, under the 15% material
threshold), and `oxlint` all clean. Backend coverage held at 98% (unchanged); frontend statement
coverage 89.03% → 88.86% (−0.17 points, well under the 5-point material-regression threshold).
Live-verified against the real accumulated dev database (33 real `PipelineRun` rows, 8 real
`ReviewQueueItem` actions across 4 real reviewer names) via a running backend — `by_status` counts
summed to exactly `total_leads` (1+29+3=33), `by_source_channel` correctly bucketed a real `None`
source_channel row under "unknown", and reviewer throughput correctly separated 4 distinct reviewers
including "Unattributed". Visually verified with real Playwright/Chromium (confirmed available this
session, unlike Feature 17's session) at all four target viewports (1920×1080, 1440×900, 1366×768,
390×844): zero horizontal/vertical overflow on `/analytics` at every viewport, and a live click-through
from `HomePage.tsx`'s new fourth card to `/analytics` confirmed working — closing the same category of
`UNVERIFIED` gap Feature 17 left open, per this plan's own Risks section.
