IMPLEMENTATION PLAN
====================

Feature / Round: Feature 06 — Human Review & Approval Gate
Classification: New feature, Cross-system integration (extends the orchestrator's own execution
model, not just a new stage body)
Planning Depth: Deep — one sentence reason: the feature spec assumes a pause/resume mechanism
("reuses Feature 01's orchestrator resume mechanism") that does not actually exist in the codebase
today; this plan must design and add it, plus a new persisted domain model and a new
concurrency-sensitive API surface — 4+ existing systems touched (`contracts.py`'s Stage set,
`graph.py`, `state.py`'s `RunStatus`, the router/schema layer).

Objective
Replace the stubbed `review` stage with a real gate: leads already routed to Human Review by the
existing confidence-threshold edge are persisted as an actionable queue item with everything needed
to resume; a new reviewer-action endpoint lets a human approve (resume as classified), reject (halt,
terminal, not an error), or edit (resume with a corrected label) — reusing the existing orchestrator
abstraction to actually continue the paused run rather than hand-rolling a second CRM-write code path.

Existing Systems Analysis
- Reusable:
  - `_route_after_enrich` (`graph.py`) **already implements this feature's Functional Requirements 1
    and 2 in full** — high-confidence leads already skip Human Review and reach `crm_write_stage`
    automatically; low-confidence leads already route to `human_review_stage` instead of
    `crm_write_stage`. `test_low_confidence_lead_routes_to_human_review_instead_of_crm_write` and
    `test_high_confidence_lead_skips_human_review` already cover this. **No edge change needed** — do
    not re-derive or duplicate this routing.
  - `ReviewSlice` (`state.py`) already has exactly the fields this feature needs
    (`queued`, `reviewer_action`, `corrected_intent_label`, `paused_at_stage`) — anticipated by
    Feature 01's bootstrap. No schema change needed on this slice.
  - `RunStatus.AWAITING_REVIEW` already exists in the enum but is never set by any code path today —
    this feature is what actually sets it.
  - `Stage` contract, `ToolRegistry`/`ScopedToolProxy`, `_make_node`'s trace-writing, and
    `PipelineRun`/`StageTrace` — the real `HumanReviewStage` and the resume path both go through these
    unchanged, per the "every stage implements the contract" and "execution data persists via
    PipelineRun/StageTrace" Key Decisions.
  - `StageTrace`'s existing input/output JSON-snapshot pattern (`_write_trace`) — generalized (not
    duplicated) into the new queue item's own resume snapshot, see New below.
  - `app/schemas/pipeline.py`'s `PipelineRunOut`/`StageTraceOut` — reused as the response shape for the
    reviewer-action endpoint's resumed-run result; no parallel response schema needed there.
  - `app/routers/leads.py`'s `get_session_factory()` dependency-override pattern — reused as-is for the
    new reviews router so tests can bind it to `db_session_factory` the same way `test_router_leads.py`
    already does.
- Duplication Risk Flagged: A naive implementation could reconstruct a paused run's state by
  re-reading and replaying its `StageTrace` rows (joining `intake_parsing`/`intent_classification`/
  `data_enrichment` output snapshots). **Rejected** — this would duplicate `StageTrace`'s
  execution-log role with a second, bespoke reconstruction path. Instead the queue item stores one
  `LeadPipelineState` JSON snapshot directly at pause time (see New below) — the same snapshot
  *technique* `StageTrace` already uses (`model_dump_json()`), applied at the run level instead of the
  per-stage level, not a new technique.
- Modify:
  - `graph.py` — swap the `review` stub for a real `HumanReviewStage`; add a dedicated node-wrapper for
    that one stage (persists the queue item + sets `AWAITING_REVIEW`, the same way `_make_node`'s
    exception branch already special-cases `FAILED`); add a second, small compiled graph
    (`crm_write_stage → notify_stage`) and a `resume_pipeline()` entry point paralleling `run_pipeline()`.
  - `state.py` — add `RunStatus.REJECTED`. A reviewer's rejection is a valid business outcome
    (spec's own edge case), and must not be recorded as `FAILED` — `FAILED` is reserved for stage
    execution failure per the existing (several-times-reworded) failure-handling Key Decision.
  - `main.py` — register the new reviews router, same one-line pattern as `leads.router`.
- New:
  - `app/orchestrator/stages/human_review.py` — `HumanReviewStage`, trivial body: given the
    classification already computed, return `ReviewSlice(queued=True, paused_at_stage="crm_write")`.
    No tool access needed (`allowed_tools = frozenset()`). Reason nothing existing fits: this is the
    first stage whose entire job is "signal that a human must act," not touch external state.
  - `app/models/review_queue.py` — `ReviewQueueItem` (new table). Reason nothing existing fits:
    `PipelineRun`/`StageTrace` are an execution *log*, not a reviewer *task queue* — they don't carry a
    resume payload, a reviewer decision, or a concurrency-safe claim mechanism, and stretching them to
    do so would overload their existing, already-documented role.
  - `app/schemas/review.py` — `ReviewActionRequest`, `ReviewQueueItemOut`.
  - `app/routers/reviews.py` — list/detail/action endpoints.
  - Alembic revision adding the `review_queue_item` table.
- Navigation Relationships Flagged: none this feature — it's backend-only, no UI surface yet (matches
  Feature 01's own precedent for this project's backend-first Tier 1 build order). Feature 08
  (Observability View) and Feature 11 (Per-Lead Audit Trail UI) will later need a direct link from a
  lead's detail view into its `ReviewQueueItem` when one exists — noted here, same as Feature 01 noted
  Feature 08's future link into `PipelineRun`/`StageTrace`, so those features' own plans don't have to
  rediscover it.

System Impact Map
```
FEATURE 06 — Human Review & Approval Gate
│
├── Backend
│   ├── app/orchestrator/stages/human_review.py (new) — real Stage body for the "review" slice
│   ├── app/orchestrator/graph.py (modify) — HumanReviewStage wired in; dedicated review-node wrapper
│   │     persists ReviewQueueItem + sets AWAITING_REVIEW; new build_resume_graph() +
│   │     resume_pipeline() (crm_write_stage → notify_stage only)
│   ├── app/orchestrator/state.py (modify) — RunStatus.REJECTED
│   ├── app/routers/reviews.py (new) — GET /reviews (pending list), GET /reviews/{run_id},
│   │     POST /reviews/{run_id}/action
│   ├── app/schemas/review.py (new) — ReviewActionRequest, ReviewQueueItemOut
│   └── main.py (modify) — registers reviews.router
│
├── Database
│   ├── app/models/review_queue.py (new) — ReviewQueueItem (run_id FK, lead_id, draft_intent_label,
│   │     confidence_score, status, reviewer_action, corrected_intent_label, state_snapshot,
│   │     created_at, actioned_at)
│   └── alembic/versions/<new> — creates review_queue_item table
│
├── Existing Systems (reused, not duplicated)
│   ├── app/orchestrator/contracts.py — Stage ABC, unchanged
│   ├── app/orchestrator/tool_scope.py — ToolRegistry/ScopedToolProxy, unchanged
│   ├── app/orchestrator/graph.py's _route_after_enrich — unchanged, already correct
│   ├── app/models/pipeline_run.py — PipelineRun.status set to REJECTED or the resumed run's outcome
│   └── app/schemas/pipeline.py — PipelineRunOut/StageTraceOut reused for the action-endpoint response
│
├── Navigation
│   └── none this feature (backend-only) — Feature 08/Feature 11 should link a lead's detail view to
│         its ReviewQueueItem when `status != "PENDING"` is not yet true (i.e. while queued) — flagged
│         for those features' own plans, not built here
│
└── AI
    └── none — this stage makes no model call; it consumes Feature 03's already-computed confidence
          score and label
```

Implementation Order (Dependency Graph)
1. **state.py — `RunStatus.REJECTED`**
   Purpose: a reviewer rejection needs a terminal status distinct from `FAILED`.
   Existing files: `backend/app/orchestrator/state.py`. New files: none.
   Dependencies: none.
   Requirements: add one enum member; no other slice change (`ReviewSlice` already fits).
   Validation: `test_orchestrator_state.py` round-trips a state with `run.status = RunStatus.REJECTED`.

2. **app/models/review_queue.py — `ReviewQueueItem` + Alembic revision**
   Purpose: persisted reviewer task queue with an embedded resume payload.
   Existing files: `backend/app/database/session.py` (Base). New files:
   `backend/app/models/review_queue.py`, one Alembic revision, updated `backend/app/models/__init__.py`.
   Dependencies: none.
   Requirements: columns — `id` (str uuid pk), `run_id` (FK → `pipeline_run.id`, unique — one queue item
   per run), `lead_id`, `draft_intent_label`, `confidence_score`, `status` (`"PENDING"` |
   `"ACTIONED"`, default `"PENDING"` — deliberately not a richer enum: the *outcome* lives in
   `reviewer_action`, `status` only gates the concurrency claim), `reviewer_action` (nullable —
   `"approve"|"reject"|"edit"`), `corrected_intent_label` (nullable), `state_snapshot` (Text — the full
   `LeadPipelineState.model_dump_json()` at pause time), `created_at`, `actioned_at` (nullable).
   Validation: `alembic upgrade head` succeeds on a fresh SQLite DB; a row round-trips via
   `SessionLocal`.

3. **app/orchestrator/stages/human_review.py — `HumanReviewStage`**
   Purpose: the real Stage body the graph currently stubs.
   Existing files: `backend/app/orchestrator/contracts.py` (Stage), `backend/app/orchestrator/state.py`
   (`ClassificationSlice`, `ReviewSlice`). New files:
   `backend/app/orchestrator/stages/human_review.py`.
   Dependencies: none beyond existing contracts.
   Requirements: `name = "human_review"`, `input_slice = "classification"`,
   `input_schema = ClassificationSlice`, `output_schema = ReviewSlice`,
   `allowed_tools = frozenset()`, `state_slice = "review"`. `run()` returns
   `ReviewSlice(queued=True, paused_at_stage="crm_write")` unconditionally — the routing decision that
   a review is needed was already made by `_route_after_enrich` before this stage ever runs.
   Validation: unit test (`test_stage_human_review.py`) asserts the output shape; no tool call, no
   exception path to cover (this stage cannot fail).

4. **graph.py — real stage wiring + dedicated review-node wrapper**
   Purpose: swap in `HumanReviewStage`; make queuing actually persist a `ReviewQueueItem` and set
   `RunStatus.AWAITING_REVIEW` (today `run.status` stays `RUNNING` even when `review.queued` is `True`
   — dead code path this feature is what activates).
   Existing files: `backend/app/orchestrator/graph.py`. New files: none.
   Dependencies: steps 2, 3.
   Requirements: `default_stages()["review"] = HumanReviewStage()`. Add
   `_make_human_review_node(stage, registry, session_factory)` — same shape as `_make_node` (calls
   `stage.run()`, writes the `StageTrace` row via the existing `_write_trace` helper, unchanged), but on
   success additionally: builds `state_snapshot = state.model_copy(update={"review": output}).model_dump_json()`,
   inserts one `ReviewQueueItem` row (`run_id=state.run.run_id`, `lead_id=state.run.lead_id`,
   `draft_intent_label=state.classification.intent_label`,
   `confidence_score=state.classification.confidence_score`, `state_snapshot=...`), and returns
   `{"review": output, "run": state.run.model_copy(update={"status": RunStatus.AWAITING_REVIEW})}`.
   Use this wrapper only for the `"human_review_stage"` node in `build_graph` — every other node keeps
   using the existing generic `_make_node` unchanged.
   Validation: extends the existing `test_low_confidence_lead_routes_to_human_review_instead_of_crm_write`
   -style graph test to additionally assert a `ReviewQueueItem` row exists with `status="PENDING"` and a
   parseable `state_snapshot`, and that `final.run.status == RunStatus.AWAITING_REVIEW`.

5. **graph.py — `build_resume_graph()` + `resume_pipeline()`**
   Purpose: the actual "resume" mechanism the feature spec assumes exists — built here as an extension
   of the existing orchestrator (same `_make_node`, same `Stage` instances, same trace-writing), not a
   bespoke code path in the API layer.
   Existing files: `backend/app/orchestrator/graph.py`. New files: none.
   Dependencies: step 4.
   Requirements: `build_resume_graph(stages, registry, session_factory)` wires a 2-node graph
   (`crm_write_stage → notify_stage → END`, both via the existing generic `_make_node`, reusing
   `stages["crm_write"]`/`stages["notification"]` from the same `default_stages()` dict — no new Stage
   instances). `resume_pipeline(run_id, state, *, graph=None, session_factory=...)` mirrors
   `run_pipeline()` but does **not** create a new `PipelineRun` row (the run already exists); it invokes
   the resume graph starting from the reconstructed `state` and, on completion, updates the existing
   `PipelineRun.status` the same way `run_pipeline()` already does. `build_production_resume_graph()`
   added alongside `build_production_graph()` for the router to use in production.
   Validation: a graph-level test invokes `resume_pipeline` directly with a hand-built post-review
   state (skipping the router) and asserts it reaches `crm_write` then `notify`, with `StageTrace` rows
   appended under the *same* `run_id` the original (paused) run used — proving continuity, not a second
   disconnected run.

6. **app/schemas/review.py + app/routers/reviews.py**
   Purpose: the reviewer-facing API surface.
   Existing files: `backend/app/schemas/pipeline.py` (`PipelineRunOut`, reused as the action endpoint's
   response body), `backend/app/routers/leads.py` (dependency-override pattern reused verbatim). New
   files: `backend/app/schemas/review.py`, `backend/app/routers/reviews.py`.
   Dependencies: steps 2, 5.
   Requirements:
   - `GET /reviews` → list `ReviewQueueItem` rows with `status="PENDING"`, shaped by
     `ReviewQueueItemOut` (id, run_id, lead_id, draft_intent_label, confidence_score, created_at) —
     deliberately excludes `state_snapshot` from the response (internal resume payload, not reviewer-
     facing data).
   - `GET /reviews/{run_id}` → single item, 404 if absent.
   - `POST /reviews/{run_id}/action` body: `ReviewActionRequest {action: "approve"|"reject"|"edit",
     corrected_intent_label: str | None}` (required when `action == "edit"`, validated in the route,
     not the schema, to keep the schema's field genuinely optional for approve/reject).
     Concurrency-safe claim: a single `UPDATE review_queue_item SET status='ACTIONED', reviewer_action=?,
     corrected_intent_label=?, actioned_at=? WHERE run_id=? AND status='PENDING'` (SQLAlchemy Core
     `update()...where(...)`, checked via the result's matched-row count) — if zero rows matched, return
     409 ("already actioned") without touching pipeline state. This is the direct implementation of the
     spec's "second concurrent action is rejected, not applied" edge case; a plain read-then-write would
     have a race window this closes.
     - `reject`: set `PipelineRun.status = RunStatus.REJECTED.value` directly (no resume graph
       invocation — the run is done). Return the updated `PipelineRunOut`.
     - `approve` / `edit`: reconstruct `LeadPipelineState.model_validate_json(item.state_snapshot)`;
       set `state.review = state.review.model_copy(update={"reviewer_action": action,
       "corrected_intent_label": corrected_intent_label})`; if `edit`, also overwrite
       `state.classification = state.classification.model_copy(update={"intent_label":
       corrected_intent_label})` — this is what makes the corrected label what Feature 05's CRM write
       reflects and what Feature 09's benchmark compares against, per the spec's own edge case. Call
       `resume_pipeline(run_id, state, session_factory=...)`. Return the resulting `PipelineRunOut`.
   Validation: `test_router_reviews.py` — approve resumes to CRM write with the original label; edit
   resumes with the corrected label reflected in the persisted `CrmWriteSlice`/trace; reject sets
   `REJECTED` with no `StageTrace` row added past `human_review`; a second action on an already-actioned
   `run_id` returns 409 and leaves the first action's effect unchanged.

7. **main.py — register `reviews.router`**
   Purpose: expose the new endpoints.
   Existing files: `backend/main.py`. New files: none.
   Dependencies: step 6.
   Requirements: one line, same pattern as `app.include_router(leads.router)`.
   Validation: `test_router_reviews.py`'s `client` fixture (already wired to the real `app` object in
   `conftest.py`) exercises the routes end-to-end.

Architecture Rule Changes
- [ ] "A paused pipeline run's resumable state is persisted as one full `LeadPipelineState` JSON
  snapshot on the owning feature's own domain row (here, `ReviewQueueItem.state_snapshot`), not
  reconstructed by replaying `StageTrace` rows — the same snapshot technique `StageTrace` already uses
  (`model_dump_json()`), applied at the run level instead of per-stage, whenever a future feature needs
  to pause and later resume a run." — Conflict check: none found. Does not compete with the existing
  "execution data persists via PipelineRun/StageTrace" Key Decision — that rule governs the execution
  *log*; this rule governs a domain-specific task queue's own resume payload, a genuinely different
  concern (see Duplication Risk Flagged above for why the two were not merged).
- [ ] "Resuming a paused run re-enters the same orchestrator abstraction — the existing `Stage`
  contract, `ToolRegistry`, and `_make_node` trace-writing — via a second, smaller compiled graph
  starting at the paused stage, rather than a bespoke code path in the API/router layer that calls
  stage tools directly." — Conflict check: none found. First time any code needs partial/resumed
  execution; extends, doesn't contradict, the existing per-stage contract/tool-scoping rules (the
  resume graph's nodes are the exact same `Stage` instances, so every existing boundary guarantee
  carries over unchanged).
- [ ] "`RunStatus.FAILED` is reserved for a stage raising during execution; a reviewer's explicit
  rejection is `RunStatus.REJECTED` — a distinct, valid terminal outcome, never recorded as `FAILED`."
  — Conflict check: the existing (twice-reworded) failure-handling Key Decision governs *when a stage
  raises vs. returns data*, which is a different axis (mid-stage behavior, not a human decision made
  after a stage already completed); no contradiction, this is a new, narrow addition alongside it, not
  a generalization of it.

Feature-Specific Requirements
- `ReviewQueueItem.status` is intentionally a two-value gate (`PENDING`/`ACTIONED`), not a richer
  status enum mirroring `reviewer_action` — the actual outcome (`approve`/`reject`/`edit`) already
  lives in `reviewer_action`; duplicating it into `status` would create two fields that must always
  agree with no added value. Stays local to this feature's own model, not a Key Decision.
- Exact response shapes (`ReviewQueueItemOut` field list, 409 error body) are this feature's own detail
  and stay in `implementation_plan.md` / this plan, not Key Decisions.

Risks
- Risk: A stale `state_snapshot` diverges from what the pipeline would have produced today (e.g. if a
  tool's behavior changed between pause and resume). Mitigation: out of scope for this round — the
  spec doesn't require replaying "as if run today," only resuming *this* lead's paused state as it was
  captured; note this as an accepted limitation, not a bug.
- Risk: The concurrency-safe claim (`UPDATE ... WHERE status='PENDING'`) could be bypassed by a caller
  that reads the item first and assumes it's actionable without going through the endpoint's atomic
  update. Mitigation: the endpoint never does a separate SELECT-then-branch on `status`; the `UPDATE`'s
  matched-row-count is the only authority for whether this action is the first one applied.
- Risk: `resume_pipeline` accidentally creating a second `PipelineRun` row for the same lead (duplicate
  run history). Mitigation: `resume_pipeline` takes an existing `run_id` and only ever updates that row;
  unlike `run_pipeline`, it must never call `db.add(PipelineRun(...))` — covered explicitly by step 5's
  validation.
- Risk: Editing the classification label without also adjusting `confidence_score` could make a
  corrected lead look like a low-confidence auto-decision to a later reader (e.g. Feature 09's
  benchmark). Mitigation: leave `confidence_score` as originally computed and rely on
  `review.reviewer_action == "edit"` as the explicit signal that the label was human-corrected — Feature
  09's own plan should read `review.corrected_intent_label`/`reviewer_action`, not re-infer correction
  from a confidence mismatch (flagged here for that plan to pick up).

Acceptance Criteria
- [ ] A high-confidence lead proceeds automatically through to CRM Write with no `ReviewQueueItem`
  created (already true today via `_route_after_enrich`; this plan must not regress it).
- [ ] A low-confidence lead creates exactly one `ReviewQueueItem` (`status="PENDING"`) and the run's
  `PipelineRun.status` becomes `AWAITING_REVIEW`; no `StageTrace` row past `human_review` exists yet.
- [ ] `POST /reviews/{run_id}/action` with `approve` resumes the same `run_id` into `crm_write` then
  `notify` using the original `intent_label`, and `PipelineRun.status` reaches its normal post-write
  terminal value (`RUNNING`/`FAILED` per existing CRM-write semantics — resume doesn't change that
  contract).
- [ ] `action=edit` resumes with `corrected_intent_label` reflected in `state.classification.intent_label`
  by the time `HubSpotCrmWriteStage` runs.
- [ ] `action=reject` sets `PipelineRun.status = REJECTED`, performs no CRM write, and adds no
  `StageTrace` row past `human_review`.
- [ ] A second `POST .../action` call on an already-actioned `run_id` returns 409 and does not alter
  the first action's persisted outcome.

Validation Requirements
Step 7 must specifically verify (beyond this plan's own Acceptance Criteria): (1) the concurrency claim
is exercised with two sequential calls in a test (true concurrent threads aren't necessary — the
atomic `UPDATE ... WHERE status='PENDING'` is what's being proven, and a second sequential call already
exercises the "already actioned" branch); (2) `resume_pipeline` never creates a second `PipelineRun`
row — assert exactly one row exists for the `lead_id` after approve/edit; (3) grep confirms
`HumanReviewStage.allowed_tools` stays `frozenset()` (this stage should never gain tool access — if a
future change adds one, that's a signal review logic is creeping into what should stay a pure gate).

Predicted Footprint
Files predicted to change: 11 (state.py, graph.py, main.py modified; review_queue.py, human_review.py,
schemas/review.py, routers/reviews.py, one Alembic revision, test_stage_human_review.py,
test_router_reviews.py new; test_orchestrator_graph.py and test_orchestrator_state.py modified — 13
total including test modifications).
Systems predicted to touch: Backend orchestrator package (graph.py, state.py, new stage), database
(new model + migration), routing/schema layer, main app wiring.

--- filled in later, by Step 7 / CD-4, once implementation is verified ---
Actual Footprint
Files actually changed: [pending Step 6/7]
Deviations from plan: [pending Step 6/7]
Rework required: [pending Step 6/7]
