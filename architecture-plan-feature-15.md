IMPLEMENTATION PLAN
====================

Feature / Round: Feature 15 (Review Queue Frontend UI) — Continued Development round, CD-2.5
Classification: New frontend surface (2 pages, 2 routes) consuming existing, unmodified backend
Planning Depth: Standard — a genuinely new UI surface with real state/error handling (not a one-line
tweak), but zero new backend systems and every conventions/pattern it needs already exists in Features
08/09; no Deep-tier architectural risk.

Objective
Give reviewers a real UI for Feature 06's already-working `/reviews` backend, closing the gap RB-002
found (dead "Review Queue" nav link, blank page) by adding a list page and a detail/action page that
consume the existing endpoints exactly as they are, with zero backend changes.

Existing Systems Analysis
- Reusable: `frontend/src/lib/api.ts`'s `axios` instance and typed-function pattern (`listLeads`/
  `getLeadDetail`, `runBenchmark`/`listBenchmarkRuns`) — new functions follow the identical shape.
  `LeadListPage.tsx`'s fetch/loading/error/empty-state pattern for the list page. `LeadDetailPage.tsx`'s
  fetch/loading/404/error pattern for the detail page. `Layout.tsx`'s existing nav-item array (only the
  `to` value changes). `App.tsx`'s existing `<Route>` registration pattern. The backend itself
  (`backend/app/routers/reviews.py`, `backend/app/schemas/review.py`) — already correct, already
  tested by Feature 06's own suite, confirmed live by Step 7 — needs literally zero changes.
- Duplication Risk Flagged: none found — no existing frontend file already renders review-queue data;
  the only prior artifact was the dead nav link itself, which this feature repoints rather than
  duplicates.
- Modify: `frontend/src/lib/api.ts` (add types/functions), `frontend/src/App.tsx` (add 2 routes),
  `frontend/src/components/Layout.tsx` (repoint one nav item's `to`).
- New: `frontend/src/pages/ReviewQueuePage.tsx`, `frontend/src/pages/ReviewDetailPage.tsx`, and their
  `.test.tsx` files. Nothing else is genuinely new — this is conventions-reuse, not new architecture.
- Navigation Relationships Flagged (docs/in-app-cohesion.md §5): Feature 07's `Notification.
  detail_link` already emits `/reviews/{run_id}` for `awaiting_review`/`rejected` outcomes (Key
  Decision, portfolio-reference.md) — this feature's detail route MUST be `reviews/:runId` (matching
  exactly) so those existing notification links start resolving correctly for the first time, not a
  new cohesion gap to fix later. No reverse link is needed from the detail page back to a specific
  lead's `LeadDetailPage` in this round (the review item's `lead_id` is shown as text; a live link is a
  nice-to-have, not an acceptance criterion — noted under Risks, not blocking).

System Impact Map
frontend/src/
├── lib/api.ts                          [MODIFY — add types + 3 functions]
├── App.tsx                             [MODIFY — add 2 routes]
├── components/Layout.tsx               [MODIFY — repoint 1 nav `to`]
└── pages/
    ├── ReviewQueuePage.tsx             [NEW]
    ├── ReviewQueuePage.test.tsx        [NEW]
    ├── ReviewDetailPage.tsx            [NEW]
    └── ReviewDetailPage.test.tsx       [NEW]
(No backend/ files touched.)

Implementation Order (Dependency Graph)
1. `api.ts` additions | typed client for the 3 existing endpoints | modifies `lib/api.ts` | none new |
   depends on: nothing | requirements: types match `backend/app/schemas/review.py` exactly
   (`ReviewQueueItemOut`, `ReviewActionRequest`) plus `PipelineRunOut`'s shape for the action response |
   validation: TypeScript compiles, shapes match a manual curl/response inspection of the live backend
2. `ReviewQueuePage.tsx` + test | PENDING-items list | new file | depends on: step 1 | requirements:
   mirrors `LeadListPage.tsx`'s loading/error/empty pattern, links each row to
   `/reviews/{run_id}` | validation: component test (mocked API) + manual render
3. `ReviewDetailPage.tsx` + test | per-item detail + action form | new file | depends on: step 1 |
   requirements: mirrors `LeadDetailPage.tsx`'s loading/404/error pattern; approve/reject buttons plus
   an edit text input gated behind selecting "edit"; submit calls `actionReview`; a 409 response
   renders an "already actioned" message (not a generic error) | validation: component test covering
   approve, edit (with and without a label — client-side block), and the 409 case
4. `App.tsx` routes | wire `reviews` and `reviews/:runId` | modifies `App.tsx` | depends on: steps 2-3
   | requirements: route param name `runId` (matches `LeadDetailPage`'s `leadId` naming convention) |
   validation: manual navigation
5. `Layout.tsx` nav repoint | `to: '/review'` → `to: '/reviews'` | modifies `Layout.tsx` | depends on:
   step 4 | requirements: label stays "Review Queue" (no user-facing copy change needed) | validation:
   clicking the nav item reaches the real list, not a blank page

Architecture Rule Changes
- [ ] None proposed. This feature adds no new pattern — it is a direct application of two existing Key
  Decisions (Feature 07's fixed `detail_link` convention, which this feature is the first to actually
  satisfy; Feature 08's page/routing/API-client conventions). Conflict check: none found — nothing in
  `.claude/portfolio-reference.md`'s Key Decisions constrains frontend page structure beyond what
  Features 08/09 already established and this plan follows.

Feature-Specific Requirements
- Route param naming: `runId` (not `reviewId` or `id`) — the backend's own path parameter and every
  existing type (`ReviewQueueItemOut.run_id`) already use `run_id`; matching it avoids a
  frontend-only rename that would only create confusion against the API shape.
- The list page does not need pagination or filters (unlike `LeadListPage.tsx`) — the spec's Tier
  scope and expected queue volume (single-operator review queue, not a high-volume list) don't warrant
  it; adding it now would be speculative scope the spec doesn't call for.

Risks
- Risk: A live link from the review detail page to the corresponding `LeadDetailPage` (via
  `lead_id`) would be a nice in-app-cohesion improvement but isn't named in the feature spec's
  acceptance criteria. Mitigation: add it if implementation time allows (it's a 1-line `<Link>`, the
  `lead_id` is already in the response) — but do not treat its absence as blocking Step 7/CD-4.
- Risk: The 409 "already actioned" case is easy to under-test since it requires a specific
  double-submission timing. Mitigation: test it directly by mocking `actionReview` to reject with a
  409-shaped error, not by relying on a real race in a component test.

Acceptance Criteria
(mirrors implementation_plan.md's Feature 15 acceptance criteria exactly — not restated as a separate
list to avoid the two drifting; see that file's Feature 15 entry)

Validation Requirements
- Step 7/CD-4 must exercise all three actions (approve, reject, edit) against a real queued item on
  the live backend (not just mocked component tests) — this is exactly the kind of gap (a nav link
  that "looks" wired but was never actually clicked end-to-end) that produced RB-002 in the first
  place, so this feature's own verification should not repeat that mistake.
- Confirm the notification `detail_link` for an `awaiting_review`/`rejected` outcome now actually
  resolves to a working page (it previously pointed at a route that didn't exist) — this is new,
  previously-latent behavior this feature unlocks, not just its own new page.

Predicted Footprint
Files predicted to change: 7 (2 new pages + 2 new test files + 3 modified files)
Systems predicted to touch: frontend routing (App.tsx), frontend nav (Layout.tsx), frontend API
client (lib/api.ts), frontend pages (2 new)

--- filled in later, by Step 7 / CD-4, once implementation is verified ---
Actual Footprint
Files actually changed: 7 — exactly as predicted (`frontend/src/pages/ReviewQueuePage.tsx`,
`ReviewQueuePage.test.tsx`, `ReviewDetailPage.tsx`, `ReviewDetailPage.test.tsx`, `frontend/src/lib/
api.ts`, `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx`). Zero backend files touched, as
predicted.
Deviations from plan: none in scope/shape. One test-infrastructure fix needed that the plan didn't
anticipate: `ReviewDetailPage.test.tsx`'s tests leaked `vi.spyOn` mocks across `it()` blocks in the
same file (a later test's `actionReview` call used an earlier test's un-reset mock), causing a
false failure only when the full suite ran (not in isolation) — fixed by adding
`afterEach(() => vi.restoreAllMocks())`, matching a pattern this project's other test files hadn't
needed yet since none had multiple tests exercising the same mocked function with different
outcomes.
Rework required: none beyond the mock-cleanup fix above.

Verification performed (CD-4 / Step 7 scoped pass, 2026-09-05):
- 118/118 backend tests passing (unchanged — no backend files touched), 11/11 frontend tests passing
  (4 new: `ReviewQueuePage.test.tsx` x2, `ReviewDetailPage.test.tsx` x4 covering approve, blocked edit,
  409-already-actioned, and 404-not-found). `npm run build` clean. `npm run lint` clean (the same
  pre-existing `react(set-state-in-effect)` warning both new pages carry is the identical pattern
  already present in `LeadDetailPage.tsx`/`LeadListPage.tsx` — not a new class of warning).
- **Live verification against the real backend** (not mocked), per this plan's own Validation
  Requirements: started both dev servers, temporarily ran the backend with
  `CONFIDENCE_THRESHOLD=0.95` (env-var override only, `.env` untouched) so real leads reliably route
  into the review queue for testing purposes (the real `llama3.2:3b` model proved consistently
  confident — 0.8-0.9 — even on the project's own known-ambiguous benchmark messages, consistent with
  Feature 09's benchmark finding; this is a test-setup convenience, not a change to the shipped
  default). Created 4 real queued leads via `POST /leads/webform`, then drove Chromium via a
  throwaway Playwright script (not committed): clicked the sidebar's "Review Queue" link and
  confirmed it reaches a real, populated list (previously a blank page — RB-002's exact defect);
  opened a detail page and confirmed draft classification/confidence render; submitted **Edit** with a
  corrected label and confirmed the pipeline resumed (status became `FAILED` at the CRM-write stage —
  expected in this dev environment, since `HUBSPOT_ACCESS_TOKEN` is an unset placeholder per this
  project's own documented deviation, not a defect in this feature); submitted **Reject** on a second
  item and confirmed status became `REJECTED`; revisited an already-actioned item and confirmed
  submitting again surfaced the "already been actioned by someone else" message (the real backend 409,
  not simulated) rather than a silent failure; visited a nonexistent run id and confirmed the 404
  not-found state. Zero unhandled console/page errors — the only console entries were the browser's
  own resource-load logging of the intentionally-triggered 404/409 responses. Also confirmed via
  `GET /notifications` that existing `awaiting_review`/`rejected` notifications' `detail_link` values
  (`/reviews/{run_id}`, Feature 07's Key Decision) now resolve to a real page for the first time —
  previously-latent behavior this feature unlocks, exactly as this plan's Validation Requirements
  anticipated.
- Both dev servers and the temporary threshold override were stopped/discarded after verification; no
  lasting environment change.

RB-002 (`.claude/refinement-backlog.md`) marked COMPLETED by this round.
