# Plan Audit Log — Lead Intake Triage Agent

Full process: `docs/plan-execute-review.md` §Plan Phase. One entry per plan checkpoint (Step 3's
initial plan, and any Step 6 mid-implementation re-plan).

---

## 2026-09-04 — Step 3: Feature Specification Engine — implementation_plan.md

Extracted all 14 `roadmap.md` features (Tier 1: 8, Tier 2: 3, Tier 3: 3) into atomic,
execution-ready specs in `implementation_plan.md` — expanded description, functional
requirements, system behaviors, edge cases, inputs/outputs, checkable acceptance criteria, and
executor metadata (status/group/locked/assigned_worker/is_blocked/depends_on) per feature.
Validated atomicity and no-overlap across all 14 features; dependency chain for Tier 1 matches
`roadmap.md`'s linear pipeline data flow (Pipeline Orchestration Layer → Intake Parsing → Intent
Classification → Data Enrichment → HubSpot CRM Write → Human Review Gate → Outcome Notification →
Observability View), with explicit boundary-enforcement acceptance criteria on every stage
touching the project's Critical risk (per-stage tool/state scoping must be architecturally real,
not cosmetic).

**Approved:**
- Tier 1 (Features 01-08) — build order per `roadmap.md`'s Execution Order Recommendation.
- Tier 2 (Features 09-11) — Classification Accuracy Benchmark, External Notification Delivery,
  Per-Lead Audit Trail UI — each independently startable per `roadmap.md`'s dependency notes.
- Tier 3 (Features 12-14) recorded for future-round visibility only.

**Rejected:**
- (None.)

**Deferred:**
- Feature 12 (Multi-Agent Orchestration) — explicitly locked (`locked: true`, `is_blocked: true`),
  not merely unscheduled: the project definition specifically warns against re-adding this
  stretch goal mid-build per the source specification's adversarial resolution.

**Approved by:** auto (no per-feature interactive sign-off occurred this session — Auto Mode +
the master prompt's "EXECUTE NOW" applied; flagged explicitly in the Step 3 report as worth a
human look before Step 6 starts writing code).

**Note (2026-09-04, Step 4):** this entry was reconstructed from the Step 3 session's own report
text after a Step 4 scaffolding error (`cp -r` from `templates/claude-dir/` overwrote this file's
original content with the blank template before it was backed up). Content above matches the
original Step 3 report verbatim where possible; no new review activity occurred. See
`.claude/pipeline-changelog.md` for the same note.

---

## 2026-09-04 — Step 5.5: Implementation Planner — Feature 01 (Pipeline Orchestration Layer)

Produced `architecture-plan-feature-01.md`. Planning Depth: Deep (foundational architecture change
carrying the project's Critical risk; Existing Systems Analysis itself was quick since nothing exists
yet to reuse beyond Step 4's empty scaffolding and already-pinned `langgraph` dependency).

**Existing Systems Analysis:** No duplication risk found — no orchestration/state-machine/tool-scoping
code exists anywhere yet. Reuses `app/database/session.py` (Base/SessionLocal) and
`app/core/config.py` (`confidence_threshold`) as-is; populates the empty `app/orchestrator/` package.

**Architecture Rule Changes approved (2, both conflict-checked against existing Key Decisions, none
found):**
1. Every pipeline stage implements the Stage contract and receives tools only through
   `tool_scope.py`'s scoped proxy — no stage may import another stage's tool binding directly.
2. Stage execution/transition data persists via `PipelineRun`/`StageTrace` — no bespoke per-feature
   log tables.

Both applied to `.claude/portfolio-reference.md`'s Key Decisions this session.

**Implementation Order set (5 steps):** contracts.py → state.py → tool_scope.py/errors.py →
pipeline_run.py models + Alembic migration → graph.py. Stage nodes for Features 02-07 are stub
callables until each feature's own Step 6 group lands.

**Approved by:** auto (Auto Mode + master prompt's "EXECUTE NOW" applied — same standing note as the
Step 3 entry above: worth a human look before Step 6 starts writing code).

**Next:** Step 6 (Worker Pool Orchestrator) claims Feature 01 using this plan's Implementation Order
and reuse instructions.

---

## 2026-09-04 — Step 5.5: Implementation Planner — Feature 02 (Intake Parsing & Normalization Stage)

Produced `architecture-plan-feature-02.md`. Planning Depth: Standard (touches three existing systems —
`Stage` contract, `LeadPipelineState`, `graph.py`'s stub-swap point — no new persistent data model, no
cross-system/AI integration).

**Existing Systems Analysis:** No duplication risk found. Reuses `contracts.py`'s `Stage` ABC,
`state.py`'s `IntakeSlice` (already shaped exactly for this feature's output — no state-schema change
needed), `schemas/pipeline.py`'s pre-existing `TriggerPipelineRunRequest` (web-form channel),
`graph.py`'s `default_stages()` dict-injection stub-swap point, and `tool_scope.py` with an empty
`allowed_tools` set. Resolved an implicit design question left open by Feature 01: since
`default_stages()` commits every stage to `input_schema == output_schema`, raw not-yet-normalized input
must be seeded into `IntakeSlice`'s own fields by whoever builds the initial state, and `IntakeStage.run()`
overwrites those fields in place — no separate pre-parsing layer.

**Architecture Rule Changes approved (2, both conflict-checked against existing Key Decisions, none
found):**
1. Each pipeline stage's real (non-stub) implementation lives in its own module under
   `app/orchestrator/stages/`, implementing the `Stage` contract.
2. A stage with `input_schema == output_schema` receives raw/unprocessed data in the same slice fields
   it will overwrite — the initial-state builder seeds them, the stage transforms them in place.

Both applied to `.claude/portfolio-reference.md`'s Key Decisions this session.

**Implementation Order set (5 steps):** `stages/intake.py` → `schemas/pipeline.py` additions (email +
callback request schemas) → `routers/leads.py` (three channel endpoints) → `graph.py`'s
`default_stages()` stub-swap → `main.py` router registration.

**Approved by:** auto (Auto Mode + master prompt's "EXECUTE NOW" applied — same standing note as prior
entries: worth a human look before Step 6 starts writing code).

**Next:** Step 6 (Worker Pool Orchestrator) claims Group_F02 using this plan's Implementation Order and
reuse instructions, and finalizes `implementation_plan.md`'s `owned_files` for that group.

---

## 2026-09-04 — Step 5.5: Implementation Planner — Feature 03 (Intent Classification Stage)

Produced `architecture-plan-feature-03.md`. Planning Depth: Deep (first AI integration; requires
extending the `Stage` contract itself, resolving how an external-system failure reaches Human Review
without bypassing it, and populating `ToolRegistry` with a real binding for the first time — 4+
existing systems touched: `contracts.py`, `graph.py`, `tool_scope.py`'s registry, `state.py`).

**Existing Systems Analysis:** No duplication risk found. Reuses `state.py`'s `ClassificationSlice`
(already shaped exactly for this feature's output), `tool_scope.py`'s `ToolRegistry`/`ScopedToolProxy`
as-is, `graph.py`'s `default_stages()` swap point and — the key finding — its existing
`_route_after_enrich` confidence-threshold routing, which already sends a `None`/low `confidence_score`
to Human Review with zero new graph edges. Reuses the already-pinned `ollama` dependency, `Settings.
ollama_base_url`/`ollama_model`, and the `"ollama_classify"` tool name already anticipated by
`test_orchestrator_tool_scope.py`. Surfaced a real architectural gap: `_make_node` only ever read a
stage's input from its own `state_slice`, which breaks for a stage (this one) that must read `intake`
but write `classification` — resolved via Architecture Rule Change #1 below rather than worked around
per-feature.

**Architecture Rule Changes approved (3, all conflict-checked against existing Key Decisions):**
1. `Stage` gains `input_slice` (default `None`, falls back to `state_slice` via a new
   `effective_input_slice` property) — generalizes, not contradicts, Feature 02's existing
   same-schema Key Decision; that rule is restated as this new rule's special case in the same bullet
   rather than left standing separately.
2. A stage's own per-spec-expected external-system failure (retry-exhausted call error or invalid
   response) is encoded as output-slice data, never raised — so it flows through existing confidence
   routing into Human Review instead of short-circuiting to `RunStatus.FAILED`/END. No conflict found;
   generalizes a risk-mitigation note Feature 02's plan stated only locally.
3. Real tool bindings live one-module-per-external-system under a new `app/orchestrator/tools/`
   package, wired by `register_default_tools(registry, settings)`, called from
   `build_production_graph()` — the tools-side analogue of Feature 02's "one file per stage" rule. No
   conflict found; nothing addressed this because no stage needed a real tool binding until now.

All three applied to `.claude/portfolio-reference.md`'s Key Decisions this session.

**Implementation Order set (4 steps):** `contracts.py`'s `input_slice`/`effective_input_slice` →
`app/orchestrator/tools/` package (`ollama_tools.py` + `register_default_tools`) →
`stages/intent_classification.py` (empty-message short-circuit; retry-once-then-fail-closed policy;
`{buyer, browser, spam}` label validation) → `graph.py` (`_make_node` reads
`effective_input_slice`; real `default_stages()["classification"]`; `build_production_graph()` now
populates `ToolRegistry` for the first time).

**Notable design resolution:** the feature spec's optional hosted-LLM-API fallback path is deliberately
**not** built this round — `.claude/portfolio-reference.md`'s existing Key Decision already defers that
until Feature 09's benchmark shows the local model is insufficient. This plan satisfies "support an
optional fallback" by leaving the seam open (multi-tool `allowed_tools`, existing
`fallback_llm_api_key` config field), not by wiring a second tool call now.

**Approved by:** auto (Auto Mode + master prompt's "EXECUTE NOW" applied — same standing note as prior
entries: worth a human look before Step 6 starts writing code, especially the two new Architecture
Rule Changes to the `Stage` contract itself).

**Next:** Step 6 (Worker Pool Orchestrator) claims Group_F03 using this plan's Implementation Order and
reuse instructions, and finalizes `implementation_plan.md`'s `owned_files` for that group.
