IMPLEMENTATION PLAN
====================

Feature / Round: Feature 16 (Failed-Run Retry / Resubmission)
Classification: Feature expansion, Backend change, Cross-system integration
Planning Depth: Standard, treated with Deep-level scrutiny on the orchestrator-graph section —
this extends the project's Critical-risk per-stage orchestration layer (`.claude/portfolio-
reference.md`'s Key Constraints), so duplication/reuse discipline there gets full attention even
though the feature itself is a single, well-scoped extension of an already-established pattern
(Feature 06's resume graph), not new architecture.

Objective
Let a `FAILED` `PipelineRun` be retried from the stage that raised, by generalizing Feature 06's
existing resume-graph mechanism (fixed at `crm_write_stage -> notify_stage`) to start from
whichever stage actually failed, and reconstructing the state that stage needs from the failed
run's own persisted `StageTrace` output — since a `FAILED` run, unlike an `AWAITING_REVIEW`
`ReviewQueueItem`, has no full-state snapshot already stored.

Existing Systems Analysis
- Reusable: `app/orchestrator/graph.py`'s `_make_node`, `_make_human_review_node`,
  `_route_or_fail`, `_route_after_enrich` — the actual reusable unit in this codebase's graph
  design (Feature 06's `build_resume_graph` already reuses these rather than the enclosing
  `build_graph`/`build_resume_graph` functions themselves being parameterized). `STAGE_ORDER` —
  the canonical stage list `app/routers/leads.py` already iterates — for mapping a failed
  `StageTrace.stage_name` back to its slice name and index. `PipelineRun`/`StageTrace` tables —
  no new columns or migration needed; `StageTrace.output_snapshot` already holds everything a
  retry needs to reconstruct pre-failure state. The non-unique `PipelineRun.lead_id` column and
  Feature 11's `GET /leads/{lead_id}/history` merge logic — both already designed for exactly
  this "multiple attempts, one lead_id" shape and need no changes to support a second row.
  `app/routers/reviews.py`'s `get_resume_graph_factory` pluggable-dependency pattern for making
  the compiled graph swappable in tests without live HubSpot/Ollama credentials.
- Duplication Risk Flagged: Building `build_retry_graph` as a single flat function (mirroring how
  `build_resume_graph` is already written, rather than trying to make `build_graph` itself accept
  a configurable start node) is a deliberate choice to match this codebase's existing convention,
  not an oversight — see Feature-Specific Requirements below for why a shared parameterized
  builder was considered and rejected. No other near-miss found: nothing else in the codebase
  reconstructs pipeline state from trace rows or retries a failed run today.
- Modify: `app/routers/leads.py`'s `get_lead_detail` — its current `PipelineRun` query
  (`.filter(PipelineRun.lead_id == lead_id).first()`, no `ORDER BY`) has always returned an
  arbitrary row when more than one exists for a `lead_id`, but this was previously unreachable in
  practice since nothing ever created a second `PipelineRun` row for the same lead. Feature 16 is
  the first feature to make that state real, so this latent gap must be closed as part of this
  round: add `.order_by(PipelineRun.created_at.desc())` so the endpoint (and therefore
  `LeadDetailPage.tsx`) always shows the most recent attempt.
- New: `build_retry_graph()` / `build_production_retry_graph()` / `retry_pipeline()` in
  `graph.py`; a small state-reconstruction helper (also in `graph.py`, colocated with the graph
  builders it serves — no new module needed for one helper); `POST /leads/{lead_id}/retry` in
  `leads.py`; the frontend Retry action and its `api.ts` function. Nothing here duplicates an
  existing system — each is the first thing of its kind.
- Navigation Relationships Flagged: none new. `LeadDetailPage.tsx` already links to
  `LeadHistoryPage.tsx` (Feature 11) and back; retry doesn't introduce a new screen, only a new
  action on an existing one, so no new link is needed in either direction.

System Impact Map

FEATURE 16 — Failed-Run Retry / Resubmission
│
├── Frontend
│   ├── `LeadDetailPage.tsx` — Retry action on the existing failed-state banner
│   ├── `lib/api.ts` — new `retryLead(leadId)` function
│
├── Backend
│   ├── `app/routers/leads.py` — new `POST /{lead_id}/retry` route; `get_lead_detail` ordering fix
│   ├── `app/orchestrator/graph.py` — `build_retry_graph`, `build_production_retry_graph`,
│   │     `retry_pipeline`, state-reconstruction helper
│
├── Database
│   ├── none added — reuses `pipeline_run` / `stage_trace` as-is
│
├── Existing Systems (reused, not duplicated)
│   ├── `_make_node` / `_make_human_review_node` / `_route_or_fail` / `_route_after_enrich`
│   │     (Feature 01/06's graph-node building blocks)
│   ├── `STAGE_ORDER` (Feature 01/08's canonical stage list)
│   ├── Feature 11's multi-`PipelineRun`-per-`lead_id` history merge (unchanged, just exercised)
│   ├── `app/routers/reviews.py`'s pluggable-graph-factory dependency pattern (mirrored, not
│   │     reused directly — a new `get_retry_graph_factory` in `leads.py`, same shape)
│
├── Navigation
│   ├── none new — see Existing Systems Analysis above
│
└── AI
    └── N/A — no new AI integration; the retried stage(s) reuse whatever tool bindings
          (Ollama/HubSpot) that stage already had

Implementation Order (Dependency Graph)

`STAGE_ORDER` + existing graph-node builders (Feature 01/06)
  → state-reconstruction helper (reads `StageTrace.output_snapshot`, new)
  → `build_retry_graph` / `build_production_retry_graph` (new)
  → `retry_pipeline` (new; depends on the graph + helper above)
  → `POST /leads/{lead_id}/retry` route + `get_retry_graph_factory` dependency (new; calls
    `retry_pipeline`)
  → `get_lead_detail`'s ordering fix (independent of the above, but same file/session — do it in
    the same pass to avoid a second review touching `leads.py`)
  → `frontend/src/lib/api.ts`'s `retryLead()` (depends on the route existing)
  → `LeadDetailPage.tsx`'s Retry action (depends on `retryLead()`)

1. **State-reconstruction helper** (`graph.py`) — purpose: rebuild a `LeadPipelineState` from a
   failed run's `StageTrace` rows, up to (not including) the failed stage. Existing files
   affected: `graph.py`. New files: none. Dependencies: `STAGE_ORDER`, the four `*Slice` Pydantic
   models already in `state.py`. Requirements: for each `STAGE_ORDER` entry before the failed
   stage's index, deserialize that stage's `output_snapshot` into its slice type and set it on a
   fresh `LeadPipelineState`; set `run` to a new `RunMetadata(run_id=<new>, lead_id=..,
   status=RUNNING)`. Validation: unit test asserts the reconstructed state's `intake`/
   `classification`/`enrichment` fields match what the original run actually produced.

2. **`build_retry_graph(start_stage, stages, registry, session_factory, confidence_threshold)`**
   (`graph.py`) — purpose: a compiled graph starting at whichever node `start_stage` maps to,
   built only from the nodes actually reachable from there (mirrors `build_resume_graph`'s
   existing crm_write-only shape when `start_stage="crm_write"`). Existing files affected:
   `graph.py`. New files: none. Dependencies: step 1's reconstructed state as its eventual input;
   the existing `_make_node`/`_make_human_review_node`/`_route_or_fail`/`_route_after_enrich`
   helpers. Requirements: reject an unsupported `start_stage` (e.g. `"notification"`) explicitly
   rather than building a malformed graph; only add `human_review_stage` when reachable (i.e.
   `start_stage` is `"intake"`, `"classification"`, or `"enrichment"`) — an unreachable node is a
   langgraph compile-time error. Validation: a test per plausible `start_stage` value confirms the
   compiled graph's shape (which nodes exist, which are reachable).

3. **`retry_pipeline(lead_id, ...)`** (`graph.py`) — purpose: the actual entry point — find the
   lead's most recent `FAILED` run, find which stage failed, create a new `PipelineRun` row,
   reconstruct state (step 1), invoke the retry graph (step 2), persist the final status. Existing
   files affected: `graph.py`. New files: none. Dependencies: steps 1-2. Requirements: raise a
   catchable, specific error (not a bare exception) when no `FAILED` run exists, for the router to
   translate into `409`; never mutate the original failed `PipelineRun` row. Validation: test
   asserts a new row is created, the old row is untouched, and the final status/columns match
   `run_pipeline`'s own finalization behavior.

4. **`POST /leads/{lead_id}/retry`** (`leads.py`) — purpose: expose step 3 over HTTP, with the
   same pluggable-graph-factory testability `reviews.py` already established. Existing files
   affected: `leads.py`. New files: none. Dependencies: step 3. Requirements: `404`/`409` mapped
   correctly (lead not found vs. no failed run to retry); response shape matches the existing
   `PipelineRunOut` other trigger/action endpoints already return. Validation: endpoint test
   confirms success + both error paths.

5. **`get_lead_detail`'s ordering fix** (`leads.py`) — purpose: close the latent unordered-`.first()`
   gap identified above. Existing files affected: `leads.py`. New files: none. Dependencies: none
   (independent fix, bundled here since it's the same file and the same feature that makes it
   observable). Requirements: add `.order_by(PipelineRun.created_at.desc())`. Validation: test
   seeds two `PipelineRun` rows for one `lead_id` (a `FAILED` one created first, a `COMPLETED` one
   created second) and asserts `GET /leads/{lead_id}` returns the second.

6. **`frontend/src/lib/api.ts`: `retryLead(leadId)`** — purpose: thin POST wrapper, same shape as
   every other `api.ts` function. Existing files affected: `api.ts`. New files: none. Dependencies:
   step 4. Requirements: returns the same `LeadDetail`-compatible shape (or triggers a refetch) so
   the page can update without a manual reload. Validation: covered by step 7's component test.

7. **`LeadDetailPage.tsx`: Retry action** — purpose: user-facing entry point. Existing files
   affected: `LeadDetailPage.tsx`, `LeadDetailPage.test.tsx`. New files: none. Dependencies: step
   6. Requirements: button appears only when `lead.status === 'failed'`; on click, calls
   `retryLead`, then re-fetches lead detail so status/stages update in place. Validation:
   component test simulates click, asserts the API call and the updated displayed status.

Architecture Rule Changes
- [ ] None proposed. This feature is a direct application of two Key Decisions
  `.claude/portfolio-reference.md` already records (`PipelineRun.lead_id`'s non-uniqueness, and
  Feature 06's resume-via-orchestrator-not-bespoke-code-path rule) — it exercises them rather than
  establishing a new one. Conflict check: none found; no existing Key Decision contradicts
  anything here.

Feature-Specific Requirements
- Why `build_retry_graph` is a new, separately-written function rather than a parameterized
  `build_graph`/`build_resume_graph`: this codebase's own convention (established when Feature 06
  added `build_resume_graph`) is one small, flat, explicit graph-builder function per graph shape,
  reusing the per-node building blocks but not the enclosing builder functions themselves. Forcing
  a single configurable builder to cover three shapes (full run, fixed crm_write resume, and now
  an arbitrary-start retry) would need a more complex conditional-node-inclusion API than the
  three call sites actually need individually — worse for a portfolio piece whose Critical risk is
  exactly "is the per-stage boundary architecturally real and easy to verify by inspection."
- Retry does not attempt to support starting from the `notification` stage (see Feature spec's
  Edge Cases) — an outcome-notification failure is already swallowed by
  `persist_outcome_notification`'s own try/except (it is a best-effort side effect, never a
  gating condition per Feature 07's Key Decision), so it never produces a `FAILED` run in the
  first place; there is nothing to retry for that stage.

Risks
- Risk: `build_retry_graph` adds a node that ends up unreachable for some `start_stage` value
  (langgraph raises at `.compile()`). Mitigation: only add `human_review_stage` when
  `start_stage` is at or before `"enrichment"` in `STAGE_ORDER`; a unit test compiles the graph
  for every plausible `start_stage` value.
- Risk: state reconstruction silently produces a wrong/incomplete slice if a prior stage's
  `output_snapshot` is missing or fails to deserialize (e.g. a schema drift between when the
  original run wrote it and now). Mitigation: this is a pre-existing risk shape Feature 06's
  `ReviewQueueItem.state_snapshot` already accepts implicitly (both rely on Pydantic model
  validation raising if the stored JSON doesn't match); scope for this round is matching that same
  behavior, not adding new defensive handling beyond it.
- Risk: `get_lead_detail`'s ordering fix changes behavior for any lead that already has multiple
  `PipelineRun` rows in an existing dev/demo database from prior ad hoc testing. Mitigation: this
  is a correctness fix, not a behavior this project ever intentionally relied on (Feature 11's own
  spec already assumes "most recent" is the right read for a current-state view); no migration
  needed since no schema changes.
- Risk: regression to Feature 06's existing resume path if `build_resume_graph` is touched while
  building the more general `build_retry_graph`. Mitigation: `build_resume_graph` is left
  completely unmodified; `build_retry_graph` is additive, new code only.

Acceptance Criteria
- [ ] All acceptance criteria already stated in `implementation_plan.md`'s Feature 16 spec
- [ ] `build_resume_graph` and its existing Feature 06 tests are unmodified and still pass
  unchanged (proves no regression from adding the more general retry mechanism alongside it)

Validation Requirements
- CD-4 must confirm `get_lead_detail`'s ordering fix specifically (a seeded two-run scenario), not
  just that retry's own happy path works — this is the one change in this round that touches
  already-shipped Feature 08 behavior, not purely new surface
- CD-4 must confirm the full existing backend suite still passes (this round touches
  `graph.py`, a file every pipeline-stage feature depends on)

Predicted Footprint
Files predicted to change: 8 (`graph.py`, `leads.py`, `api.ts`, `LeadDetailPage.tsx`,
`LeadDetailPage.test.tsx`, plus 2 new backend test files + this plan's own Actual Footprint
appendix)
Systems predicted to touch: orchestrator graph, leads router, lead-detail frontend page

--- filled in later, by Step 7 / CD-4, once implementation is verified ---
Actual Footprint
Files actually changed: 8 — exactly as predicted:
`backend/app/orchestrator/graph.py`, `backend/app/routers/leads.py`,
`backend/app/tests/test_orchestrator_retry.py`, `backend/app/tests/test_router_leads_retry.py`,
`frontend/src/lib/api.ts`, `frontend/src/pages/LeadDetailPage.tsx`,
`frontend/src/pages/LeadDetailPage.test.tsx`, plus this plan's own Actual Footprint appendix.
Deviations from plan: none architectural. One naming addition not explicitly named in the plan:
`api.ts`'s existing `ReviewActionResult` interface was generalized into a new `PipelineRunResult`
interface (with `ReviewActionResult` kept as a type alias to it) so `retryLead()` could return the
same shape `actionReview()` already does without duplicating an identical interface under a
second name — a small, in-the-spirit-of-the-plan reuse decision made during implementation, not a
new system.
Rework required: none. Full backend suite (147/147) and frontend suite (47/47) passed on the
first full run; `build_resume_graph` and its existing Feature 06 tests were left untouched and
still pass unchanged, confirming no regression from adding the more general `build_retry_graph`
alongside it.
