IMPLEMENTATION PLAN
====================

Feature / Round: Feature 08 (Observability / Monitoring View)
Classification: New feature (frontend), Backend change, Database change
Planning Depth: Standard — a genuine cross-system feature (backend read endpoints + a new React
surface), but it reuses the entire existing persistence layer end-to-end; no new architectural
primitive is introduced, only two read-optimization columns and a read-layer status mapping.

Objective
Expose the pipeline's existing per-stage trace store (`PipelineRun`/`StageTrace`, written by every
stage since Feature 01) as a paginated, filterable lead-list view and a per-lead stage-by-stage detail
view in the React frontend — the first real frontend surface this project has beyond the Step 4
bootstrap scaffold (`HomePage.tsx`).

Existing Systems Analysis
- Reusable:
  - `PipelineRun`/`StageTrace` (`app/models/pipeline_run.py`) — the entire data source this feature
    needs already exists and is already written to by every stage via `_write_trace`/`_make_node`.
    Feature 08 adds zero new trace-writing logic.
  - `graph.py`'s `_STAGE_ORDER` — the canonical 6-stage name/order list (`intake_parsing`,
    `intent_classification`, `data_enrichment`, `hubspot_crm_write`, `human_review`,
    `outcome_notification`) already matches every `Stage.name` value used as `StageTrace.stage_name`.
    This is exactly the ordering Feature 08's detail view must iterate to render "not yet run" stages
    correctly — no new stage-order list should be invented on the backend.
  - `Notification`'s fixed `detail_link` convention (`architecture-plan-feature-07.md`'s Key Decision)
    — `/leads/{lead_id}` for auto_processed/failed, `/reviews/{run_id}` for awaiting_review/rejected.
    Feature 08's lead detail page route (`/leads/:leadId`) must match the first half of this
    convention exactly, since Feature 07's notifications already point there.
  - `routers/leads.py` — already exists (POST-only intake endpoints today); the natural home for new
    GET routes, not a new router module.
  - `schemas/pipeline.py`'s `PipelineRunOut`/`StageTraceOut` — a starting shape, extended rather than
    replaced (see New, below).
  - `frontend/src/components/Layout.tsx`/`BuildIndicator.tsx`, `frontend/src/lib/api.ts`'s existing
    fetch-wrapper pattern — reused for the new pages/API calls, not reinvented.
- Duplication Risk Flagged: Feature 07's `outcome_notification.py`'s `_OUTCOME_TYPE_BY_STATUS` dict
  looks reusable for turning a run's status into a display label, but is **not** directly reusable as
  written: it's evaluated at `notify_stage` execution time, before `RunStatus.COMPLETED` is ever
  assigned (`_mark_completed_if_still_running` runs after the graph returns) — it maps
  `RunStatus.RUNNING` -> `"auto_processed"` and has no `COMPLETED` entry at all. Feature 08 reads
  `PipelineRun` rows *after* persistence completes, where `COMPLETED` is the terminal auto-processed
  state and `RUNNING` means a lead is genuinely still mid-pipeline — reusing Feature 07's map unchanged
  would silently mislabel an in-progress lead as auto-processed. Resolution: Feature 08 defines its own
  small post-persistence status-mapping function in the backend response layer (see Architecture Rule
  Changes) rather than importing or modifying Feature 07's stage-internal map.
  No other duplication found — no existing lead-list/detail view, pagination helper, or filter
  mechanism exists anywhere else in the codebase.
- Modify:
  - `backend/app/models/pipeline_run.py` — add two nullable, read-optimized columns to `PipelineRun`:
    `source_channel` and `confidence_score` (see Architecture Rule Changes for why).
  - `backend/app/orchestrator/graph.py` — rename `_STAGE_ORDER` to `STAGE_ORDER` (drop the
    underscore; it becomes a cross-module export the frontend's backend contract depends on, not a
    module-private constant); `run_pipeline()`'s existing final-commit block (which already does
    `db.get(PipelineRun, run_id)` and sets `.status`) also sets `.source_channel`/`.confidence_score`
    from `final_state.intake.source_channel`/`final_state.classification.confidence_score` — both are
    already known by the time any terminal or paused state is reached, since classification always
    runs before the enrich/review/crm_write branch point.
  - `backend/app/schemas/pipeline.py` — add `LeadListItemOut`, `LeadListOut` (paginated envelope),
    `StageDetailOut`, `LeadDetailOut`.
  - `backend/app/routers/leads.py` — add `GET /leads` (list, paginated, filterable, sortable) and
    `GET /leads/{lead_id}` (detail).
  - `frontend/src/App.tsx` — register the two new routes.
  - `frontend/src/components/Layout.tsx` — add a nav link to the lead list (this project's first real
    nav destination beyond the bootstrap placeholder).
  - `frontend/src/lib/api.ts` — add `listLeads(params)`/`getLeadDetail(leadId)` helpers.
- New:
  - `backend/alembic/versions/<new>_add_pipeline_run_list_columns.py` — migration for the two new
    columns.
  - `frontend/src/pages/LeadListPage.tsx` — filterable/sortable/paginated lead table.
  - `frontend/src/pages/LeadDetailPage.tsx` — per-lead 6-stage trace timeline.
  - `frontend/src/lib/stageOrder.ts` — a small static mirror of the backend's `STAGE_ORDER` (stage key
    + human-readable label), needed because TypeScript can't import a Python constant. This is an
    explicitly-flagged, deliberately duplicated 6-item static list (not a duplicated *system* — the
    single source of truth for trace data stays the backend); noted here so a future stage addition
    remembers to update both.
  - Nothing new is required on the pipeline-execution side (no new stage, no new tool, no new state
    slice) — Feature 08 is read-only relative to the orchestrator.
- Navigation Relationships Flagged: No existing frontend screen exists yet for Feature 08 to link
  with — `HomePage.tsx` is the only page today, and both the review queue (Feature 06) and
  notifications (Feature 07) are backend-only so far, with no frontend surface. Feature 08 is
  therefore this round's *reachability target*, not a consumer of one: Feature 07's `Notification.
  detail_link` values already point at `/leads/{lead_id}` (auto_processed, failed), and Feature 11
  (Per-Lead Audit/History Trail UI, Tier 2, `depends_on: [08, 06]`) explicitly says it extends "beyond
  the current-state summary Feature 08's monitoring view provides" and will link back into it — so
  Feature 08's detail page is the future link target for that feature, not the reverse.
  **Gap surfaced, not introduced, out of scope for this feature:** no feature anywhere in
  `implementation_plan.md` (Tier 1, 2, or 3) builds a frontend for the existing `GET /reviews` /
  `POST /reviews/{run_id}/action` backend routes — a human reviewer today has no UI to actually
  approve/reject/edit a queued lead. Feature 08's spec is explicitly scoped to trace *display*, so
  this plan does not add a review-action UI. Because Feature 08's `detail_link`-style convention would
  naturally want to link an `awaiting_review`/`rejected` lead's detail view to `/reviews/{run_id}`,
  and that route currently renders nothing, this plan deliberately does **not** add that link yet
  (`docs/in-app-cohesion.md` §4, avoid linking to a dead destination) — it shows the review outcome as
  an inline status badge instead. When a frontend Review Queue page is eventually built, Feature 08's
  detail view should gain that link at that time; flagged here so it isn't forgotten (see Risks).

System Impact Map
```
FEATURE 08 — Observability / Monitoring View
│
├── Frontend
│   ├── frontend/src/pages/LeadListPage.tsx (new) — filterable/sortable/paginated lead table
│   ├── frontend/src/pages/LeadDetailPage.tsx (new) — per-lead 6-stage trace timeline
│   ├── frontend/src/lib/stageOrder.ts (new) — static stage key/label list mirroring backend STAGE_ORDER
│   ├── frontend/src/lib/api.ts (modify) — listLeads()/getLeadDetail() helpers
│   ├── frontend/src/App.tsx (modify) — routes: /leads, /leads/:leadId
│   ├── frontend/src/components/Layout.tsx (modify) — nav link to /leads
│
├── Backend
│   ├── app/routers/leads.py (modify) — GET /leads, GET /leads/{lead_id}
│   ├── app/schemas/pipeline.py (modify) — LeadListItemOut, LeadListOut, StageDetailOut, LeadDetailOut
│   ├── app/orchestrator/graph.py (modify) — STAGE_ORDER export; run_pipeline() sets the 2 new columns
│
├── Database
│   ├── app/models/pipeline_run.py (modify) — PipelineRun.source_channel, PipelineRun.confidence_score
│   ├── alembic/versions/<new>_add_pipeline_run_list_columns.py (new)
│
├── Existing Systems (reused, not duplicated)
│   ├── PipelineRun / StageTrace (pipeline_run.py) — sole data source, zero new writes to trace content
│   ├── graph.py STAGE_ORDER — canonical stage ordering, reused not reinvented
│   ├── Notification detail_link convention (architecture-plan-feature-07.md) — /leads/{lead_id} honored
│
├── Navigation
│   ├── none today (Feature 08 is this project's first real frontend surface)
│   └── forward-declared: Feature 11's audit/history trail UI will link back into this feature's
│       /leads/:leadId detail page; a not-yet-built Review Queue frontend should eventually gain a
│       link from here to /reviews/{run_id} (see Navigation Relationships Flagged, and Risks)
│
└── AI
    └── N/A — pure read/display layer, no LLM/generation involved
```

Implementation Order (Dependency Graph)
1. **`PipelineRun` model columns + Alembic migration**
   - Purpose: read-optimized columns the list endpoint filters/sorts on, avoiding per-request JSON
     parsing of `StageTrace` snapshots.
   - Existing files: `app/models/pipeline_run.py`. New files: 1 Alembic migration.
   - Dependencies: none.
   - Requirements: `source_channel: str | None`, `confidence_score: float | None`, both nullable
     (an in-progress lead may not have reached classification yet — though in practice both are set
     by intake/classification before any branch point, nullability is the safe default for a lead that
     fails inside `intake_parsing` itself, before `source_channel` is even known... actually
     `source_channel` is set by the intake router before the graph runs, so it is always known; only
     `confidence_score` can legitimately stay null, e.g. classification itself raises).
   - Validation: `alembic upgrade head` succeeds; columns exist with correct nullability.

2. **`STAGE_ORDER` export + `run_pipeline()` denormalization write** (`graph.py`)
   - Purpose: rename the existing private list for cross-module reuse; populate the two new columns
     at the one place `PipelineRun.status` is already persisted after a run terminates.
   - Existing files: `graph.py` (`_STAGE_ORDER` rename, all internal references updated;
     `run_pipeline()`'s final `db.get(PipelineRun, run_id)` block).
   - New files: none.
   - Dependencies: step 1.
   - Requirements: set `run_row.source_channel = final_state.intake.source_channel` and
     `run_row.confidence_score = final_state.classification.confidence_score` immediately alongside the
     existing `run_row.status = final_state.run.status.value` assignment. `resume_pipeline()` does not
     need the same write — the row's `source_channel`/`confidence_score` were already set by the
     original `run_pipeline()` call before the run ever paused, and neither value changes during
     resume (an "edit" review action changes `intent_label`, not `confidence_score`).
   - Validation: a completed run's `PipelineRun` row has both columns populated; a rejected/resumed
     run's row keeps the values set at its original pause point.

3. **Backend schemas** (`schemas/pipeline.py`)
   - Purpose: typed response shapes for the list and detail endpoints, including the post-persistence
     status-mapping this feature owns (distinct from Feature 07's notification-time map — see
     Architecture Rule Changes).
   - Existing files: `schemas/pipeline.py` (extends, doesn't replace, `PipelineRunOut`/`StageTraceOut`).
   - New files: none (added to the same module).
   - Dependencies: step 1.
   - Requirements: `LeadListItemOut` (lead_id, run_id, status [display status], source_channel,
     confidence_score, created_at, updated_at); `LeadListOut` (items, total, page, page_size);
     `StageDetailOut` (stage_key, stage_label, status: COMPLETED|FAILED|NOT_YET_RUN, decision: dict |
     None [the parsed `output_snapshot`, passed through unchanged — no reformatting of underlying
     values, per the spec's own System Behaviors], error: str | None, created_at: datetime | None);
     `LeadDetailOut` (lead_id, run_id, status, source_channel, confidence_score, created_at,
     updated_at, failed_stage, error, stages: list[StageDetailOut]).
   - Validation: schema unit round-trip (`model_validate`/`model_dump`) with a fabricated `PipelineRun`
     + partial `StageTrace` set (simulating an in-progress lead).

4. **`GET /leads` and `GET /leads/{lead_id}`** (`routers/leads.py`)
   - Purpose: the actual query endpoints.
   - Existing files: `routers/leads.py` (added alongside the existing POST intake endpoints, same
     router/module — not a new router).
   - New files: none.
   - Dependencies: steps 1-3.
   - Requirements: `GET /leads` accepts `status` (auto_processed|awaiting_review|rejected|failed|
     in_progress), `source_channel` (web_form|email|callback), `sort` (created_desc [default] |
     confidence_asc | confidence_desc), `page` (default 1), `page_size` (default 20, capped at 100);
     applies filters as SQL `WHERE` clauses on the two new columns plus `status`, never a full-table
     Python-side filter. `GET /leads/{lead_id}` looks up the `PipelineRun` by `lead_id`, 404s if
     missing, iterates `STAGE_ORDER` building one `StageDetailOut` per canonical stage (matching
     `StageTrace` rows by `stage_name`, marking any stage with no row `NOT_YET_RUN` — this is exactly
     the in-progress/failed-partway edge cases from the spec), and applies the post-persistence status
     mapping (`COMPLETED`->`auto_processed`, `RUNNING`->`in_progress`, `FAILED`->`failed`,
     `AWAITING_REVIEW`->`awaiting_review`, `REJECTED`->`rejected`).
   - Validation: list endpoint tests per filter/sort/pagination combination; detail endpoint tests for
     completed/in-progress/failed/awaiting-review leads, plus a 404 test for an unknown `lead_id`.

5. **Backend tests**
   - Purpose: acceptance-criteria coverage.
   - Existing files: none reused directly (new test module). New files:
     `backend/app/tests/test_router_leads_list.py` (or extends the existing leads test file if one
     already covers POST endpoints — check before creating a second file for the same router).
   - Dependencies: step 4.
   - Requirements: see Acceptance Criteria below.
   - Validation: full backend suite (currently 102 tests) still passes, plus new tests for this
     feature.

6. **Frontend API client** (`lib/api.ts`, `lib/stageOrder.ts`)
   - Purpose: typed fetch helpers and the stage-order/label mirror the two pages need.
   - Existing files: `lib/api.ts` (extends the existing fetch-wrapper pattern).
   - New files: `lib/stageOrder.ts`.
   - Dependencies: step 4 (needs the finalized response contract).
   - Requirements: `listLeads(params)` -> `LeadListOut`-shaped response; `getLeadDetail(leadId)` ->
     `LeadDetailOut`-shaped response. `stageOrder.ts` mirrors `STAGE_ORDER`'s 6 keys with
     human-readable labels ("Intake Parsing", "Intent Classification", "Data Enrichment", "HubSpot CRM
     Write", "Human Review", "Outcome Notification").
   - Validation: manual/dev-server smoke check against the running backend.

7. **`LeadListPage`/`LeadDetailPage` + routing + nav link**
   - Purpose: the actual UI surface.
   - Existing files: `App.tsx` (routes), `components/Layout.tsx` (nav link).
   - New files: `pages/LeadListPage.tsx`, `pages/LeadDetailPage.tsx`.
   - Dependencies: step 6.
   - Requirements: list page renders a paginated, filterable (status, source channel), sortable
     (confidence) table with a status badge per row and a link to each lead's detail page; detail page
     renders the 6-stage timeline in `STAGE_ORDER`, visually distinguishing COMPLETED / FAILED /
     NOT_YET_RUN per stage, shows the run-level status badge (including "in progress" for RUNNING and
     "awaiting review"/"rejected" inline badges per the Navigation Relationships note above — no link
     yet, since no frontend destination exists), and shows `failed_stage`/`error` prominently when the
     run is FAILED.
   - Validation: dev server (`npm run dev`) manual check against seeded/live leads covering all four
     terminal statuses plus one in-progress lead; frontend test suite still passes.

8. **Frontend smoke test**
   - Purpose: minimal automated coverage, consistent with this project's existing frontend test depth
     (currently 1 test, `App.test.tsx`).
   - Existing files: none. New files: at minimum one render-level test for `LeadListPage`.
   - Dependencies: step 7.
   - Validation: `npm test` passes.

Architecture Rule Changes
- [ ] "A `PipelineRun`'s post-persistence display status (used by any read-only view built after a run
  has terminated or paused) is computed by its own mapping — `COMPLETED`->`auto_processed`,
  `FAILED`->`failed`, `AWAITING_REVIEW`->`awaiting_review`, `REJECTED`->`rejected`,
  `RUNNING`->`in_progress` — kept separate from Feature 07's `_OUTCOME_TYPE_BY_STATUS`, which is
  evaluated only at `notify_stage`/`persist_outcome_notification` call time, before `COMPLETED` is ever
  assigned, and therefore has no `COMPLETED` entry and treats `RUNNING` as the success case. The two
  mappings answer different questions at different points in a run's lifecycle and must never be
  unified into one shared function." — Conflict check: none found. Feature 07's own Key Decisions scope
  its map explicitly to "notification call site" outcome typing; this is additive, not a contradiction,
  and prevents a future session from "simplifying" by merging the two and silently mislabeling
  in-progress runs as auto-processed.
- [ ] "`PipelineRun` carries two denormalized, read-optimized columns (`source_channel`,
  `confidence_score`), set exactly once, at the same final-commit point in `run_pipeline()` that
  already persists `.status`. These columns exist purely so a list/query view can filter and sort
  without parsing `StageTrace.output_snapshot` JSON per request; `StageTrace`'s own snapshots remain
  the sole authoritative record of what each stage actually produced. Any future feature needing to
  filter/sort a lead list by a value a specific stage produces should add a similarly-scoped
  denormalized column here, set at the same commit point, rather than parsing trace JSON at query
  time or inventing a second query-optimized store." — Conflict check: none found. Does not compete
  with the existing "execution data persists via PipelineRun/StageTrace" Key Decision — that decision
  governs where the authoritative trace lives (unchanged, still `StageTrace`); this is a read-path
  optimization derived from data `StageTrace` already owns.

Feature-Specific Requirements
- Exact table column choices, badge colors/labels, and pagination page-size default are implementer
  judgment within the acceptance criteria below — not promoted to Key Decisions.
- The "awaiting review"/"rejected" inline badge shown without a link (per Navigation Relationships
  Flagged above) is this feature's own scoping decision, not a durable rule other features must follow
  — it reflects only that no frontend review-action destination exists yet, not a permanent policy
  against linking to `/reviews/{run_id}`.

Risks
- Risk: the denormalized `source_channel`/`confidence_score` columns could drift from
  `StageTrace`'s authoritative data if a future run-terminating code path bypasses `run_pipeline()`'s
  final-commit block (e.g., a hypothetical new replay/backfill path). Mitigation: set them in exactly
  one place, document the invariant in `PipelineRun`'s docstring, and have Step 7/CD-4 explicitly check
  that any future run-terminating code path also sets them (or confirm it doesn't need to, because it
  reuses the same row via `resume_pipeline()` the way approve/edit/reject already do).
- Risk: parsing `StageTrace.output_snapshot` JSON at detail-view read time couples the response shape
  to each stage's Pydantic slice field names; a future stage renaming a field silently breaks the
  detail view with no type error at the Python/TypeScript boundary. Mitigation: the backend
  (`LeadDetailOut`/`StageDetailOut`) does the JSON parsing server-side, so a stage-slice rename becomes
  a backend-side typing/test break, not a silent frontend runtime issue.
- Risk: an in-progress (RUNNING) lead has fewer `StageTrace` rows than a terminal lead; a naive detail
  view could assume all 6 rows exist and crash or render blank sections. Mitigation: iterate the
  canonical `STAGE_ORDER` and explicitly mark any stage with no matching trace row `NOT_YET_RUN` — this
  is the spec's own required edge case, not an incidental implementation detail.
- Risk: no frontend destination exists yet for `/reviews/{run_id}`, so a reviewer still cannot actually
  action a queued lead through the UI even after this feature ships — the monitoring view can *show*
  that a lead is awaiting review but not let anyone act on it from the UI. Mitigation: not fixed by this
  feature (out of Feature 08's spec scope); flagged explicitly in `.claude/pipeline-reference.md` as a
  candidate for a future Scope Expansion/CD round, since it's a genuine gap in
  `implementation_plan.md`'s full 14-feature roadmap, not something this plan should silently absorb.
- Risk: large lead volume — the spec requires pagination; naive `OFFSET`/`LIMIT` on `pipeline_run`
  degrades at very large scale. Mitigation: acceptable at this project's actual scale (a portfolio demo
  on a SQLite dev DB) — deliberately not over-engineering with keyset pagination; noted as a known,
  accepted simplification rather than an unaddressed gap.

Acceptance Criteria
- [ ] `GET /leads` returns a paginated list, filterable by `status` and `source_channel`, sortable by
  `confidence_score`.
- [ ] `GET /leads/{lead_id}` returns all 6 canonical stages with `COMPLETED`/`FAILED`/`NOT_YET_RUN`
  status per stage, and the parsed `decision` payload for each `COMPLETED` stage matches the underlying
  `StageTrace.output_snapshot` exactly (no reformatting).
- [ ] A lead currently mid-pipeline (`RUNNING`) shows only its completed-so-far stages as `COMPLETED`
  and every later stage as `NOT_YET_RUN`, with an overall `in_progress` display status — never blank or
  missing sections.
- [ ] A lead whose pipeline failed partway through clearly identifies the failing stage
  (`failed_stage`) and its error, distinct from a stage that simply has not run yet.
- [ ] The `LeadListPage` renders a filterable (status, source channel), sortable (confidence),
  paginated table backed by `GET /leads`; the `LeadDetailPage` renders the full stage timeline backed
  by `GET /leads/{lead_id}`, reachable by clicking a lead-list row.
- [ ] An unknown `lead_id` returns 404 from `GET /leads/{lead_id}` and is handled gracefully by the
  frontend (not an unhandled crash).

Validation Requirements
- All acceptance criteria above.
- Confirm the two new `PipelineRun` columns are set for every terminal/paused status
  (`COMPLETED`/`FAILED`/`AWAITING_REVIEW`/`REJECTED`), not only the success path.
- Confirm no stage's `run()`, `allowed_tools`, or tool-scoping code was touched — Feature 08 must be
  purely additive/read-only relative to the existing orchestrator (grep the diff for changes under
  `app/orchestrator/stages/` — there should be none).
- Confirm the post-persistence status mapping (this feature) and Feature 07's notification-time
  mapping remain two separate functions, not merged into one shared map.
- Cross-check: a lead's `Notification.detail_link` from Feature 07 (`/leads/{lead_id}`) actually
  resolves to this feature's detail page for that same lead.

Predicted Footprint
Files predicted to change: ~11 (new: 1 Alembic migration, `LeadListPage.tsx`, `LeadDetailPage.tsx`,
`stageOrder.ts`, 1 new backend test file, 1 new frontend test; modified: `models/pipeline_run.py`,
`orchestrator/graph.py`, `schemas/pipeline.py`, `routers/leads.py`, `lib/api.ts`, `App.tsx`,
`components/Layout.tsx`)
Systems predicted to touch: `PipelineRun` model/migration, `run_pipeline()`'s final-commit block,
leads router/schemas, frontend routing/nav/API client, `.claude/portfolio-reference.md` Key Decisions.

--- filled in later, by Step 7, once implementation is verified ---
Actual Footprint
Files actually changed: [pending Step 6/7]
Deviations from plan: [pending Step 6/7]
Rework required: [pending Step 6/7]
