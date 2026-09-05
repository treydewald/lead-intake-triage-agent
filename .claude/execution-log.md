# Execution Log — Lead Intake Triage Agent

Full process: `docs/plan-execute-review.md` §Execute Phase. One entry per Execute-phase step
(Step 6, and any Step 9 repair pass).

---

## 2026-09-04 — Step 6: Feature 01 (Pipeline Orchestration Layer), Group_F01

Implemented per `architecture-plan-feature-01.md`'s Implementation Order: contracts.py →
state.py → tool_scope.py/errors.py → pipeline_run.py models + Alembic migration → graph.py.

**Files modified:**
- `backend/app/orchestrator/contracts.py` (new) — `Stage` ABC contract
- `backend/app/orchestrator/state.py` (new) — `LeadPipelineState` + 6 per-stage slices
- `backend/app/orchestrator/tool_scope.py` (new) — `ToolRegistry`/`ScopedToolProxy`
- `backend/app/orchestrator/errors.py` (new) — `OutOfScopeToolError`, `StageExecutionError`, `StateValidationError`
- `backend/app/orchestrator/graph.py` (new) — LangGraph `StateGraph` wiring, stub stages for Features 02-07, `run_pipeline` entry point
- `backend/app/orchestrator/__init__.py` (modified) — package public exports
- `backend/app/models/pipeline_run.py` (new) — `PipelineRun`, `StageTrace` SQLAlchemy models
- `backend/app/models/__init__.py` (modified) — registers models for Alembic autogenerate
- `backend/app/schemas/pipeline.py` (new) — trigger/query Pydantic schemas
- `backend/alembic/versions/245c694fed3d_add_pipeline_run_and_stage_trace_tables.py` (new)
- `backend/app/tests/test_orchestrator_contracts.py`, `test_orchestrator_state.py`,
  `test_orchestrator_tool_scope.py`, `test_orchestrator_graph.py`, `test_pipeline_run_models.py` (new)
- `backend/app/tests/conftest.py` (modified) — added `db_session_factory` fixture (isolated in-memory SQLite per test)

**Diff size:** ~640 lines added across 16 files (8 new source modules, 6 new test files, 2 modified `__init__.py`/`conftest.py`)
**Validation:** PASS — see `.claude/validation-results.md`
**Status:** approved — all 5 of Feature 01's acceptance criteria verified by test; `implementation_plan.md` marked Feature 01 `COMPLETED`, Group_F01 `COMPLETED`

---

## 2026-09-04 — Step 6: Feature 02 (Intake Parsing & Normalization Stage), Group_F02

Implemented per `architecture-plan-feature-02.md`'s Implementation Order: `stages/intake.py` →
`schemas/pipeline.py` additions → `routers/leads.py` → `graph.py` stub-swap → `main.py`
registration.

**Files modified:**
- `backend/app/orchestrator/stages/__init__.py` (new) — package export
- `backend/app/orchestrator/stages/intake.py` (new) — `IntakeStage`: web-form field mapping,
  email header/body extraction (stdlib `email` module, never raises), callback transcript phone
  extraction, phone/email normalization, empty-message/low-identifiability flagging
- `backend/app/routers/leads.py` (new) — `POST /leads/webform`, `/leads/email`, `/leads/callback`;
  each builds the initial `LeadPipelineState.intake`, calls `run_pipeline()`, returns
  `PipelineRunOut`
- `backend/app/schemas/pipeline.py` (modified) — added `EmailIntakeRequest`, `CallbackIntakeRequest`
- `backend/app/orchestrator/graph.py` (modified) — `default_stages()["intake"]` now returns a real
  `IntakeStage()` instead of `_StubStage`
- `backend/main.py` (modified) — registered `leads.router`
- `backend/app/tests/test_stage_intake.py` (new) — 9 tests covering all channels + edge cases
- `backend/app/tests/test_router_leads.py` (new) — 3 integration tests (one per channel), via
  `TestClient` with `get_session_factory` overridden to the isolated test DB
- `backend/app/tests/test_orchestrator_graph.py` (modified) — added one graph-level test that a
  web-form payload through `default_stages()`'s real `IntakeStage` reaches `classify_stage` with
  `state.intake` normalized (classification itself still stubbed, per plan)

**Diff size:** ~330 lines added across 9 files (3 new source modules, 2 new test files, 4 modified)
**Validation:** PASS — see `.claude/validation-results.md` (29/29 tests passing, first run clean)
**Status:** approved — all 7 of Feature 02's roadmap acceptance criteria verified by test, plus the
architecture plan's boundary-test and stub-swap criteria; `implementation_plan.md` marked Feature 02
`COMPLETED`, Group_F02 `COMPLETED`

---

## 2026-09-04 — Step 6: Feature 03 (Intent Classification Stage), Group_F03

Implemented per `architecture-plan-feature-03.md`'s Implementation Order: `contracts.py`
(`input_slice`/`effective_input_slice`) → `orchestrator/tools/` package (`ollama_tools.py`,
`__init__.py`) → `stages/intent_classification.py` → `graph.py` (`_make_node`, `default_stages()`,
`build_production_graph()`).

**Files modified:**
- `backend/app/orchestrator/contracts.py` (modified) — `Stage` gains `input_slice: ClassVar[str |
  None] = None` and the `effective_input_slice` property (`input_slice or state_slice`)
- `backend/app/orchestrator/tools/__init__.py` (new) — `register_default_tools(registry, settings)`:
  constructs one `ollama.Client`, binds `classify_intent` via `functools.partial`, registers it as
  `"ollama_classify"`
- `backend/app/orchestrator/tools/ollama_tools.py` (new) — `classify_intent(client, model, lead_text)`:
  one `client.chat()` call, `format="json"`, `temperature=0`, fixed `{buyer, browser, spam}` label
  set in the system prompt; no validation/retry logic (kept in the stage)
- `backend/app/orchestrator/stages/intent_classification.py` (new) — `IntentClassificationStage`:
  empty-message short-circuit (`"empty_message_short_circuit"` sentinel, no tool call), bounded
  retry-once-then-fail-closed loop (`"classification_failed"` sentinel on either exhausted-exception
  or exhausted-invalid-response), never raises for either named failure mode
- `backend/app/orchestrator/graph.py` (modified) — `_make_node` reads
  `stage.effective_input_slice` instead of `stage.state_slice`; `default_stages()["classification"]`
  now returns a real `IntentClassificationStage()`; `build_production_graph()` constructs a
  `ToolRegistry` and calls `register_default_tools()` before compiling, instead of passing an
  always-empty registry
- `backend/app/tests/test_orchestrator_contracts.py` (modified) — 2 new tests for
  `effective_input_slice` fallback/override
- `backend/app/tests/test_orchestrator_tools.py` (new) — 3 tests: `classify_intent`'s JSON parsing
  and deterministic call options (fake `.chat()` double), `register_default_tools` registers the
  expected tool name
- `backend/app/tests/test_stage_intent_classification.py` (new) — 8 tests covering all Feature 03
  acceptance criteria (buyer/empty/failure/invalid-label/retry-recovers/boundary/determinism)
- `backend/app/tests/test_orchestrator_graph.py` (modified) — updated the existing
  `test_default_stages_web_form_payload_reaches_classify_with_normalized_intake` to register a fake
  `"ollama_classify"` tool so it exercises the real stage's *success* path (previously passed for
  the old, no-longer-true reason: an unimplemented stub); added 2 new graph-level tests proving a
  low-confidence and a `classification_failed` result (both from the real, non-stub stage) reach
  Human Review via the existing, unmodified `_route_after_enrich`, with `enrichment` and `review`
  faked since Features 04/06 aren't built yet

**Diff size:** ~370 lines added/changed across 8 files (3 new source modules, 2 new test files, 3
modified)
**Validation:** PASS — see `.claude/validation-results.md` (44/44 tests passing; grep-verified no
direct `ollama` import in the stage module; real end-to-end smoke call against the local
`llama3.2:3b` daemon returned a valid, in-set label)
**Status:** approved — all 5 of Feature 03's roadmap acceptance criteria verified by test, plus the
architecture plan's tool-scoping-discipline and routing-reuse criteria; `implementation_plan.md`
marked Feature 03 `COMPLETED`, Group_F03 `COMPLETED`

---

## 2026-09-04 — Step 6: Feature 04 (Data Enrichment Stage), Group_F04

Implemented per `architecture-plan-feature-04.md`'s Implementation Order: `state.py`
(`EnrichmentSlice` extension) → `tools/hubspot_tools.py` + `tools/__init__.py` → `stages/
data_enrichment.py` → `graph.py` stub-swap.

**Files modified:**
- `backend/app/orchestrator/state.py` (modified) — `EnrichmentSlice` gains `attempted_fields`,
  `match_confidence`, `conflicts`, `lookup_error`, alongside the existing `resolved_fields`/`sources`
- `backend/app/orchestrator/tools/hubspot_tools.py` (new) — `search_contact(client, base_url, token,
  *, phone=None, email=None, name=None)`: one HubSpot CRM Search API call (`EQ` filter on phone/email
  when given, else `CONTAINS_TOKEN` on name), returns the first match's `properties` or `None`; no
  confidence logic (kept in the stage, thin-tool principle)
- `backend/app/orchestrator/tools/__init__.py` (modified) — `register_default_tools` additionally
  constructs one shared `httpx.Client(timeout=5.0)` and registers `search_contact` as
  `"hubspot_search_contact"`
- `backend/app/orchestrator/stages/data_enrichment.py` (new) — `DataEnrichmentStage`: detects missing
  `name`/`phone`/`email` fields, picks exact-key (phone/email, `match_confidence=1.0`) or fuzzy-name
  (`difflib.SequenceMatcher`, `0.85` threshold) query, merges only fields Intake left null, records
  conflicts instead of overwriting, encodes a tool exception as `lookup_error` rather than raising
- `backend/app/orchestrator/graph.py` (modified) — `default_stages()["enrichment"]` now returns a
  real `DataEnrichmentStage()` instead of `_StubStage`
- `backend/app/tests/test_orchestrator_state.py` (modified) — 1 new test for `EnrichmentSlice`'s
  extended default shape
- `backend/app/tests/test_orchestrator_tools.py` (modified) — 5 new tests: `search_contact`'s
  exact-match hit / no-result / HTTP-error-passthrough / fuzzy-name-filter behavior (fake `httpx`-shaped
  client double, no mocking library), plus `register_default_tools` registers
  `"hubspot_search_contact"`
- `backend/app/tests/test_orchestrator_tool_scope.py` (modified) — 1 new boundary test: the real
  `DataEnrichmentStage`'s scoped proxy can call `hubspot_search_contact` but raises
  `OutOfScopeToolError` on `hubspot_write`
- `backend/app/tests/test_stage_data_enrichment.py` (new) — 8 tests covering all Feature 04
  acceptance criteria (exact-match resolve, no-op pass-through, lookup failure, conflict recorded not
  merged, fuzzy match below/at-or-above threshold, no-match, no-identifying-field)
- `backend/app/tests/test_orchestrator_graph.py` (modified) — updated the existing
  `test_default_stages_web_form_payload_reaches_classify_with_normalized_intake` (renamed to
  `..._reaches_enrichment_with_normalized_intake`) to register a fake `"hubspot_search_contact"` tool
  that asserts it's never called (all fields already present, so real `DataEnrichmentStage` is a
  no-op) — the run now halts at the still-stubbed `hubspot_crm_write`, not `data_enrichment`

**Diff size:** ~330 lines added/changed across 8 files (2 new source modules, 1 new test file, 5
modified)
**Validation:** PASS — see `.claude/validation-results.md` (59/59 tests passing, first run clean;
grep-verified no direct `httpx` import in the stage module)
**Status:** approved — all 5 of Feature 04's roadmap acceptance criteria verified by test, plus the
architecture plan's tool-scoping-discipline and boundary-test criteria; `implementation_plan.md`
marked Feature 04 `COMPLETED`, Group_F04 `COMPLETED`

---

## 2026-09-04 — Step 6: Feature 05 (HubSpot CRM Write Stage), Group_F05

Implemented per `architecture-plan-feature-05.md`'s Implementation Order (7 steps): `contracts.py`
(`input_slices`) → `state.py` (`CrmWriteSlice` extended + `MergedIntakeEnrichment`) → `graph.py`'s
`_make_node` (generic multi-slice branch) → `hubspot_tools.py` (`write_contact`, `HubSpotWriteError`)
→ `tools/__init__.py` (registers `"hubspot_write"`) → `stages/hubspot_crm_write.py` (new
`HubSpotCrmWriteStage`) → `graph.py`'s `default_stages()["crm_write"]` swap.

**Files modified:**
- `backend/app/orchestrator/contracts.py` (modified) — `Stage` gains `input_slices:
  ClassVar[tuple[str, ...] | None] = None`, additive companion to the existing singular
  `input_slice`; unused by any existing stage
- `backend/app/orchestrator/state.py` (modified) — `CrmWriteSlice` gains `dedupe_key_used`,
  `dedupe_uncertain`, `retry_count`, plus a corrected `write_status` doc-comment; new
  `MergedIntakeEnrichment(intake: IntakeSlice, enrichment: EnrichmentSlice)` read-time merge schema
- `backend/app/orchestrator/graph.py` (modified) — `_make_node` gains a generic branch: when
  `stage.input_slices` is set, builds `stage.input_schema(**{name: getattr(state, name) for name in
  stage.input_slices})` instead of the single-slice `effective_input_slice` lookup;
  `default_stages()["crm_write"]` now returns a real `HubSpotCrmWriteStage()`
- `backend/app/orchestrator/tools/hubspot_tools.py` (modified) — new `HubSpotWriteError` and
  `write_contact(client, base_url, token, *, phone=None, email=None, properties, max_retries=3,
  base_delay=0.5, sleep=time.sleep)`: each retry re-runs the whole attempt (dedupe lookup + write,
  not just the write); dedupe lookup reuses `search_contact` directly (unmodified); a match is
  addressed for PATCH via HubSpot's `idProperty` upsert query parameter (the dedupe key's own value
  as the path segment) rather than a second lookup to recover the internal HubSpot id — this keeps
  `search_contact`'s existing return shape (properties only, no id) completely untouched; no
  match → POST create; neither phone nor email given → POST directly, `dedupe_uncertain=True`, zero
  lookup calls; 429/5xx retries with backoff up to `max_retries`; 401/403 raises immediately, no
  retry; other 4xx raises immediately, no retry; retries exhausted raises
- `backend/app/orchestrator/tools/__init__.py` (modified) — `register_default_tools` additionally
  registers `write_contact` as `"hubspot_write"` on the same shared `httpx.Client` already
  constructed for `"hubspot_search_contact"`
- `backend/app/orchestrator/stages/hubspot_crm_write.py` (new) — `HubSpotCrmWriteStage`: reads
  `input_slices = ("intake", "enrichment")`, builds `properties` from intake-primary/
  enrichment-fallback fields, calls `tools.call("hubspot_write", ...)` with **no** try/except (a
  `HubSpotWriteError` propagates straight out of `run()`, per the reworded Key Decision)
- `backend/app/tests/test_orchestrator_contracts.py` (modified) — 1 new test: `input_slices`
  defaults to `None`
- `backend/app/tests/test_orchestrator_state.py` (modified) — 2 new tests: `CrmWriteSlice`'s
  extended default shape, `MergedIntakeEnrichment` construction
- `backend/app/tests/test_orchestrator_graph.py` (modified) — 3 new tests: `_make_node`'s generic
  multi-slice merge branch (independent minimal fake stage), a real-stage chained success path
  reaching `notify_stage` (Notification faked, per Feature 04's precedent), a real-stage
  `HubSpotWriteError` halting the run `FAILED` at `"hubspot_crm_write"`. The existing
  `test_default_stages_web_form_payload_reaches_enrichment_with_normalized_intake` needed **no**
  change — with `"hubspot_write"` unregistered in that test's registry, the real stage's
  `tools.call` now raises `KeyError` instead of hitting a `_StubStage`'s `NotImplementedError`,
  producing the identical expected outcome (`FAILED` at `"hubspot_crm_write"`)
- `backend/app/tests/test_orchestrator_tools.py` (modified) — 1 new test (`register_default_tools`
  registers `"hubspot_write"` distinct from `"hubspot_search_contact"`) + 7 new `write_contact` unit
  tests (create, update, 429-then-success retry, retries-exhausted, 401 immediate-raise, other-4xx
  immediate-raise, no-identifying-field)
- `backend/app/tests/test_orchestrator_tool_scope.py` (modified) — 1 new boundary test: the real
  `HubSpotCrmWriteStage`'s scoped proxy can call `hubspot_write` but raises `OutOfScopeToolError` on
  `hubspot_search_contact`
- `backend/app/tests/test_stage_hubspot_crm_write.py` (new) — 5 tests: successful create, retried-
  then-succeeded write reflected verbatim, `run()` re-raises a tool exception without catching it,
  enrichment-fallback field used when intake left it null, intake field takes priority over
  enrichment's fallback

**Diff size:** ~470 lines added/changed across 10 files (2 new source modules, 1 new test file, 7
modified)
**Validation:** PASS — see `.claude/validation-results.md` (79/79 tests passing, first run clean;
grep-verified no direct `httpx` import and no `try`/`except` around the tool call in the new stage
module)
**Status:** approved — all 5 of Feature 05's roadmap acceptance criteria verified by test, plus the
architecture plan's tool-scoping-discipline, multi-slice-merge, and reworded-failure-handling
criteria; `implementation_plan.md` marked Feature 05 `COMPLETED`, Group_F05 `COMPLETED`

---

## 2026-09-04 — Step 6: Feature 06 (Human Review & Approval Gate), Group_F06

Implemented per `architecture-plan-feature-06.md`'s Implementation Order (7 steps): `state.py`
(`RunStatus.REJECTED`) → `models/review_queue.py` + Alembic revision → `stages/human_review.py`
(`HumanReviewStage`) → `graph.py` (real stage wired in + `_make_human_review_node`) → `graph.py`
(`build_resume_graph()` + `resume_pipeline()` + `build_production_resume_graph()`) →
`schemas/review.py` + `routers/reviews.py` → `main.py` router registration.

**Files modified:**
- `backend/app/orchestrator/state.py` (modified) — `RunStatus` gains `REJECTED`, a terminal outcome
  distinct from `FAILED` for an explicit reviewer rejection
- `backend/app/models/review_queue.py` (new) — `ReviewQueueItem`: `run_id` (unique FK →
  `pipeline_run.id`), `lead_id`, `draft_intent_label`, `confidence_score`, `status`
  (`PENDING`/`ACTIONED`), `reviewer_action`, `corrected_intent_label`, `state_snapshot` (full
  `LeadPipelineState` JSON at pause time), `created_at`, `actioned_at`
- `backend/app/models/__init__.py` (modified) — registers `ReviewQueueItem` for Alembic autogenerate
- `backend/alembic/versions/68de6a50cacb_add_review_queue_item_table.py` (new)
- `backend/app/orchestrator/stages/human_review.py` (new) — `HumanReviewStage`: `input_slice =
  "classification"`, `allowed_tools = frozenset()`, unconditionally returns
  `ReviewSlice(queued=True, paused_at_stage="crm_write")` — the routing decision was already made by
  `_route_after_enrich`
- `backend/app/orchestrator/graph.py` (modified) — `default_stages()["review"]` now returns a real
  `HumanReviewStage()`; new `_make_human_review_node` (same shape as `_make_node`, but on success also
  persists a `ReviewQueueItem` with a full-state resume snapshot and moves `run.status` to
  `AWAITING_REVIEW`); new `build_resume_graph()` (2-node `crm_write_stage -> notify_stage`, reusing
  the same `Stage` instances and the generic `_make_node`), `build_production_resume_graph()`, and
  `resume_pipeline()` (mirrors `run_pipeline()` but never creates a new `PipelineRun` row, and resets
  `run.status` to `RUNNING` before invoking — a gap caught during validation, see
  `.claude/validation-results.md`)
- `backend/app/schemas/review.py` (new) — `ReviewActionRequest` (`action`, optional
  `corrected_intent_label`), `ReviewQueueItemOut` (excludes `state_snapshot`/`status`/`reviewer_action`)
- `backend/app/routers/reviews.py` (new) — `GET /reviews`, `GET /reviews/{run_id}`, `POST
  /reviews/{run_id}/action`; the action endpoint's claim is a single atomic `UPDATE ... WHERE
  status='PENDING'` (SQLAlchemy Core), never a SELECT-then-branch on `status`, so a second concurrent
  action gets 409 from the update's zero matched rows; `reject` sets `RunStatus.REJECTED` directly (no
  resume); `approve`/`edit` reconstruct `LeadPipelineState` from the snapshot and call
  `resume_pipeline()`. Also adds `get_resume_graph_factory`, a `get_session_factory`-style dependency
  making the resume graph pluggable in tests (test-only need, not in the original architecture plan)
- `backend/main.py` (modified) — registered `reviews.router`
- `backend/app/tests/test_stage_human_review.py` (new) — 2 tests: output shape, no-tool-access
- `backend/app/tests/test_router_reviews.py` (new) — 8 tests: list/detail/404, approve (original
  label), edit (corrected label + required-field 422), reject (status + no further trace), 409 on a
  second action
- `backend/app/tests/test_orchestrator_graph.py` (modified) — extended
  `test_high_confidence_lead_skips_human_review` (asserts zero `ReviewQueueItem` rows) and
  `test_low_confidence_lead_routes_to_human_review_instead_of_crm_write` (asserts `PENDING`
  `ReviewQueueItem` + `AWAITING_REVIEW`); added
  `test_resume_pipeline_continues_paused_run_through_crm_write_and_notify` (proves resume continuity:
  same `run_id`, appended `StageTrace` rows, exactly one `PipelineRun` row)
- `backend/app/tests/test_orchestrator_state.py` (modified) — 1 new test: `RunStatus.REJECTED`
  round-trips distinctly from `FAILED`

**Diff size:** ~430 lines added/changed across 12 files (5 new source modules incl. migration, 2 new
test files, 5 modified)
**Validation:** PASS — see `.claude/validation-results.md` (91/91 tests passing; grep-verified
`HumanReviewStage.allowed_tools` stays empty)
**Status:** approved — all of Feature 06's Acceptance Criteria verified by test, including the
resume-continuity and concurrency-safe-claim requirements the architecture plan specifically called
out for Step 7 to check; `implementation_plan.md` marked Feature 06 `COMPLETED`, Group_F06
`COMPLETED`

---

## 2026-09-04 — Step 6: Feature 07 (Outcome Notification — In-App), Group_F07

Implemented per `architecture-plan-feature-07.md`'s Implementation Order (7 steps): `models/
notification.py` + Alembic revision → `stages/outcome_notification.py` (`OutcomeNotificationStage`) →
`persist_outcome_notification()` helper in `graph.py` → wired into the three direct call sites
(`_make_node`'s except block, `_make_human_review_node`, `reviews.py`'s reject branch) →
`RunStatus.COMPLETED` gap closed in `run_pipeline`/`resume_pipeline` → `default_stages()` swap →
`schemas/notification.py` + `routers/notifications.py`.

**Files modified:**
- `backend/app/orchestrator/state.py` (modified) — `NotificationSlice` gains `message`/`detail_link`;
  new `NotificationInput` merge schema (`run`+`intake`+`crm_write`), same pattern as
  `MergedIntakeEnrichment`
- `backend/app/orchestrator/stages/outcome_notification.py` (new) — `OutcomeNotificationStage`:
  `input_slices = ("run", "intake", "crm_write")`, `allowed_tools = frozenset()`; maps `run.status` to
  one of `auto_processed`/`awaiting_review`/`rejected`/`failed`, builds `message` (falling back
  name→phone→email→lead_id when the lead has no name) and `detail_link` (`/leads/{lead_id}` or
  `/reviews/{run_id}` per the new routing-convention Key Decision)
- `backend/app/models/notification.py` (new) — `Notification`: `run_id` (FK → `pipeline_run.id`,
  indexed, **not** unique — a run can produce more than one notification over its lifetime),
  `lead_id`, `outcome_type`, `message`, `detail_link`, `created_at`. No addressee field — this is a
  single-tenant app with no `User`/auth model anywhere in the codebase
- `backend/app/models/__init__.py` (modified) — registers `Notification` for Alembic autogenerate
- `backend/alembic/versions/5f3cbe979b96_add_notification_table.py` (new)
- `backend/app/orchestrator/graph.py` (modified) — new `persist_outcome_notification()` helper (the
  shared "resolve merged input, call stage, write trace, save Notification row" logic used outside the
  normal per-node flow); `_make_node()` gains an optional `notification_stage` parameter, called from
  its except block on a stage failure (wrapped in its own try/except — never masks the original
  failure); `_make_human_review_node()` likewise fires the awaiting-review notification after queueing;
  new `_mark_completed_if_still_running()` closes the pre-existing gap where `RunStatus.COMPLETED` was
  never assigned anywhere — `run_pipeline()`/`resume_pipeline()` now apply it to `final_state` before
  persisting; `default_stages()["notification"]` now returns a real `OutcomeNotificationStage()`. The
  crm_write-success (`auto_processed`) outcome still fires through the existing, unmodified
  `notify_stage` graph node — zero graph edges changed
- `backend/app/routers/reviews.py` (modified) — the reject branch now parses `state_snapshot`, sets
  `run.status = REJECTED`, and calls `persist_outcome_notification()` directly (wrapped in try/except)
  — reject never touched the orchestrator at all before this
- `backend/app/schemas/notification.py` (new) — `NotificationOut`
- `backend/app/routers/notifications.py` (new) — `GET /notifications` (list, newest first; no
  read/unread state — not in the spec)
- `backend/main.py` (modified) — registered `notifications.router`
- `backend/app/tests/test_stage_outcome_notification.py` (new) — 6 tests: all four outcome types, the
  name→phone→email→lead_id message fallback, no-tool-access
- `backend/app/tests/test_router_notifications.py` (new) — 2 tests: newest-first listing, empty list
- `backend/app/tests/test_orchestrator_state.py` (modified) — 3 new tests: `RunStatus.COMPLETED`
  round-trips, `NotificationSlice` defaults, `NotificationInput` construction
- `backend/app/tests/test_orchestrator_graph.py` (modified) — updated 5 existing tests whose
  assertions encoded the pre-fix behavior (`RunStatus.RUNNING` after success → `COMPLETED`; `"notify"
  not in calls` on the failure/awaiting-review paths → now present; trace lists gain an
  `outcome_notification` entry on those paths)
- `backend/app/tests/test_router_reviews.py` (modified) — the `_paused_stages` notification fake now
  returns a realistic `NotificationSlice` instead of an all-`None` one (the all-`None` version silently
  failed the `Notification` table's `NOT NULL outcome_type` on every test using it — harmless since
  notification errors are swallowed by design, but noisy); updated the approve test's expected status
  to `COMPLETED`; renamed/rewrote the reject test (`test_reject_sets_rejected_status_and_creates_a_
  rejected_notification`) to assert the two `outcome_notification` traces (pause + reject) and the two
  `Notification` rows (`awaiting_review` then `rejected`) now produced

**Diff size:** ~470 lines added/changed across 14 files (6 new source modules incl. migration, 2 new
test files, 6 modified)
**Validation:** PASS — see `.claude/validation-results.md` (102/102 tests passing; grep-verified
`OutcomeNotificationStage.allowed_tools` stays empty; manually traced all four outcome paths to confirm
no code path can invoke `persist_outcome_notification` and the `notify_stage` graph node for the same
transition)
**Status:** approved — all of Feature 07's Acceptance Criteria verified by test, including the
pre-existing `RunStatus.COMPLETED` gap this feature's own outcome-typing requirement exposed and fixed;
`implementation_plan.md` marked Feature 07 `COMPLETED`, Group_F07 `COMPLETED`

---

## 2026-09-04 — Step 6: Feature 08 (Observability / Monitoring View), Group_F08

Implemented per `architecture-plan-feature-08.md`'s 8-step Implementation Order: `PipelineRun` columns
+ migration → `STAGE_ORDER` export + `run_pipeline()` denormalization write → backend schemas →
`GET /leads`/`GET /leads/{lead_id}` → backend tests → frontend API client/`stageOrder.ts` →
`LeadListPage`/`LeadDetailPage` + routing/nav → frontend smoke test. This project's first real
frontend surface beyond the Step 4 bootstrap scaffold.

**Files modified:**
- `backend/app/models/pipeline_run.py` (modified) — `PipelineRun` gains `source_channel: str | None`,
  `confidence_score: float | None`, both nullable, denormalized read-optimization columns
- `backend/alembic/versions/9217c457cc82_add_pipeline_run_list_columns.py` (new) — autogenerated,
  applied to the dev DB (`alembic upgrade head`)
- `backend/app/orchestrator/graph.py` (modified) — `_STAGE_ORDER` renamed to `STAGE_ORDER` (exported,
  no longer module-private; all internal references updated); `run_pipeline()`'s final-commit block
  now also sets `run_row.source_channel`/`run_row.confidence_score` from `final_state.intake`/
  `final_state.classification` alongside the existing `.status` write. `resume_pipeline()` deliberately
  left unchanged — the row's values were already set by the original `run_pipeline()` call before the
  run paused
- `backend/app/schemas/pipeline.py` (modified) — `LeadListItemOut`, `LeadListOut`, `StageDetailOut`,
  `LeadDetailOut`; `display_status_for()`/`run_status_for_display()`, the post-persistence status
  mapping this feature owns (kept separate from Feature 07's notification-time map — see
  `.claude/portfolio-reference.md`'s Key Decisions)
- `backend/app/routers/leads.py` (modified) — `GET /leads` (filter by `status`/`source_channel`, sort
  by `created_desc`/`confidence_asc`/`confidence_desc`, paginated, all via SQL `WHERE`/`ORDER BY`, no
  Python-side filtering) and `GET /leads/{lead_id}` (looks up by `lead_id`, 404s if missing, iterates
  `STAGE_ORDER` building one `StageDetailOut` per canonical stage — any stage with no matching
  `StageTrace` row marked `NOT_YET_RUN` — and derives `failed_stage`/`error` from whichever trace has
  `status == "FAILED"`, since `PipelineRun` itself carries no such column)
- `backend/app/tests/test_router_leads_list.py` (new) — 9 tests: list pagination, status/source-channel
  filtering (plus a 422 on an unknown status), confidence sorting, detail view for
  completed/awaiting-review/failed leads, decision-payload exactness, unknown-`lead_id` 404
- `frontend/src/lib/stageOrder.ts` (new) — static mirror of the backend's `STAGE_ORDER` (6 keys +
  human-readable labels); TypeScript can't import the Python constant, so this is a deliberately
  duplicated static list, not a duplicated system
- `frontend/src/lib/api.ts` (modified) — `listLeads(params)`/`getLeadDetail(leadId)` + response types
- `frontend/src/pages/LeadListPage.tsx` (new) — filterable (status, source channel), sortable
  (confidence), paginated table with a status badge per row, linking to each lead's detail page
- `frontend/src/pages/LeadDetailPage.tsx` (new) — full 6-stage timeline (`STAGE_ORDER` order),
  visually distinguishing COMPLETED/FAILED/NOT_YET_RUN, a failed-stage banner, an in-progress banner,
  and each completed stage's parsed decision payload rendered verbatim
- `frontend/src/pages/LeadListPage.test.tsx` (new) — 2 tests: renders API-returned leads, empty state
- `frontend/src/App.tsx` (modified) — added `leads` and `leads/:leadId` routes; the existing
  bootstrap `index` route (`HomePage`) intentionally left untouched — it is not in Group_F08's
  `owned_files` and `App.test.tsx` (also not owned) still asserts its placeholder text
- `frontend/src/components/Layout.tsx` (modified) — the existing "Observability" nav item's target
  changed from `/` to `/leads`, now this project's first real, reachable nav destination

**Diff size:** ~640 lines added/changed across 12 files (1 new migration, 4 new frontend files, 1 new
backend test file, 6 modified)
**Validation:** PASS — see `.claude/validation-results.md` (111/111 backend tests passing — 102
pre-existing + 9 new; 3/3 frontend tests passing — 1 pre-existing + 2 new; `npm run build`/`tsc -b`
clean; manual dev-server + Playwright smoke test against real seeded leads, including a genuine
HubSpot-write failure from the placeholder sandbox token, confirmed the list and detail views, the
failed-stage banner, and the 404 case all render correctly)
**Pre-existing flaky test noted, not fixed (out of Group_F08's file ownership):**
`test_router_notifications.py::test_list_notifications_returns_newest_first` (Feature 07's own test
file, untouched this round) fails intermittently when re-run in isolation (5 reruns: 2 failed, 3
passed) — a timestamp-ordering race, unrelated to any Feature 08 change (Feature 08 touches no file
this test depends on). Logged to `.claude/refinement-backlog.md` (RB-001) rather than fixed here, since
`notifications.py`/its test file are outside this group's `owned_files`.
**Status:** approved — all 5 of Feature 08's acceptance criteria verified by test; this is also the
last Tier 1 feature — `implementation_plan.md` marks Feature 08 `COMPLETED`, Group_F08 `COMPLETED`,
completing all 8 Tier 1 features end-to-end

## 2026-09-04 — Step 6: Feature 09 (Classification Accuracy Benchmark Report), Group_F09

Built against `architecture-plan-feature-09.md`'s 10-step Implementation Order (Tier 2, first feature
built after the Tier 1 gate). Followed the plan's Architecture Rule Change exactly: the harness builds
its own `ToolRegistry`, calls the real `register_default_tools(registry, settings)`, and invokes
`IntentClassificationStage().run()` directly — no reimplementation of classification logic.

**Files touched:**
- `backend/app/benchmark/dataset.py` (new) — `BENCHMARK_DATASET`: 22 labeled `DatasetItem`s (6 buyer,
  6 browser, 6 spam, 4 ambiguous), each an `IntakeSlice` plus `expected_label`/`case_id`; ships as a
  Python-literal fixture, zero setup beyond a working Ollama install
- `backend/app/benchmark/harness.py` (new) — `run_benchmark(repeats, session_factory, settings)`:
  builds one registry/proxy per run (not per case), runs each dataset item `repeats` times through the
  real stage, computes attempt-level accuracy (non-ambiguous items only, failures never excluded) and
  item-level consistency (all items, a failed attempt breaks consistency), persists one `BenchmarkRun`
  + one `BenchmarkCase` per item. Discovered mid-implementation: `IntentClassificationStage.run()`
  never raises for expected failure modes — it retries its own tool call once internally and returns
  a `classification_failed` sentinel (`intent_label=None, confidence_score=0.0`) — so the harness's
  outer exception catch is a defensive fallback, not the primary failure path; the sentinel is.
- `backend/app/models/benchmark.py` (new) — `BenchmarkRun`/`BenchmarkCase` ORM models, plus
  `predicted_label`/`confidence` columns on `BenchmarkCase` (first attempt's result — the single
  representative prediction the failure table shows; not in the original plan's field list, added
  during implementation to give `correct` a defined comparison basis — see the plan's Actual Footprint)
- `backend/app/schemas/benchmark.py` (new) — `BenchmarkCaseOut`, `BenchmarkRunSummaryOut` (list view),
  `BenchmarkRunOut` (detail view: summary + full `cases` list), `BenchmarkRunListOut`
- `backend/app/routers/benchmark.py` (new) — `POST /benchmark/run` (synchronous, returns the completed
  run), `GET /benchmark/runs` (list, newest first, no per-case detail), `GET /benchmark/runs/{run_id}`
  (404 on unknown id, same pattern as `routers/leads.py`)
- `backend/alembic/versions/b86e4d4ef367_add_benchmark_tables.py` (new) — `benchmark_run`/
  `benchmark_case` tables, autogenerated and applied cleanly against the dev SQLite DB
- `backend/main.py` (modified) — registered `benchmark.router`
- `backend/app/models/__init__.py` (modified) — added `BenchmarkRun`/`BenchmarkCase` to the barrel
  export (not in the original `owned_files` list — caught by Step 6's companion-file checklist)
- `backend/app/tests/test_benchmark_harness.py` (new) — 3 tests: hand-computed accuracy/consistency
  against a scripted fake `ollama_classify` tool (accounting for the stage's own internal retry),
  ambiguous items never counted in the accuracy denominator, a deliberately-failing case counted as
  incorrect not excluded
- `backend/app/tests/test_router_benchmark.py` (new) — 4 tests: POST computes/persists accuracy, list
  view omits case detail, detail view lists every misclassified case with predicted/actual/confidence,
  404 on unknown run id
- `frontend/src/lib/api.ts` (modified) — `runBenchmark()`, `listBenchmarkRuns()`, `getBenchmarkRun(id)`
  + `BenchmarkRun`/`BenchmarkRunSummary`/`BenchmarkCase` types
- `frontend/src/pages/BenchmarkPage.tsx` (new) — "Run Benchmark" button (disabled + "Running…" label
  while in flight), accuracy/consistency/model stat tiles, a table of every ambiguous-or-misclassified
  case (predicted vs. actual label, confidence) — ambiguous items shown with an explicit "Ambiguous"
  badge, never forced into correct/incorrect
- `frontend/src/pages/BenchmarkPage.test.tsx` (new) — 2 tests: renders latest run + misclassified case,
  empty state with no runs yet
- `frontend/src/App.tsx` (modified) — added `benchmark` route
- `frontend/src/components/Layout.tsx` (modified) — added "Benchmark" nav item

**Diff size:** ~520 lines added/changed across 15 files (1 new migration, 8 new backend files, 2 new
frontend files, 4 modified)
**Validation:** PASS — see `.claude/validation-results.md` (118/118 backend tests — 111 pre-existing +
7 new; 5/5 frontend tests — 3 pre-existing + 2 new; `npm run build`/`tsc -b` clean; `oxlint` clean, no
new warnings; live manual dev-server + Playwright smoke test against the real local `llama3.2:3b`
model — not mocked — produced accuracy 87.0%/consistency 90.9% over the real 22-item dataset x 3
repeats, nav link correct, failure/ambiguous table rendered all 4 ambiguous items and all 3
misclassified cases with zero console errors).
**Status:** approved — all 6 of Feature 09's acceptance criteria verified live against the real model;
`implementation_plan.md` marks Feature 09 `COMPLETED`, Group_F09 `COMPLETED`.
