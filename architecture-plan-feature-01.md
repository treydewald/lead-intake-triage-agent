IMPLEMENTATION PLAN
====================

Feature / Round: Feature 01 — Pipeline Orchestration Layer
Classification: New feature, Architecture change
Planning Depth: Deep — this is the single foundational feature the project's Critical risk (per-stage
tool/state boundary must be real under code inspection, not cosmetic) attaches to, and it defines a
new persistent state/trace data model every downstream Tier 1 feature depends on. Existing Systems
Analysis itself is quick (nothing exists yet to reuse beyond scaffolding), but Implementation Order,
Architecture Rule Changes, and Risk Analysis get full treatment because errors here propagate to all
seven remaining Tier 1 features.

Objective
Stand up the LangGraph state-machine backbone, the Stage contract every pipeline stage implements,
and an enforced (not documentation-only) per-stage tool-access boundary, plus the persisted
PipelineRun/StageTrace records Feature 08 will later query — before any of the six downstream stages
write their own logic.

Existing Systems Analysis
- Reusable: `app/database/session.py` (Base/SessionLocal/get_db — the new PipelineRun/StageTrace
  models bind to this, no new engine/session setup needed). `app/core/config.py` (already carries
  `confidence_threshold`, `ollama_*`, `hubspot_*` settings later stages need; the orchestrator itself
  only needs `confidence_threshold` for the Human Review conditional edge). `app/orchestrator/`
  (empty package created at Step 4 bootstrap — this feature is exactly what populates it).
  `langgraph==0.2.34` already pinned in `backend/requirements.txt` — matches the Key Decision in
  `portfolio-reference.md` ("Orchestration library: LangGraph"), no re-decision needed.
- Duplication Risk Flagged: none found — no orchestration, state-machine, or tool-scoping logic
  exists anywhere in the codebase yet (Step 4 bootstrap explicitly shipped no pipeline-stage logic
  per its own "What This Stage Does NOT" boundary).
- Modify: `app/orchestrator/__init__.py` (currently empty — becomes the package's public surface).
- New: `app/orchestrator/contracts.py`, `app/orchestrator/state.py`, `app/orchestrator/tool_scope.py`,
  `app/orchestrator/errors.py`, `app/orchestrator/graph.py`, `app/models/pipeline_run.py`,
  `app/schemas/pipeline.py`, one Alembic revision. None of these have an existing analogue — this is
  the project's first persisted data model and first orchestration code.
- Navigation Relationships Flagged: none this feature — it's backend-only, no UI surface. Feature 08
  (Observability / Monitoring View) will later read the `PipelineRun`/`StageTrace` tables this
  feature creates and should link each dashboard row to its underlying run — noted here so Feature
  08's own plan doesn't have to rediscover it.

System Impact Map
```
FEATURE 01 — Pipeline Orchestration Layer
│
├── Backend
│   ├── app/orchestrator/contracts.py (new) — Stage interface: input/output schema, declared tool
│   │     names, declared state-slice keys
│   ├── app/orchestrator/state.py (new) — LeadPipelineState schema (one slice per stage)
│   ├── app/orchestrator/tool_scope.py (new) — scoped tool-binding proxy; raises on out-of-scope call
│   ├── app/orchestrator/errors.py (new) — OutOfScopeToolError, StageExecutionError, StateValidationError
│   ├── app/orchestrator/graph.py (new) — LangGraph StateGraph: 6 stage nodes (stub bodies for
│   │     Features 02-07 until their own Step 6 groups land), deterministic edges, conditional
│   │     Human Review branch, per-transition StageTrace write
│   └── app/schemas/pipeline.py (new) — Pydantic request/response schemas for triggering/querying a run
│
├── Database
│   ├── app/models/pipeline_run.py (new) — PipelineRun, StageTrace SQLAlchemy models
│   └── alembic/versions/<new> — creates pipeline_run / stage_trace tables
│
├── Existing Systems (reused, not duplicated)
│   ├── app/database/session.py — Base/SessionLocal for the new models
│   └── app/core/config.py — confidence_threshold read by the conditional edge
│
├── Navigation
│   └── none this feature — Feature 08 will later link into PipelineRun/StageTrace records this
│         feature creates (see Existing Systems Analysis above)
│
└── AI
    └── none directly — this feature wires graph shape only; per-stage LLM calls belong to
          Features 03 (Intent Classification) and 04 (Data Enrichment)
```

Implementation Order (Dependency Graph)
1. **contracts.py** — Stage Protocol/ABC (input schema, output schema, declared tool names, declared
   state-slice keys). Purpose: the interface every stage (this feature's stubs, and every later
   feature's real implementation) must satisfy. Existing files: none. New files:
   `app/orchestrator/contracts.py`. Dependencies: none. Requirements: usable to type both a stub node
   and a future real stage. Validation: unit test instantiates a dummy stage conforming to the
   contract and asserts a non-conforming one is rejected.
2. **state.py** — `LeadPipelineState` Pydantic model, one field group per stage's declared slice
   (intake, classification, enrichment, crm_write, review, notification, run metadata). Existing
   files: none. New files: `app/orchestrator/state.py`. Dependencies: contracts.py. Validation:
   schema round-trips a full state object through serialization.
3. **tool_scope.py + errors.py** — `ToolRegistry`/scoped-tool-proxy: each stage receives a proxy
   exposing only its contract's declared tool names; any other call raises `OutOfScopeToolError`,
   caught and logged by the orchestrator (never a silent no-op). Existing files: none. New files:
   `app/orchestrator/tool_scope.py`, `app/orchestrator/errors.py`. Dependencies: contracts.py.
   Validation: test proves the Intent Classification stage's proxy rejects a call to the (future)
   HubSpot write tool — this is the direct test for the project's Critical risk.
4. **pipeline_run.py models + Alembic migration** — `PipelineRun` (id, lead_id, status, created_at,
   updated_at), `StageTrace` (id, run_id FK, stage_name, input_snapshot, output_snapshot, status,
   error, created_at). Existing files: `app/database/session.py` (Base). New files:
   `app/models/pipeline_run.py`, one Alembic revision. Dependencies: state.py (trace payload shape
   must match state slices). Validation: `alembic upgrade head` succeeds on a fresh SQLite DB; a
   model round-trips via `SessionLocal`.
5. **graph.py** — LangGraph `StateGraph` wiring the 6 stages: deterministic edges Intake → Classify →
   Enrich → CRM Write → Notify; conditional edge from Classify/Enrich into Human Review when
   `state.classification.confidence < settings.confidence_threshold`; error edge — any stage
   exception halts that lead's run only, marks it FAILED, writes a StageTrace row with the error, and
   does not affect other concurrent runs. Stage nodes for Features 02-07 are stub callables (raise
   `NotImplementedError`) until each feature's own Step 6 group lands — this file defines graph shape
   and transition logic only, not stage bodies. Existing files: `app/core/config.py`
   (`confidence_threshold`). New files: `app/orchestrator/graph.py`. Dependencies: contracts.py,
   state.py, tool_scope.py, pipeline_run.py. Validation: the five acceptance-criteria tests below.

Architecture Rule Changes
- [x] "Every pipeline stage implements the Stage contract (`app/orchestrator/contracts.py`) and
  receives tools only through `tool_scope.py`'s scoped proxy — a stage module must never import or
  call another stage's tool binding directly." Conflict check: none found — no existing Key Decision
  addressed stage/tool structure; this makes the "per-stage scoped tool access" language already in
  `portfolio-reference.md`'s Project Overview concrete and enforceable. **Applied to
  `.claude/portfolio-reference.md`'s Key Decisions.**
- [x] "Stage execution/transition data persists via `PipelineRun`/`StageTrace`
  (`app/models/pipeline_run.py`) — any future stage's execution record belongs there, not a bespoke
  per-feature log table." Conflict check: none found. **Applied to `.claude/portfolio-reference.md`'s
  Key Decisions.**

Feature-Specific Requirements
- Stub node bodies for Features 02-07 raise `NotImplementedError` with the feature ID they belong to,
  purely to keep `graph.py`'s edges testable before those features land — not a durable design,
  documented as a code comment in `graph.py` only, not promoted to Key Decisions.
- `LeadPipelineState`'s exact field names per stage slice are feature-specific detail (e.g. the
  precise shape of the classification slice) and stay in this plan / `implementation_plan.md`, not
  Key Decisions.

Risks
- Risk: Tool-scoping enforcement ends up documentation-only (cosmetic), which is precisely the
  project's stated Critical risk. Mitigation: `tool_scope.py` must be the *only* path any stage code
  uses to reach a tool binding — no stage module may import a tool module directly; enforced by the
  out-of-scope-call test in Acceptance Criteria, which Step 7 must run, not skip as a happy-path-only
  check.
- Risk: LangGraph's native state object is visible in full to every node by default, conflicting with
  "each stage reads/writes only its declared slice." Mitigation: wrap each node with a
  slice-restricting adapter derived from `contracts.py` before invoking the real stage function, so a
  stage physically cannot read fields outside its declared slice.
- Risk: Downstream feature groups (02-07) start building against `graph.py`'s stub shape before this
  feature's interfaces are stable, causing rework. Mitigation: `contracts.py`'s Stage interface is
  frozen as part of this round's Architecture Rule Changes before Step 6 claims any downstream group.
- Risk: SQLite write contention across concurrently-running leads could violate the "no shared mutable
  state across leads" acceptance criterion. Mitigation: `StageTrace` writes are per-run-scoped inserts
  (never a shared-row update), which is safe under SQLite's file-level locking for this project's
  scale; revisit only if the already-planned PostgreSQL DSN swap-in is triggered by real load.

Acceptance Criteria
- [ ] A stage cannot access state fields or tools outside its declared contract — verified by a test
  that attempts an out-of-scope tool call and asserts `OutOfScopeToolError` is raised, not silently
  ignored.
- [ ] The graph routes a high-confidence lead through Intake → Classify → Enrich → CRM Write → Notify
  with no Human Review branch taken (using stub nodes).
- [ ] The graph routes a low-confidence lead into the Human Review branch instead of auto-proceeding
  to CRM Write.
- [ ] A stage exception halts only that lead's pipeline run (marked FAILED, error recorded) without
  affecting a second, concurrently-running lead's execution.
- [ ] Every stage transition produces a `StageTrace` row queryable per lead.
- [ ] `alembic upgrade head` creates `pipeline_run`/`stage_trace` tables cleanly on a fresh SQLite DB.

Validation Requirements
Step 7 must specifically execute the out-of-scope-tool-call test and the concurrent-lead-isolation
test — these are the two most likely to be silently reduced to happy-path-only coverage, and they are
the direct evidence for the project's Critical risk claim. Step 7 should also confirm no stage module
(once Features 02-07 land) imports a tool binding outside `tool_scope.py`'s proxy, by grep, not just
by test pass/fail.

Predicted Footprint
Files predicted to change: 8 (contracts.py, state.py, tool_scope.py, errors.py, graph.py,
pipeline_run.py, schemas/pipeline.py, one Alembic revision) — plus `app/orchestrator/__init__.py`
populated with the package's public exports.
Systems predicted to touch: Backend orchestrator package, database models/migrations, config
(read-only).

--- filled in later, by Step 7, once implementation is verified ---
Actual Footprint
Files actually changed: [pending Step 6/7]
Deviations from plan: [pending Step 6/7]
Rework required: [pending Step 6/7]
