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

---

## 2026-09-04 — Step 5.5: Implementation Planner — Feature 04 (Data Enrichment Stage)

Produced `architecture-plan-feature-04.md`. Planning Depth: Standard (reuses Feature 03's
`input_slice`/`ToolRegistry` machinery unchanged — no `Stage` contract change needed — but introduces
the project's first HubSpot integration code and a new cross-slice question: what "merge into the lead
record" means when each stage owns only one slice).

**Existing Systems Analysis:** No duplication risk found (grep-confirmed no HubSpot client/lookup code
exists yet). Reuses `contracts.py`'s `input_slice`/`effective_input_slice` (Enrichment reads `intake`,
writes `enrichment` — the second stage to do this), `graph.py`'s `_STAGE_ORDER`/`default_stages()` swap
point and unmodified `_route_after_enrich` (routes purely on `classification.confidence_score`, so
Enrichment's own success/failure needs no new edge), the `tools/` one-module-per-external-system
convention, and already-present `hubspot_base_url`/`hubspot_access_token` config + pinned `httpx`.
**Key finding:** `app/tests/test_orchestrator_tool_scope.py` already anticipated a `"hubspot_write"`
tool name and a `"data_enrichment"`-named stage proxy that must never reach it — written ahead of this
feature, the same kind of forward-anticipation Feature 03 found for `"ollama_classify"`. This fixed
both the stage's `name` and the eventual Feature 05 write-tool name, and made a HubSpot-backed
read-only search (rather than a new paid third-party lookup service) the natural, free-by-default
choice for Enrichment's own tool — reusing the project's already-planned HubSpot integration instead of
adding a new external dependency, and turning the two tools' shared external system into a concrete
demonstration of the project's stated Critical risk.

**Architecture Rule Changes approved (3, all conflict-checked against existing Key Decisions):**
1. Wording generalization only (not a new rule) — the existing "recoverable external-system failure
   encoded as data, never raised" Key Decision's parenthetical examples broadened to include a lookup
   timeout, since Enrichment is a second real instance of the same already-general principle.
2. New: a read-only tool and a write tool for the same external system may share one `tools/
   <system>.py` module but must be registered under distinct names and granted to different stages'
   `allowed_tools` — never the same name gating both (`hubspot_search_contact` vs. `hubspot_write`).
   No conflict found; the read/write-scoping analogue of Feature 03's one-module-per-system rule,
   unaddressed until now because Ollama has only ever had one binding.
3. New: a "merged lead record" spanning more than one `LeadPipelineState` slice is a read-time concept,
   never a write-time one — a stage never writes into another stage's owned slice to represent a merge;
   a downstream consumer (e.g. Feature 05) reads the owning slice first, falling back to another named
   slice's fields for whatever the owner left null. No conflict found; doesn't change
   `LeadPipelineState`'s existing "each stage reads/writes only its own slice" boundary, just states for
   the first time how a multi-slice merge happens within it.

All three applied to `.claude/portfolio-reference.md`'s Key Decisions this session.

**Implementation Order set (4 steps):** `state.py`'s `EnrichmentSlice` extended
(`attempted_fields`/`match_confidence`/`conflicts`/`lookup_error`) → `app/orchestrator/tools/
hubspot_tools.py` (`search_contact`, read-only) + `tools/__init__.py` registration → `stages/
data_enrichment.py` (exact-key phone/email match at confidence 1.0, else fuzzy name match via stdlib
`difflib` against a `0.85` threshold; never overwrites an already-populated field; never raises on
lookup failure) → `graph.py` (`default_stages()["enrichment"] = DataEnrichmentStage()`, one line — no
other change, since `_make_node`/`_route_after_enrich` already generalize).

**Notable design resolution:** Classification's output is deliberately never read by this stage — the
feature spec's "lead record with classification result attached" phrasing describes the conceptual
lead moving through the pipeline, not a literal input Enrichment's own logic needs; it only ever reads
`IntakeSlice` fields.

**Approved by:** auto (Auto Mode + master prompt's "EXECUTE NOW" applied — same standing note as prior
entries: worth a human look before Step 6 starts writing code, particularly the new HubSpot
read/write tool-naming convention Feature 05 must follow).

**Next:** Step 6 (Worker Pool Orchestrator) claims Group_F04 using this plan's Implementation Order and
reuse instructions, and finalizes `implementation_plan.md`'s `owned_files` for that group.

---

## 2026-09-04 — Step 5.5: Implementation Planner — Feature 05 (HubSpot CRM Write Stage)

Produced `architecture-plan-feature-05.md`. Planning Depth: Deep — the project's own stated
highest-risk external integration, and the analysis surfaced two genuine architecture gaps rather than
a routine reuse case: this stage needs read access to two `LeadPipelineState` slices at once (which the
existing singular `input_slice` mechanism can't express), and the existing "recoverable failure, never
raise" Key Decision, read literally, contradicted what this feature's own spec explicitly requires (a
genuine write failure must halt the run).

**Existing Systems Analysis:** No duplication risk found (grep-confirmed `hubspot_tools.py` currently
holds only `search_contact` and its two Protocols). Reuses `CrmWriteSlice` (extended, not replaced),
the existing shared `httpx.Client` from `tools/__init__.py`, `hubspot_base_url`/`hubspot_access_token`
config, `_STAGE_ORDER`/the existing `crm_write_stage` → `_route_or_fail("notify")` edge, and — most
importantly — Feature 04's own `search_contact` function, called directly inside the new `write_contact`
as the dedupe lookup rather than re-implemented or exposed as a second tool.

**Architecture Rule Changes approved (3, all conflict-checked against existing Key Decisions):**
1. **Reworded, not additive** — the existing "recoverable failure encoded as data, never raised" Key
   Decision's closing clause ("never a failure mode a feature's own spec already anticipates")
   literally forbade Feature 05's own required behavior. Generalized: the deciding question is whether
   the spec wants the pipeline to continue past the failure or halt this lead's run — not whether the
   spec anticipates it. This supersedes the prior wording rather than sitting beside it.
2. New: a stage needing more than one input slice declares `input_slices` (plural companion to the
   existing singular `input_slice`); `_make_node` builds the merged input generically from a merge-only
   schema whose field names match the slice names. Additive — the singular mechanism (Feature 02/03) is
   completely unchanged. No conflict found; builds the mechanism Feature 04's "merged lead record is
   read-time" Key Decision had already anticipated needing without yet building.
3. New: a tool's dedupe-before-write lookup reuses an existing read-only tool as a direct in-module
   function call, never a second registered tool granted to the writing stage. No conflict found; the
   unstated corollary of Feature 04's "distinct tool names, different stages' `allowed_tools`" rule.

All three applied to `.claude/portfolio-reference.md`'s Key Decisions this session.

**Implementation Order set (7 steps):** `contracts.py` (`input_slices` added) → `state.py`
(`CrmWriteSlice` extended + new `MergedIntakeEnrichment` merge schema) → `graph.py`'s `_make_node`
(generic multi-slice branch) → `hubspot_tools.py` (`write_contact`: dedupe-lookup-then-create-or-update,
retry-with-backoff on 429/5xx via injected `sleep`, immediate raise on 401/403/other 4xx) →
`tools/__init__.py` (registers `"hubspot_write"` on the existing shared client) →
`stages/hubspot_crm_write.py` (new `HubSpotCrmWriteStage`, deliberately **no** try/except around the
tool call — see Rule Change #1) → `graph.py` (`default_stages()["crm_write"]` swap, no routing change).

**Notable design resolution:** write-side dedupe is exact-key only (phone/email) — deliberately no
name-fuzzy fallback (unlike Enrichment's read-side match), because a false-positive fuzzy match here
would update the wrong person's *live* CRM record, not just this project's own local state. No reliable
key present → always create, flagged `dedupe_uncertain=True`, per the spec's own edge case.

**Approved by:** auto (Auto Mode + master prompt's "EXECUTE NOW" applied — same standing note as prior
entries: worth a human look before Step 6 starts writing code, particularly the reworded failure-
handling Key Decision and the new `input_slices` contract change, both of which affect how future
stages should be written, not just this one).

**Next:** Step 6 (Worker Pool Orchestrator) claims Group_F05 using this plan's Implementation Order and
reuse instructions, and finalizes `implementation_plan.md`'s `owned_files` for that group.

---

## 2026-09-04 — Step 5.5: Implementation Planner — Feature 06 (Human Review & Approval Gate)

Produced `architecture-plan-feature-06.md`. Planning Depth: Deep — the feature spec assumes a
pause/resume mechanism ("reuses Feature 01's orchestrator resume mechanism") that turned out not to
actually exist anywhere in the codebase; this plan had to design and add one, plus a new persisted
domain model and a concurrency-sensitive API surface (4+ existing systems touched).

**Existing Systems Analysis:** No duplication risk found in the sense of a rebuilt system, but one real
near-miss was caught and rejected: naively reconstructing a paused run's state by replaying `StageTrace`
rows would have duplicated `StageTrace`'s execution-log role with a second, bespoke path — instead the
new `ReviewQueueItem` stores one full `LeadPipelineState` JSON snapshot at pause time, the same
snapshot *technique* `StageTrace` already uses, applied at the run level. **Key finding:** the existing
`_route_after_enrich` edge already fully implements this feature's confidence-based routing (high
confidence → auto CRM Write, low confidence → Human Review) — Feature 06 does not touch that edge at
all, only implements the real stage body it currently stubs and builds what happens after a lead lands
there. `RunStatus.AWAITING_REVIEW` already existed in the enum, unused by any code path until now.

**Architecture Rule Changes approved (3, all conflict-checked against existing Key Decisions, none
found):**
1. A paused run's resumable state is persisted as one full `LeadPipelineState` JSON snapshot on the
   owning feature's own domain row, never reconstructed by replaying `StageTrace` rows — a distinct
   concern from `StageTrace`'s execution-log role, not a competing rule.
2. Resuming a paused run re-enters the orchestrator abstraction (`Stage` contract, `ToolRegistry`,
   `_make_node`) via a second, smaller compiled graph starting at the paused stage, never a bespoke
   API-layer code path calling stage tools directly.
3. `RunStatus.REJECTED` is a new, distinct terminal status for an explicit reviewer rejection — never
   recorded as `FAILED`, which stays reserved for a stage raising during execution (a different axis
   than a human decision made after a stage already completed).

All three applied to `.claude/portfolio-reference.md`'s Key Decisions this session.

**Implementation Order set (7 steps):** `state.py` (`RunStatus.REJECTED`) → `app/models/review_queue.py`
(`ReviewQueueItem` + Alembic revision) → `stages/human_review.py` (trivial `HumanReviewStage` — the
queue-vs-auto decision was already made upstream) → `graph.py` (real stage wired in; dedicated
review-node wrapper persists the queue item + sets `AWAITING_REVIEW`) → `graph.py`
(`build_resume_graph()` + `resume_pipeline()`, a 2-node `crm_write_stage → notify_stage` continuation
reusing the same `Stage` instances) → `schemas/review.py` + `routers/reviews.py` (concurrency-safe
claim via a single conditional `UPDATE ... WHERE status='PENDING'`, never read-then-write) → `main.py`
router registration.

**Notable design resolution:** the reviewer-action endpoint never re-derives CRM-write logic itself —
approve/edit always goes through `resume_pipeline()`, so `HubSpotCrmWriteStage`'s existing dedupe/retry/
tool-scoping guarantees apply identically whether a lead reached CRM Write automatically or via human
approval.

**Approved by:** auto (Auto Mode + master prompt's "EXECUTE NOW" applied — same standing note as prior
entries: worth a human look before Step 6 starts writing code, particularly the new resume mechanism
and the concurrency-safe claim, since neither has an existing precedent in this project to check against).

**Next:** Step 6 (Worker Pool Orchestrator) claims Group_F06 using this plan's Implementation Order and
reuse instructions, and finalizes `implementation_plan.md`'s `owned_files` for that group.
