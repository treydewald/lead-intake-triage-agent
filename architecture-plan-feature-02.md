IMPLEMENTATION PLAN
====================

Feature / Round: Feature 02 — Intake Parsing & Normalization Stage
Classification: New feature, Backend change
Planning Depth: Standard — touches three existing systems (the Stage contract, the LeadPipelineState
schema, the graph's stub-swap point) with no new persistent data model and no cross-system/AI
integration, but the exact shape of how raw external input enters the graph needs to be resolved
explicitly (see Existing Systems Analysis) rather than left implicit.

Objective
Replace `graph.py`'s "intake" stub with a real `IntakeStage`, and add the API entry points (web form,
email, missed-call callback) that construct the graph's initial state and call Feature 01's
`run_pipeline()` — so a raw inbound lead becomes the first real data flowing through the orchestrator.

Existing Systems Analysis
- Reusable:
  - `app/orchestrator/contracts.py`'s `Stage` ABC — `IntakeStage` implements it directly; no new
    interface needed.
  - `app/orchestrator/state.py`'s `IntakeSlice` — already declares exactly the fields Feature 02's
    spec requires as output (`source_channel`, `name`, `phone`, `email`, `message_body`,
    `raw_input_ref`, `received_at`, `low_identifiability`, `empty_message`). **No state-schema change
    is needed.** Resolved question: `default_stages()` (Feature 01) already commits every stage to
    `input_schema == output_schema == its own slice type`. That means raw, not-yet-normalized input
    must be carried *in the same `IntakeSlice` fields* — `message_body` holds the raw email/callback
    text (or is left as the caller supplied it for web form) going in, and `IntakeStage.run()`
    overwrites the slice in place with the normalized version, exactly mirroring how `_make_node`
    already reads `state.intake` as input and writes the stage's return value back to `state.intake`
    as output. This is a reuse of Feature 01's existing node-wiring pattern, not a rewiring of it.
  - `app/schemas/pipeline.py`'s `TriggerPipelineRunRequest` — already shaped for the web-form channel
    (`source_channel`, `name`, `phone`, `email`, `message_body`, `raw_input_ref`); reused as-is for the
    web-form endpoint's request body.
  - `app/orchestrator/graph.py`'s `default_stages()` — its dict-injection design (`stages: dict[str,
    Stage]` passed into `build_graph`) is exactly the swap point this feature needs; only the
    `"intake"` entry changes, no edge/wiring changes.
  - `app/orchestrator/tool_scope.py` — reused with an empty `allowed_tools` set, per the spec's "no
    external tool access beyond parsing/normalization logic." No new scoping logic.
  - `app/routers/health.py`'s router-registration pattern (`APIRouter` + `app.include_router(...)` in
    `main.py`) — followed as-is for the new leads router.
- Duplication Risk Flagged: none found — no parsing/normalization code exists anywhere yet.
- Modify: `app/orchestrator/graph.py` (`default_stages()`'s `"intake"` entry), `app/schemas/pipeline.py`
  (add two request schemas for the email and callback channels), `backend/main.py` (register the new
  router).
- New: `app/orchestrator/stages/` package (`__init__.py` + `intake.py`), `app/routers/leads.py`.
- Navigation Relationships Flagged: none — backend-only, no UI surface, same as Feature 01. The three
  intake channels are external API integration points (a client's own web form, an inbound email
  handler, a callback transcript source), not an in-app page.

System Impact Map
```
FEATURE 02 — Intake Parsing & Normalization Stage
│
├── Backend
│   ├── app/orchestrator/stages/intake.py (new) — IntakeStage(Stage[IntakeSlice, IntakeSlice]):
│   │     web-form direct field mapping; email header/body extraction; callback transcript handling;
│   │     phone/email formatting normalization; empty-message and low-identifiability flagging
│   ├── app/routers/leads.py (new) — POST /leads/webform, /leads/email, /leads/callback; each builds
│   │     the initial LeadPipelineState.intake from its channel-specific request schema, generates a
│   │     lead_id (uuid4), and calls run_pipeline()
│   └── app/schemas/pipeline.py (modify) — add EmailIntakeRequest {raw_text}, CallbackIntakeRequest
│         {transcript}; TriggerPipelineRunRequest (existing) reused for the web-form endpoint
│
├── Database
│   └── none — IntakeSlice persists via Feature 01's existing StageTrace mechanism, no new table
│
├── Existing Systems (reused, not duplicated)
│   ├── app/orchestrator/contracts.py — Stage ABC
│   ├── app/orchestrator/state.py — IntakeSlice (as-is, no changes)
│   ├── app/orchestrator/graph.py — default_stages() stub-swap point, run_pipeline() entry
│   └── app/orchestrator/tool_scope.py — empty-allowed-tools reuse
│
├── Navigation
│   └── none this feature — backend/API only
│
└── AI
    └── none — this stage is explicitly non-AI (parsing/normalization logic only, no LLM call)
```

Implementation Order (Dependency Graph)
1. **app/orchestrator/stages/intake.py** — `IntakeStage` implementing `Stage[IntakeSlice, IntakeSlice]`:
   `name = "intake_parsing"`, `state_slice = "intake"`, `allowed_tools = frozenset()`. `run()` branches
   on `data.source_channel`: `web_form` → normalize phone/email formatting only (fields already
   structured); `email` → parse sender name/email/subject from `message_body`'s raw text (stdlib
   `email` module), replace `message_body` with the extracted body only, fall back to treating the
   entire raw text as `message_body` with structured fields left null if parsing fails; `callback` →
   extract a phone number from the transcript via regex if present, leave `message_body` as the
   transcript. Sets `empty_message=True` when the resulting body is blank/whitespace-only, and
   `low_identifiability=True` when name, phone, and email are all null after normalization. Existing
   files: none read beyond `state.py`'s `IntakeSlice` type. New files: `app/orchestrator/stages/
   __init__.py`, `app/orchestrator/stages/intake.py`. Dependencies: `contracts.py`, `state.py`.
   Validation: unit tests for all three channels plus the four edge cases in the feature spec.
2. **app/schemas/pipeline.py** — add `EmailIntakeRequest {raw_text: str}` and `CallbackIntakeRequest
   {transcript: str}` alongside the existing `TriggerPipelineRunRequest`. Existing files: `app/schemas/
   pipeline.py`. New files: none. Dependencies: none. Validation: schema round-trip test.
3. **app/routers/leads.py** — three POST endpoints, one per channel. Each: validates the request body
   against its schema, builds `LeadPipelineState(intake=IntakeSlice(source_channel=..., <raw fields>,
   received_at=now))`, generates `lead_id = str(uuid4())`, calls `run_pipeline(lead_id, initial_state)`
   (Feature 01's existing entry point — no changes to it), returns the resulting `PipelineRunOut`
   (existing schema). Existing files: `app/orchestrator/graph.py` (`run_pipeline`), `app/schemas/
   pipeline.py` (`PipelineRunOut`). New files: `app/routers/leads.py`. Dependencies: steps 1-2.
   Validation: integration test per channel, using `TestClient` against a test DB (same pattern
   `test_health.py`/`conftest.py` already establish).
4. **app/orchestrator/graph.py** — in `default_stages()`, replace the `"intake"` entry's `_StubStage`
   with `IntakeStage()`. Existing files: `app/orchestrator/graph.py`. New files: none. Dependencies:
   step 1. Validation: the existing graph tests (`test_orchestrator_graph.py`) continue passing with a
   real intake stage in place of the stub; add one new graph-level test that a full web-form payload
   reaches `classify_stage` with `state.intake` populated (classification itself still stubbed).
5. **backend/main.py** — `app.include_router(leads.router)`, following the existing `health.router`
   registration line. Existing files: `backend/main.py`. New files: none. Dependencies: step 3.
   Validation: `TestClient(app)` can reach the three new routes (already covered by step 3's tests).

Architecture Rule Changes
- [x] "Each pipeline stage's real (non-stub) implementation lives in its own module under
  `app/orchestrator/stages/`, one file per stage, implementing the `Stage` contract from
  `contracts.py`." Conflict check: none found — Feature 01 intentionally shipped no stage logic (only
  stubs in `graph.py` itself) and never specified where real per-stage business logic should live; this
  fills that gap before Features 03-07 each face the identical question independently. **Applied to
  `.claude/portfolio-reference.md`'s Key Decisions.**
- [x] "A stage whose `input_schema` equals its `output_schema` (per Feature 01's `default_stages()`
  convention) receives not-yet-normalized data in the same slice fields it will overwrite — the caller
  constructing the initial `LeadPipelineState` is responsible for seeding those fields, not for
  pre-normalizing them." Conflict check: none found — this makes explicit a convention Feature 01's
  `_StubStage` design implied (same schema for input/output) but never stated for a stage with real
  transformation logic. **Applied to `.claude/portfolio-reference.md`'s Key Decisions.**

Feature-Specific Requirements
- Exact regex/format rules for phone normalization and email casing/whitespace trimming are
  implementation detail local to `intake.py`, not promoted to Key Decisions.
- The three specific route paths (`/leads/webform`, `/leads/email`, `/leads/callback`) are
  feature-specific API surface, not an architecture rule.

Risks
- Risk: Email parsing (extracting sender/subject from raw text) is inherently lossy for malformed or
  non-standard email text. Mitigation: spec's own edge case already defines the fallback — on parse
  failure, treat the entire raw text as `message_body` with structured fields left null, never throw.
- Risk: A stage exception here would halt the pipeline before it starts for that lead, which is worse
  for intake than for a downstream stage since no partial trace exists yet. Mitigation: every
  expected-per-spec condition (empty body, low identifiability, malformed email, missing fields) is
  handled via slice flags/nulls inside `run()`, never raised as an exception; only a truly unexpected
  error (e.g. a bug) reaches the orchestrator's existing catch-and-FAILED handling in `_make_node`.
- Risk: Introducing `app/orchestrator/stages/` as a new package boundary could be read ambiguously by
  a future feature if not stated as a rule now. Mitigation: recorded explicitly as an Architecture Rule
  Change above, before Feature 03 needs to make the same choice.

Acceptance Criteria
- [ ] A web-form payload with all fields present produces a fully-populated `IntakeSlice`.
- [ ] Raw email text produces a record with extracted sender fields and the full body retained in
  `message_body`.
- [ ] A callback transcript with no extractable structured fields still produces a valid record with
  the transcript as `message_body`.
- [ ] Every normalized record is tagged with the correct `source_channel`.
- [ ] An empty message body does not raise and results in `empty_message=True`.
- [ ] `IntakeStage` has no successful path to any tool call (`allowed_tools` is empty), verified by a
  boundary test consistent with Feature 01's existing tool-scoping test pattern.
- [ ] `default_stages()["intake"]` is a real `IntakeStage`, not `_StubStage`, and existing
  `test_orchestrator_graph.py` tests still pass unchanged.

Validation Requirements
Step 7 must specifically run the malformed-email fallback case and the all-fields-missing
low-identifiability case — these are the two edge cases most likely to be silently skipped in favor of
the happy-path web-form test. Step 7 should also confirm (by grep, not just test pass/fail) that
`intake.py` never imports a tool binding directly, consistent with Feature 01's existing scoping
discipline.

Predicted Footprint
Files predicted to change: 5 new (`app/orchestrator/stages/__init__.py`, `app/orchestrator/stages/
intake.py`, `app/routers/leads.py`, `app/tests/test_stage_intake.py`, `app/tests/test_router_leads.py`)
+ 3 modified (`app/orchestrator/graph.py`, `app/schemas/pipeline.py`, `backend/main.py`).
Systems predicted to touch: Backend orchestrator package (new stages/ sub-package), API routers,
request/response schemas. No database/migration changes.

--- filled in later, by Step 7, once implementation is verified ---
Actual Footprint
Files actually changed: [pending Step 6/7]
Deviations from plan: [pending Step 6/7]
Rework required: [pending Step 6/7]
