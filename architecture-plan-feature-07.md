IMPLEMENTATION PLAN
====================

Feature / Round: Feature 07 (Outcome Notification — In-App)
Classification: New feature, Architecture change
Planning Depth: Deep — touches shared orchestrator plumbing at multiple call sites (`_make_node`'s
exception handler, `_make_human_review_node`, `reviews.py`'s reject branch, `run_pipeline`/
`resume_pipeline`), not just one new isolated module.

Objective
Fire exactly one persisted in-app notification at each of the pipeline's four terminal/review-pending
outcomes (auto-processed, awaiting review, rejected, failed). The existing graph topology only
naturally reaches the scaffolded `notify_stage` node for one of these four (the crm_write-success
path) — this plan wires the other three in without changing graph edges or risking a double-fire.

Existing Systems Analysis
- Reusable:
  - `LeadPipelineState.notification` slice (`NotificationSlice`, already in `state.py`) — used as-is.
  - The existing `notify_stage` graph node (`_make_node(stages["notification"], ...)`) on both the
    primary graph (`crm_write_stage -> notify_stage`) and the resume graph (same edge) — once
    `default_stages()` swaps the stub for a real stage, this node already correctly fires for the
    auto-processed outcome with **zero graph/edge changes**.
  - `StageTrace`/`PipelineRun` (`app/models/pipeline_run.py`) — the notification stage's own execution
    is just another stage transition, logged the same way every other stage's trace already is.
  - `Stage` contract (`app/orchestrator/contracts.py`) and `ToolRegistry`/`ScopedToolProxy` — reused
    with an empty `allowed_tools`, the same shape as `HumanReviewStage` (pure signaling stage, no
    external system access).
- Duplication Risk Flagged: none found — no existing notification/messaging system exists anywhere in
  the codebase.
- Modify:
  - `backend/app/orchestrator/graph.py`:
    - `default_stages()` — swap the notification stub for the real stage (1 line, same pattern
      Features 03-06 already used).
    - `_make_node()`'s except block — currently returns `{"run": ...}` only on a stage exception and
      never notifies, because the "failed" conditional-edge target is `END` directly, never
      `notify_stage`.
    - `run_pipeline()` / `resume_pipeline()` — **neither currently ever sets `RunStatus.COMPLETED`**.
      Nothing in the codebase does. A successful run's `PipelineRun.status` stays `"RUNNING"` forever.
      This is a pre-existing gap that Feature 07's own "auto-processed" outcome-typing requirement
      exposes (confirmed via search — `RunStatus.COMPLETED` has zero assignment sites; the only
      "COMPLETED" occurrences in the codebase are unrelated `StageTrace.status` string literals).
  - `_make_human_review_node()` (in `graph.py`) — its success path persists a `ReviewQueueItem` and
    returns, but `human_review_stage -> END` never visits `notify_stage` either. The awaiting-review
    outcome needs the same direct-call treatment as the failure case.
  - `backend/app/routers/reviews.py`'s reject branch — currently flips `PipelineRun.status` to
    `REJECTED` via a direct SQL-level update and returns; never creates a notification, and (unlike
    approve/edit) never re-enters the orchestrator at all for this path.
- New:
  - `backend/app/orchestrator/stages/outcome_notification.py` — `OutcomeNotificationStage(Stage)`,
    one file per stage, per the existing Key Decision.
  - `backend/app/models/notification.py` — `Notification` SQLAlchemy model.
  - `backend/app/schemas/notification.py` — `NotificationOut` Pydantic response shape.
  - `backend/app/routers/notifications.py` — `GET /notifications` (list, newest first).
  - New Alembic migration for the `notification` table.
  - `persist_outcome_notification()` — a new module-level helper in `graph.py`, exported for
    `reviews.py` to import — the shared "build merged input, call stage, write trace, save
    `Notification` row" logic used by the three call sites that bypass the graph-node path.
- Navigation Relationships Flagged: none — Feature 07 has no frontend surface of its own (Tier 1,
  group PIPELINE_STAGES). It writes `detail_link` values a *future* frontend (Feature 08's lead
  detail view; the existing review queue) will consume — see the routing-convention Architecture Rule
  Change below, which exists precisely so Feature 08 doesn't have to guess the path shape.

System Impact Map
```
FEATURE 07 — Outcome Notification (In-App)
│
├── Backend
│   ├── app/orchestrator/stages/outcome_notification.py (new) — OutcomeNotificationStage
│   ├── app/orchestrator/graph.py (modify) — default_stages() swap; _make_node() FAILED-branch notify
│   │     call; _make_human_review_node() AWAITING_REVIEW notify call; run_pipeline()/
│   │     resume_pipeline() RunStatus.COMPLETED fix; new persist_outcome_notification() helper
│   ├── app/routers/reviews.py (modify) — reject branch calls persist_outcome_notification()
│   ├── app/routers/notifications.py (new) — GET /notifications
│
├── Database
│   ├── app/models/notification.py (new) — Notification table
│   ├── alembic/versions/<new>_add_notification_table.py (new)
│
├── Existing Systems (reused, not duplicated)
│   ├── LeadPipelineState.notification slice (state.py) — unchanged, already scaffolded
│   ├── StageTrace / PipelineRun (pipeline_run.py) — notification stage's transition logs here too
│   ├── Stage contract + ToolRegistry/ScopedToolProxy — plugs in exactly like HumanReviewStage
│
├── Navigation
│   ├── none today (no frontend of its own)
│   └── forward-declared for Feature 08: detail_link = `/leads/{lead_id}` (auto_processed, failed) or
│       `/reviews/{run_id}` (awaiting_review, rejected)
│
└── AI
    └── N/A — purely deterministic message construction, no LLM/generation involved
```

Implementation Order (Dependency Graph)
1. **`Notification` model + Alembic migration**
   - Purpose: persisted store for outcome records.
   - Existing files: none. New files: `app/models/notification.py`,
     `alembic/versions/<rev>_add_notification_table.py`.
   - Dependencies: none.
   - Requirements: string UUID PK (same pattern as `PipelineRun`/`ReviewQueueItem`); `run_id` FK to
     `pipeline_run.id`, indexed (same style as `StageTrace.run_id`); `lead_id` indexed; `outcome_type`,
     `message`, `detail_link`, `created_at`.
   - Validation: `alembic upgrade head` succeeds; table exists with the above columns.

2. **`OutcomeNotificationStage`** (`app/orchestrator/stages/outcome_notification.py`)
   - Purpose: pure business logic building a `NotificationSlice` from `run`+`intake`+`crm_write` input,
     keyed off `state.run.status`.
   - Existing files: `contracts.py` (Stage base, unchanged), `state.py` (existing slices, unchanged —
     add a new merge schema `NotificationInput` alongside `MergedIntakeEnrichment` for consistency).
   - New files: the stage module.
   - Dependencies: step 1.
   - Requirements: `input_slices = ("run", "intake", "crm_write")`, `state_slice = "notification"`,
     `allowed_tools = frozenset()`. Map `run.status` -> `outcome_type`: `RUNNING` -> `auto_processed`
     (the only status value possible at this call point when nothing else has claimed the run — see
     Architecture Rule Change below), `FAILED` -> `failed`, `AWAITING_REVIEW` -> `awaiting_review`,
     `REJECTED` -> `rejected`. Build `message` from intake's name (falling back to phone/email/lead_id
     when name is null — Feature 02's "low_identifiability"/"empty_message" cases already leave name
     null upstream) plus outcome-specific detail (`failed_stage`/`error` for `failed`). Build
     `detail_link` per the Navigation convention.
   - Validation: unit tests, one per outcome_type input combination, including the null-name fallback.

3. **`persist_outcome_notification()` helper** (`graph.py`)
   - Purpose: shared "resolve merged input, call `stage.run()`, write `StageTrace`, save `Notification`
     row" logic, usable outside the normal per-node graph flow.
   - Existing files: `graph.py` (`_write_trace`, `_make_node` — mirror their shape).
   - New files: none (function added to `graph.py`).
   - Dependencies: steps 1-2.
   - Requirements: signature `(state, stage, registry, session_factory) -> NotificationSlice`. Must
     never be combined with the generic `notify_stage` graph-node path for the *same* transition — it
     exists specifically for the three transitions that node never sees.
   - Validation: called exactly once per terminal outcome; `Notification` row count matches outcome
     count in tests.

4. **Wire the three direct call sites**
   - Purpose: cover the three terminal transitions the existing graph topology doesn't route through
     `notify_stage`.
   - Existing files: `graph.py`'s `_make_node()` except-block and `_make_human_review_node()`;
     `routers/reviews.py`'s reject branch.
   - New files: none.
   - Dependencies: step 3.
   - Requirements:
     (a) `_make_node`'s except block calls `persist_outcome_notification` with the just-built FAILED
     state before returning, wrapped in its own try/except that logs and swallows — never lets a
     notification-layer error mask or replace the original stage failure being reported.
     (b) `_make_human_review_node`'s success path calls it with the just-built AWAITING_REVIEW state
     before returning.
     (c) `reviews.py`'s reject branch parses `item.state_snapshot` into a `LeadPipelineState`, sets
     `run.status = REJECTED`, and calls `persist_outcome_notification` directly (a fresh `ToolRegistry()`
     is sufficient — the stage needs no tools) before returning.
   - Validation: one test per call site confirming a `Notification` row is created with the correct
     `outcome_type`.

5. **Close the `RunStatus.COMPLETED` gap**
   - Purpose: make "auto_processed" actually distinguishable from an in-progress run.
   - Existing files: `graph.py`'s `run_pipeline()`/`resume_pipeline()`.
   - New files: none.
   - Dependencies: none (independent of steps 1-4, but must land before any status-based validation
     passes).
   - Requirements: immediately before persisting `final_state.run.status` to `PipelineRun.status`, if
     it's still `RUNNING`, set it to `COMPLETED` first.
   - Validation: a full successful pipeline run's `PipelineRun.status` reads `"COMPLETED"`, not
     `"RUNNING"`, after `run_pipeline()` returns.

6. **`default_stages()` swap**
   - Purpose: activate the auto-processed outcome's notification path via the untouched existing graph
     edge.
   - Existing files: `graph.py`'s `default_stages()`.
   - New files: none.
   - Dependencies: step 2.
   - Requirements: `stages["notification"] = OutcomeNotificationStage()`.
   - Validation: existing `test_orchestrator_graph.py` tests covering `crm_write -> notify -> END` now
     exercise real stage logic instead of the stub's `NotImplementedError`.

7. **`GET /notifications` router + schema**
   - Purpose: expose created notifications (no read/unread state — nothing in the spec's Outputs shape
     or acceptance criteria calls for one).
   - Existing files: `routers/__init__.py` (registration, same pattern as `reviews.py`).
   - New files: `schemas/notification.py`, `routers/notifications.py`.
   - Dependencies: steps 1-6.
   - Requirements: list endpoint, newest-first, `NotificationOut.model_validate`.
   - Validation: a created notification appears in `GET /notifications`.

Architecture Rule Changes
- [ ] "A pipeline run's terminal status is set exactly once, at the point where that outcome becomes
  known — `RunStatus.FAILED` inside `_make_node`'s exception handler, `RunStatus.AWAITING_REVIEW`
  inside `_make_human_review_node`, `RunStatus.REJECTED` inside `routers/reviews.py`'s reject branch,
  and `RunStatus.COMPLETED` by `run_pipeline`/`resume_pipeline` whenever the graph returns with
  `run.status` still `RUNNING` (the only way `RUNNING` can reach that point is that no other terminal
  path fired). No other code should independently decide a run is 'done'." — Conflict check: none
  found; generalizes rather than contradicts the existing Feature 06 Key Decision ("`RunStatus.FAILED`
  is reserved for a stage raising... a reviewer's explicit rejection is `RunStatus.REJECTED`") — that
  rule established the FAILED/REJECTED distinction; this one completes the enum by stating where
  COMPLETED and AWAITING_REVIEW are each authoritatively set, since COMPLETED wasn't a problem until
  Feature 07's outcome-typing needed it.
- [ ] "An outcome-notification call site is one of exactly two shapes: (a) the existing generic
  per-stage graph node (`_make_node`), used only for the one transition that already flows through
  `notify_stage` in normal execution (crm_write success); (b) a direct call to
  `persist_outcome_notification()` at each of the other terminal-transition points (stage failure,
  human-review queueing, reviewer rejection) that don't otherwise reach that node. A future
  outcome-consuming feature — Feature 10 (External Notification Delivery) explicitly says it
  'subscribes to the same outcome events Feature 07 consumes' — extends `persist_outcome_notification()`
  and its three direct call sites, not a new parallel notification mechanism." — Conflict check: none
  found; first Key Decision addressing outcome/event dispatch.
- [ ] "Notification `detail_link` values follow a fixed convention: `/leads/{lead_id}` for outcomes
  tied to a lead's CRM/detail record (`auto_processed`, `failed`), `/reviews/{run_id}` for outcomes
  tied to the review queue (`awaiting_review`, `rejected`). Any future frontend route for these views
  (Feature 08's lead detail page; the existing review queue) must match these exact paths rather than
  the notification layer adapting to whatever route the frontend happens to choose." — Conflict check:
  none found; first Key Decision stating a frontend routing convention — Feature 08 (next in sequence)
  is the one that must honor it.

Feature-Specific Requirements
- Exact message text templates are implementer's judgment within the acceptance criteria below — not
  promoted to Key Decisions.
- `Notification` message falls back to phone/email/lead_id when `intake.name` is null, rather than
  producing a broken/blank message for a low-identifiability lead.
- No "delivery target user"/addressee field at all. Confirmed via search: no `User` class, no
  `assigned_rep`/`assigned_user`/`rep_id`/`owner_id` field exists anywhere in this codebase — it's a
  single-tenant app with no auth system. The spec's "falls back to a general/unassigned notification
  destination" edge case is satisfied by there being exactly one, system-wide destination (the
  `/notifications` list) — do not add a per-user addressee field speculatively.

Risks
- Risk: A notification-creation error inside `_make_node`'s except block or `_make_human_review_node`
  could mask the original stage failure/queueing outcome. Mitigation: wrap each direct call to
  `persist_outcome_notification` in its own try/except that logs and swallows — never re-raises, never
  replaces the original error already being returned.
- Risk: `RunStatus.COMPLETED` now being set changes existing persisted status values — any existing
  test asserting `PipelineRun.status == "RUNNING"` after a successful run will start failing.
  Mitigation: grep existing tests for `"RUNNING"` assertions on a completed run before landing step 5;
  update them as part of this feature's own test changes, not a silent breakage discovered later.
- Risk: A future refactor accidentally routes a FAILED/AWAITING_REVIEW state through the `notify_stage`
  graph node in addition to the direct call, double-firing a notification. Mitigation: the Architecture
  Rule Change above states the two call-site shapes are mutually exclusive per outcome; Step 7
  verification must confirm no code path can reach both for the same run.

Acceptance Criteria
- [ ] An auto-processed lead (crm_write succeeds, run reaches COMPLETED) produces exactly one
  `Notification` row with `outcome_type="auto_processed"` and `detail_link="/leads/{lead_id}"`.
- [ ] A lead routed to Human Review produces exactly one `Notification` row with
  `outcome_type="awaiting_review"` and `detail_link="/reviews/{run_id}"`, at the point it's queued.
- [ ] A pipeline run that raises in any stage produces exactly one `Notification` row with
  `outcome_type="failed"`, describing `failed_stage`/`error`.
- [ ] A reviewer's reject action produces exactly one additional `Notification` row
  (`outcome_type="rejected"`), distinct from the original `awaiting_review` notification (both persist).
- [ ] A reviewer's approve/edit action, after resuming through crm_write, produces exactly one
  additional `Notification` row (`auto_processed` or `failed` depending on resume outcome), distinct
  from the original `awaiting_review` notification.
- [ ] `PipelineRun.status` reads `"COMPLETED"` (not `"RUNNING"`) after a successful run completes.
- [ ] `GET /notifications` returns created notifications, newest first.

Validation Requirements
- Confirm no code path invokes `persist_outcome_notification` AND the generic `notify_stage` graph node
  for the same `run_id` (the double-fire risk named above).
- Re-check existing tests asserting `PipelineRun.status == "RUNNING"` post-completion — these should be
  updated to `"COMPLETED"`, not left silently describing the pre-fix behavior.
- Confirm `OutcomeNotificationStage.allowed_tools == frozenset()` under the existing
  `test_orchestrator_tool_scope.py`-style scoping test, consistent with `HumanReviewStage`.

Predicted Footprint
Files predicted to change: ~10 (new: `outcome_notification.py`, `models/notification.py`,
`schemas/notification.py`, `routers/notifications.py`, 1 Alembic migration; modified: `graph.py`,
`routers/reviews.py`, `state.py` [new merge schema], `routers/__init__.py`, `models/__init__.py`)
Systems predicted to touch: orchestrator graph/stage plumbing, review router, database
models/migrations, new notifications router, `.claude/portfolio-reference.md` Key Decisions.

--- filled in later, by Step 7, once implementation is verified ---
Actual Footprint
Files actually changed: [pending Step 7]
Deviations from plan: [pending Step 7]
Rework required: [pending Step 7]
