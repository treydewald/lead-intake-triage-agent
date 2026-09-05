IMPLEMENTATION PLAN
====================

Feature / Round: Feature 11 (Per-Lead Audit/History Trail UI)
Classification: New feature, Cross-system integration, UI/UX change
Planning Depth: Standard — a new read-only aggregation view over two existing systems
(PipelineRun/StageTrace, ReviewQueueItem) plus one new frontend page; not Deep (no new persistent
data model, not security-sensitive, touches 2 existing systems not 4+).

Objective
Give each lead a full chronological history view — every pipeline stage transition plus any human
review action taken, across however many `PipelineRun` attempts share that lead's `lead_id` — reachable
from and linking back to Feature 08's existing per-lead detail view.

Existing Systems Analysis
- Reusable:
  - `backend/app/models/pipeline_run.py`'s `PipelineRun`/`StageTrace` — the same execution-log tables
    Feature 08 already reads; no new table needed for stage-transition history.
  - `backend/app/models/review_queue.py`'s `ReviewQueueItem` — already carries `reviewer_action`,
    `corrected_intent_label`, `actioned_at`, keyed by `lead_id`; the review-action side of the timeline
    needs no new table either.
  - `backend/app/orchestrator/graph.py`'s `STAGE_ORDER` and `backend/app/routers/leads.py`'s
    `_STAGE_LABELS` — the canonical stage-name/label mapping Feature 08 already established; reused
    as-is, not reimplemented.
  - `frontend/src/lib/stageOrder.ts` — the frontend's existing TS mirror of `STAGE_ORDER`, reused for
    stage labels on the new timeline page.
  - `frontend/src/lib/api.ts` conventions (typed fetch helper per endpoint) and
    `frontend/src/pages/LeadDetailPage.tsx`'s/`BenchmarkPage.tsx`'s existing Tailwind card/timeline
    styling — extended, not reinvented.
- Duplication Risk Flagged: None found. This is additive to Feature 08 (a different view of the same
  underlying data, not a second list/detail page for leads) and does not touch Feature 08's own
  `GET /leads`/`GET /leads/{lead_id}` endpoints or their response shapes.
- Modify:
  - `backend/app/models/review_queue.py` (`ReviewQueueItem`) — add one nullable `reviewer_name: str |
    None` column. See "reviewer identity" discussion below.
  - `backend/app/schemas/review.py` — `ReviewActionRequest` gains optional `reviewer_name: str | None
    = None`; `ReviewQueueItemOut` is a PENDING-only listing shape and does not need this field.
  - `backend/app/routers/reviews.py`'s `action_review` — persist `reviewer_name` in the same atomic
    `UPDATE ... WHERE status='PENDING'` that already sets `reviewer_action`/`corrected_intent_label`/
    `actioned_at`. No change to the concurrency-safe claim logic itself.
  - `frontend/src/pages/ReviewDetailPage.tsx` (Feature 15) — add one optional "Your name" text input to
    the existing approve/reject/edit action form, sent as `reviewer_name`.
  - `backend/app/routers/leads.py` — add the new `GET /leads/{lead_id}/history` endpoint alongside the
    existing `GET /leads/{lead_id}` (same router, same file — this is a lead-scoped read view, not a
    new resource).
  - `backend/app/schemas/pipeline.py` — add `TimelineEntryOut`/`LeadHistoryOut` response shapes.
  - `frontend/src/lib/api.ts` — add `getLeadHistory(leadId)`.
  - `frontend/src/App.tsx` — add the `leads/:leadId/history` route.
  - `frontend/src/pages/LeadDetailPage.tsx` — add a "View Full History" link.
- New:
  - `frontend/src/pages/LeadHistoryPage.tsx` — the new timeline view. Genuinely new because no existing
    page renders a merged, cross-run, cross-source (stage + review-action) chronological list; Feature
    08's `LeadDetailPage.tsx` renders exactly one run's `STAGE_ORDER`-shaped current state, which is a
    different shape and a different question ("what's true now" vs. "what happened, in order").
  - One new Alembic migration for the `reviewer_name` column.
- Navigation Relationships Flagged: `LeadDetailPage.tsx` (Feature 08) gains a link to
  `/leads/:leadId/history`; `LeadHistoryPage.tsx` links back to `/leads/:leadId` — the exact
  bidirectional relationship the feature spec itself requires ("so a user can move between 'current
  state' and 'full history' naturally"). No top-level `Layout.tsx` nav entry — same pattern
  `ReviewDetailPage.tsx` already uses (reached only via its list page's links, not a persistent nav
  item), since this is a per-lead drill-down, not an independent section of the app.

A note on an architecture gap this analysis surfaced (not a duplication risk, a genuine mismatch
between the feature spec and current behavior):

- **"Multiple pipeline attempts for the same lead" is not a behavior any current code path produces.**
  `backend/app/routers/leads.py`'s `_run_and_respond` mints a fresh `lead_id = str(uuid4())` for every
  webform/email/callback submission, and no endpoint anywhere resubmits/retries an existing `lead_id`
  (confirmed: no `retry`/`resubmit`/`re-run` route exists in `backend/app/routers/`).
  `implementation_plan.md`'s Feature 01 spec names "duplicate pipeline invocation for the same lead" only
  as a theoretical edge case handled by Feature 05's CRM-write idempotency, never as a user-triggered
  retry feature. **Decision: do not build a retry/resubmit mechanism — that is new scope this feature's
  spec does not ask for.** Instead, the new history endpoint queries *all* `PipelineRun` rows for a
  `lead_id` (there is no uniqueness constraint on that column — it was always technically possible to
  have more than one), so the multi-attempt acceptance criterion is satisfiable and forward-compatible
  with any future feature that does add a retry path, without this feature inventing one. Step 7/CD-4's
  verification of that specific acceptance criterion will need to seed two `PipelineRun` rows sharing a
  `lead_id` directly at the DB/fixture level (there is no live user flow that produces this today) — see
  Validation Requirements below.

System Impact Map
```
FEATURE 11
│
├── Frontend
│   ├── frontend/src/pages/LeadHistoryPage.tsx (new)
│   ├── frontend/src/pages/LeadDetailPage.tsx (modify — "View Full History" link)
│   ├── frontend/src/pages/ReviewDetailPage.tsx (modify — optional reviewer name input)
│   ├── frontend/src/App.tsx (modify — new route)
│   ├── frontend/src/lib/api.ts (modify — getLeadHistory(), reviewer_name on submitReviewAction())
│
├── Backend
│   ├── backend/app/routers/leads.py (modify — GET /leads/{lead_id}/history)
│   ├── backend/app/routers/reviews.py (modify — persist reviewer_name)
│   ├── backend/app/schemas/pipeline.py (modify — TimelineEntryOut/LeadHistoryOut)
│   ├── backend/app/schemas/review.py (modify — ReviewActionRequest.reviewer_name)
│
├── Database
│   ├── backend/app/models/review_queue.py (modify — reviewer_name column)
│   ├── backend/alembic/versions/<new>_add_reviewer_name.py (new)
│
├── Existing Systems (reused, not duplicated)
│   ├── PipelineRun / StageTrace (backend/app/models/pipeline_run.py)
│   ├── ReviewQueueItem (backend/app/models/review_queue.py)
│   ├── STAGE_ORDER / _STAGE_LABELS (graph.py / leads.py)
│   ├── frontend/src/lib/stageOrder.ts
│
├── Navigation
│   ├── LeadDetailPage.tsx → gains a link into LeadHistoryPage.tsx
│   ├── LeadHistoryPage.tsx → links back to LeadDetailPage.tsx
│
└── AI
    └── N/A — this feature is a read-only view over already-persisted data; no new AI call
```

Implementation Order (Dependency Graph)
1. **`ReviewQueueItem.reviewer_name` column + migration**
   purpose: capture "by whom" for a review action without building authentication (see Architecture
   Rule Changes below)
   existing files: `backend/app/models/review_queue.py`
   new files: `backend/alembic/versions/<new>_add_reviewer_name.py`
   dependencies: none
   requirements: nullable `String`, no default; chain the migration onto the **actual current
   alembic head at claim time** — confirmed `a95fad549dbf` as of this planning session
   (`add notification delivery columns`), but re-run `alembic heads` before writing `down_revision`
   rather than trusting this plan's stated value, per the pipeline-insight logged after Feature 10's
   own down_revision went stale between planning and claim time
   validation: `alembic upgrade head` applies cleanly; existing `review_queue`/`reviews` tests
   unaffected (field is optional, no existing test supplies it)

2. **`ReviewActionRequest.reviewer_name` (optional) + `reviews.py` persists it**
   purpose: accept "by whom" at the point a reviewer takes action
   existing files: `backend/app/schemas/review.py`, `backend/app/routers/reviews.py`
   new files: none
   dependencies: step 1
   requirements: add to the same atomic `UPDATE ... WHERE status='PENDING'` `.values(...)` call in
   `action_review` — do not add a second write; `reviewer_name` stays `None` when omitted
   validation: existing `test_router_reviews.py`-style tests still pass with the field omitted; a new
   test asserts a supplied `reviewer_name` persists and appears back on a subsequent history read

3. **`TimelineEntryOut`/`LeadHistoryOut` schemas + `GET /leads/{lead_id}/history`**
   purpose: the aggregation endpoint this feature is actually about
   existing files: `backend/app/schemas/pipeline.py`, `backend/app/routers/leads.py`
   new files: none
   dependencies: steps 1-2 (reviewer_name must exist to include it)
   requirements:
   - Query **all** `PipelineRun` rows where `lead_id == lead_id` (not `.first()` — see the multi-attempt
     gap noted above), ordered by `created_at`; 404 if zero rows (same as the existing
     `GET /leads/{lead_id}`).
   - For each such run, load its `StageTrace` rows (ordered by `created_at`) and emit one
     `TimelineEntryOut(kind="stage", run_id=..., stage_key=..., stage_label=..., status=...,
     created_at=..., error=...)` per trace, reusing `_STAGE_LABELS`.
   - Query all `ReviewQueueItem` rows where `lead_id == lead_id`; for each one with
     `status == "ACTIONED"`, emit one `TimelineEntryOut(kind="review_action", run_id=...,
     reviewer_action=..., corrected_intent_label=..., reviewer_name=..., created_at=actioned_at)`.
     A `PENDING` (not yet actioned) item emits nothing — this is what keeps an auto-processed lead's
     timeline free of a fabricated review entry (edge case 1).
   - Merge both lists and sort by `created_at` ascending. Never merge/deduplicate two entries into one
     — an actual re-run's stage transitions and a resume's post-pause transitions must both appear
     (edge case 2 / acceptance criterion 4).
   validation: unit test with a synthetic multi-run `lead_id` fixture (per the gap noted above); unit
   test for the no-review-action case; unit test for a rejected lead showing the reject entry as
   terminal and distinct from a `FAILED` stage entry

4. **`LeadHistoryPage.tsx` + `api.ts` + `App.tsx` route**
   purpose: render the timeline
   existing files: `frontend/src/lib/api.ts`, `frontend/src/App.tsx`, `frontend/src/lib/stageOrder.ts`
   new files: `frontend/src/pages/LeadHistoryPage.tsx`
   dependencies: step 3
   requirements: one chronological list, each entry showing timestamp + stage label (stage entries) or
   reviewer action + `reviewer_name` (falls back to "Reviewer" display text when null) + corrected
   label if present (review-action entries); a back-link to `/leads/:leadId`
   validation: `npm run build` clean; manual Playwright check against a real seeded multi-stage lead

5. **`LeadDetailPage.tsx` "View Full History" link**
   purpose: close the bidirectional navigation loop
   existing files: `frontend/src/pages/LeadDetailPage.tsx`
   new files: none
   dependencies: step 4
   requirements: a visible link near the existing "← Back to leads" link
   validation: manual click-through, both directions

6. **`ReviewDetailPage.tsx` optional "Your name" input**
   purpose: let a reviewer actually supply `reviewer_name` through the UI (steps 1-2 only add backend
   support)
   existing files: `frontend/src/pages/ReviewDetailPage.tsx`
   new files: none
   dependencies: step 2
   requirements: optional text input alongside the existing approve/reject/edit action form; omitting
   it must not block submission (matches the backend field being optional)
   validation: manual click-through — action with a name supplied shows up correctly on the new
   history page; action with no name shows the "Reviewer" fallback

Architecture Rule Changes
- [ ] **A per-lead read view that aggregates pipeline execution history must query every `PipelineRun`
  row sharing a `lead_id` (ordered by `created_at`), never assume exactly one — even though today's
  three intake endpoints happen to mint a fresh `lead_id` per submission and no code path currently
  produces a second `PipelineRun` for an existing `lead_id`.** `PipelineRun.lead_id` carries no
  uniqueness constraint specifically so multi-attempt history stays representable if a future feature
  ever adds a retry/resubmit path. Feature 08's `GET /leads/{lead_id}` correctly uses `.first()` because
  its job is "current state of the most recent/only attempt" — this rule applies to a *history* view,
  not a *current-state* view, and does not change Feature 08's endpoint.
  Conflict check: none found — additive to, not a restatement of, Feature 08's "post-persistence display
  status" Key Decision (which governs a different question: mapping `RunStatus` to a display string for
  one run, not how many runs to consider).
- [ ] **Reviewer identity is captured as an optional, free-text, self-reported `reviewer_name` field on
  `ReviewQueueItem`/`ReviewActionRequest`, populated at action time — this project has no User/auth
  model, and building one is out of scope for what is architecturally a single-operator review
  workflow.** Any future feature needing "who did X" should extend this same field/pattern rather than
  introducing authentication.
  Conflict check: none found — this generalizes, rather than contradicts, Feature 07's existing Key
  Decision note that `Notification` has "no addressee field (no User/auth model exists)"; that was a
  deliberate omission for a different reason (no one to address a notification to) but the same
  underlying constraint (no auth) applies here, and this rule states explicitly how a future
  "who did this" requirement should be met when it comes up again.

Feature-Specific Requirements
- Timeline entry display: stage entries show stage label + status + timestamp (+ error text if
  `FAILED`); review-action entries show the action taken, `reviewer_name` (or "Reviewer" if null), the
  corrected label if `action == "edit"`, and timestamp.
- "View Full History" link placement/copy on `LeadDetailPage.tsx`, and "Your name" input placement/copy
  on `ReviewDetailPage.tsx`, are UI-copy details for Step 6 to finalize consistent with each page's
  existing style — not durable rules, not restated here beyond what Implementation Order steps 4-6
  already specify.

Risks
- Risk: The multi-attempt acceptance criterion has no real user flow to exercise it, so it could be
  accidentally verified only against a single-run lead and falsely marked passing.
  Mitigation: Validation Requirements below explicitly requires a fixture-seeded two-run test — Step
  7/CD-4 must confirm this specific test exists and passes, not just that the endpoint works for the
  common single-run case.
- Risk: Adding `reviewer_name` free-text input could read as a stand-in for real authentication in a
  portfolio review, if not clearly framed as a deliberate scope decision.
  Mitigation: The Architecture Rule Change above states the reasoning explicitly in
  `.claude/portfolio-reference.md`'s Key Decisions, so this reads as an intentional, justified choice
  under code/documentation inspection rather than an oversight.
- Risk: A new endpoint duplicating part of `GET /leads/{lead_id}`'s stage-iteration logic
  (`traces_by_stage`, `_STAGE_LABELS`) could drift from it over time.
  Mitigation: Both endpoints import the same `_STAGE_LABELS`/`STAGE_ORDER` constants; the history
  endpoint iterates actual `StageTrace` rows directly (it doesn't need `STAGE_ORDER`'s "show NOT_YET_RUN
  placeholders" behavior, since a history view only ever lists things that actually happened) — no
  shared function to keep in sync, so there's nothing to drift.

Acceptance Criteria
- [ ] A lead that went through Human Review shows both the pipeline stage transitions and the
  reviewer's action, correctly ordered by time (feature spec)
- [ ] An auto-processed lead's timeline contains no fabricated review-related entries (feature spec)
- [ ] Navigating from Feature 08's detail view reaches this timeline view for the same lead, and back
  (feature spec + this plan's Navigation Relationships)
- [ ] A fixture-seeded lead with two `PipelineRun` rows sharing one `lead_id` shows both attempts'
  stage transitions distinctly, in actual chronological order (feature spec, made testable per this
  plan's multi-attempt gap note)
- [ ] A review action taken with `reviewer_name` supplied displays that name on the history timeline;
  one taken without it displays the "Reviewer" fallback, never a blank/null-looking value
  (this plan's Architecture Rule Change)
- [ ] `GET /leads/{lead_id}/history` 404s for an unknown `lead_id`, matching `GET /leads/{lead_id}`'s
  existing behavior

Validation Requirements
- Confirm the actual alembic head at claim time via `alembic heads` before writing the new migration's
  `down_revision` — do not trust this plan's stated `a95fad549dbf` if another feature's migration has
  landed since this plan was written (per the Feature 10 pipeline insight).
- Confirm the multi-attempt test seeds two `PipelineRun` rows directly (DB fixture / test setup), not
  via any live API call — no such call exists, and Step 7/CD-4 should not spend time looking for one.
- Confirm `GET /leads/{lead_id}/history` does not alter or duplicate `GET /leads/{lead_id}`'s own
  response shape or behavior — both must keep working unchanged, verified by re-running Feature 08's
  existing tests unmodified.
- Confirm `reviewer_name` is genuinely optional end-to-end: an approve/reject/edit action with no name
  supplied must not fail validation anywhere in the chain.

Predicted Footprint
Files predicted to change: 10 (5 new: migration, `LeadHistoryPage.tsx`; 8 modified: `review_queue.py`,
`review.py` schema, `reviews.py`, `pipeline.py` schema, `leads.py` router, `api.ts`, `App.tsx`,
`LeadDetailPage.tsx`, `ReviewDetailPage.tsx` — see exact list in Implementation Order above)
Systems predicted to touch: `ReviewQueueItem` model/schema/router, `PipelineRun`/`StageTrace` read
path, frontend routing, `LeadDetailPage.tsx`, `ReviewDetailPage.tsx`, one new Alembic migration

--- filled in later, by Step 7 / CD-4, once implementation is verified ---
Actual Footprint
Files actually changed: [pending Step 6]
Deviations from plan: [pending Step 6/7]
Rework required: [pending Step 6/7]
