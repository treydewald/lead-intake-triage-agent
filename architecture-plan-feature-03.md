IMPLEMENTATION PLAN
====================

Feature / Round: Feature 03 — Intent Classification Stage
Classification: New feature, AI integration, Architecture change
Planning Depth: Deep — first feature to call an external AI system, requires extending the `Stage`
contract itself (a stage that reads one slice and writes a different one), requires resolving how a
stage's own expected external-system failure reaches Human Review without bypassing it, and
introduces the first real tool binding the `ToolRegistry` has ever held in production. Four+ existing
systems touched: `contracts.py`, `graph.py`, `tool_scope.py`'s registry (populated for the first
time), and `state.py`.

Objective
Replace `graph.py`'s "classification" stub with a real `IntentClassificationStage` that calls a local
Ollama model (via a new registered tool binding) to produce an intent label and confidence score for a
normalized lead, so low-confidence and outright classification failures both flow — without any new
graph edges — into the existing confidence-threshold routing that sends a lead to Human Review instead
of CRM Write.

Existing Systems Analysis
- Reusable:
  - `app/orchestrator/state.py`'s `ClassificationSlice` — already declares exactly the fields this
    feature's spec requires as output (`intent_label`, `confidence_score`, `model_used`). No
    state-schema change needed.
  - `app/orchestrator/tool_scope.py`'s `ToolRegistry`/`ScopedToolProxy` — the enforced tool-access
    boundary is already correct for this use case; reused as-is, not modified.
  - `app/orchestrator/graph.py`'s `default_stages()` dict-injection stub-swap point, and
    `_route_after_enrich`'s existing confidence-threshold routing — **this is the key reuse finding**:
    a classification result with `confidence_score` `None` or below `settings.confidence_threshold`
    already routes to Human Review with zero graph.py edge changes, once it passes through Enrichment.
    No new conditional edge is needed for the "classification failed" case — see Architecture Rule
    Change #2 below for how a failure is represented so it hits this existing routing.
  - `ollama` python client (`ollama==0.3.3`, already pinned in `backend/requirements.txt`) and
    `Settings.ollama_base_url` / `Settings.ollama_model` (`app/core/config.py`) — both already present
    from Step 4 bootstrap; no new dependency or config field needed. A local `llama3.2:3b` model is
    already pulled in this environment (`.claude/pipeline-reference.md`'s Deviations section).
  - `app/orchestrator/stages/` package convention, established as a Key Decision by Feature 02 — the
    new stage module goes here, one file, implementing the `Stage` contract.
  - Naming precedent: `app/tests/test_orchestrator_tool_scope.py` already registers a demo tool named
    `"ollama_classify"` scoped to a stage named `"intent_classification"`, anticipating exactly this
    feature. Reused verbatim rather than inventing a different tool name.
- Duplication Risk Flagged: none found — no classification or tool-binding-registration code exists
  anywhere yet.
- Modify:
  - `app/orchestrator/contracts.py` — `Stage` needs a way to declare that it reads a *different* slice
    than the one it writes (see Architecture Rule Change #1).
  - `app/orchestrator/graph.py` — `_make_node` must resolve a stage's input from that declaration;
    `default_stages()`'s `"classification"` entry becomes the real stage; `build_production_graph()`
    must populate `ToolRegistry` with real bindings (today it always constructs an empty one, since no
    prior stage needed a real tool).
- New:
  - `app/orchestrator/stages/intent_classification.py` — `IntentClassificationStage`.
  - `app/orchestrator/tools/` package (`__init__.py` exporting `register_default_tools`,
    `ollama_tools.py` holding the actual Ollama call) — the first real tool bindings the project has
    registered; sibling convention to `stages/` for external-system bindings (see Architecture Rule
    Change #3).
- Navigation Relationships Flagged: none — backend-only, matches Features 01/02; no UI surface.

System Impact Map
```
FEATURE 03 — Intent Classification Stage
│
├── Backend
│   ├── app/orchestrator/stages/intent_classification.py (new) — IntentClassificationStage:
│   │     empty-message short-circuit, retry-once-then-fail-closed call/validation policy
│   ├── app/orchestrator/tools/ollama_tools.py (new) — thin classify_intent(client, model, text) call,
│   │     temperature=0 / JSON-mode for deterministic structured output
│   ├── app/orchestrator/tools/__init__.py (new) — register_default_tools(registry, settings)
│   ├── app/orchestrator/contracts.py (modify) — Stage gains input_slice + effective_input_slice
│   └── app/orchestrator/graph.py (modify) — _make_node reads effective_input_slice; default_stages()
│         real classification entry; build_production_graph() calls register_default_tools()
│
├── Database
│   └── none — ClassificationSlice persists via Feature 01's existing StageTrace mechanism unchanged
│
├── Existing Systems (reused, not duplicated)
│   ├── app/orchestrator/contracts.py — Stage ABC (extended, not replaced)
│   ├── app/orchestrator/state.py — ClassificationSlice, IntakeSlice (as-is, no changes)
│   ├── app/orchestrator/tool_scope.py — ToolRegistry/ScopedToolProxy (as-is)
│   ├── app/orchestrator/graph.py — default_stages() swap point, _route_after_enrich confidence routing
│   └── app/core/config.py — ollama_base_url, ollama_model (as-is)
│
├── Navigation
│   └── none this feature — backend/AI only
│
└── AI
    ├── Context builder: lead_text assembled from IntakeSlice.message_body (+ name/phone/email if
    │     present) inside the stage, not the tool binding
    ├── Structured generation: Ollama chat call with format="json", temperature=0, fixed label set
    │     {buyer, browser, spam} stated in the system prompt
    └── Output validation: stage validates label ∈ fixed set and confidence ∈ [0.0, 1.0] before
          accepting the tool's response; retries once on any failure (call error or invalid response),
          then returns a FAILED sentinel rather than raising
```

Implementation Order (Dependency Graph)
1. **app/orchestrator/contracts.py** — add `input_slice: ClassVar[str | None] = None` to `Stage`, plus
   a read-only `effective_input_slice` property returning `self.input_slice or self.state_slice`. A
   stage that doesn't set `input_slice` (every existing stage, including `IntakeStage`) is unaffected —
   `effective_input_slice` falls back to `state_slice`, identical to today's behavior. Existing files:
   `contracts.py`. New files: none. Dependencies: none. Validation: existing `test_orchestrator_
   contracts.py` unaffected; add one test asserting a stage with no `input_slice` set falls back to
   `state_slice`, and one asserting an explicit `input_slice` overrides it.
2. **app/orchestrator/tools/** (new package) — `ollama_tools.py`: `classify_intent(client, model:
   str, lead_text: str) -> dict` issues one `client.chat(...)` call with `format="json"`,
   `options={"temperature": 0}`, a system prompt stating the fixed label set, and returns the parsed
   `{"intent_label": ..., "confidence_score": ...}` dict with no validation/retry logic (that's the
   stage's job, kept out of the tool so the tool stays a thin, swappable binding). `__init__.py`:
   `register_default_tools(registry: ToolRegistry, settings: Settings) -> None` constructs one
   `ollama.Client(host=settings.ollama_base_url)`, binds it via `functools.partial(classify_intent,
   client, settings.ollama_model)`, and calls `registry.register("ollama_classify", bound_fn)`. Existing
   files: `tool_scope.py` (ToolRegistry, unmodified), `core/config.py` (settings, unmodified). New
   files: `app/orchestrator/tools/__init__.py`, `app/orchestrator/tools/ollama_tools.py`. Dependencies:
   none beyond the already-pinned `ollama` package. Validation: unit test for `classify_intent` using an
   injected fake client double (a plain object with a `.chat()` method returning a canned response, same
   lightweight style `test_orchestrator_tool_scope.py` already uses — no mocking library needed); unit
   test for `register_default_tools` asserting the registry ends up with a callable named
   `"ollama_classify"`.
3. **app/orchestrator/stages/intent_classification.py** — `IntentClassificationStage(Stage[IntakeSlice,
   ClassificationSlice])`: `name = "intent_classification"`, `input_schema = IntakeSlice`,
   `output_schema = ClassificationSlice`, `input_slice = "intake"`, `state_slice = "classification"`,
   `allowed_tools = frozenset({"ollama_classify"})`. `run(data: IntakeSlice, tools) ->
   ClassificationSlice`: if `data.empty_message` is `True`, return
   `ClassificationSlice(intent_label=None, confidence_score=0.0,
   model_used="empty_message_short_circuit")` without calling the tool (deterministic, no wasted LLM
   call on input with nothing to classify). Otherwise, build `lead_text` from `message_body` (+
   name/phone/email if present), call `tools.call("ollama_classify", lead_text)` inside a bounded
   retry-once loop: on a raised exception, retry once; on success, validate `intent_label` is one of
   `{buyer, browser, spam}` and `confidence_score` is a float in `[0.0, 1.0]` — an invalid response also
   gets one retry. If both attempts fail (exception) or both return an invalid response, return
   `ClassificationSlice(intent_label=None, confidence_score=0.0,
   model_used="classification_failed")` — never raise for this per-spec-expected failure (see
   Architecture Rule Change #2). Only a genuinely unexpected exception (e.g. a bug in the tool wiring
   itself, not the two named failure modes) is allowed to propagate. Existing files: `state.py`
   (`IntakeSlice`, `ClassificationSlice` — unchanged), `contracts.py` (per step 1). New files:
   `app/orchestrator/stages/intent_classification.py`. Dependencies: steps 1-2. Validation: unit tests
   per Acceptance Criteria below, using a fake tool function registered directly into a `ToolRegistry`
   (no real Ollama call in the core test suite).
4. **app/orchestrator/graph.py** — `_make_node` reads `slice_in = getattr(state, stage.
   effective_input_slice)` instead of `stage.state_slice`; `default_stages()`'s `"classification"` entry
   becomes `IntentClassificationStage()`; `build_production_graph()` now does `registry =
   ToolRegistry(); register_default_tools(registry, settings)` before calling `build_graph(...)`
   instead of passing an always-empty `ToolRegistry()`. Existing files: `graph.py`. New files: none.
   Dependencies: steps 1-3. Validation: existing `test_orchestrator_graph.py` tests continue passing
   (the `_FakeStage`/`_make_stages` fixtures don't set `input_slice`, so `effective_input_slice` falls
   back to `state_slice` exactly as before — no fixture changes needed). Update
   `test_default_stages_web_form_payload_reaches_classify_with_normalized_intake` to register a fake
   `"ollama_classify"` tool via `ToolRegistry` before building the graph, so the test demonstrates the
   real classification stage's *success* path reaching the still-stubbed `enrich_stage` — not merely
   confirming failure at classify for the wrong reason (an unregistered tool), mirroring how Feature
   02's version of this test proved intake succeeding and reaching the (then-stubbed) classify stage.
   Add one new graph-level test proving a `confidence_score` below `settings.confidence_threshold`
   (from a real, non-stub `IntentClassificationStage`) reaches Human Review after passing through the
   still-stubbed enrich stage — actually, since `enrichment` is still a stub that raises
   `NotImplementedError`, this specific new test must inject a fake enrichment stage (same pattern as
   `_make_stages`) alongside the real classification stage, to isolate "does a low/failed confidence
   score reach `_route_after_enrich` correctly" from "is enrichment implemented yet" (it isn't, until
   Feature 04).

Architecture Rule Changes
- [ ] **"A stage may declare `input_slice` (a `ClassVar[str | None]`, default `None`) when it reads a
  different `LeadPipelineState` slice than the one it writes; `_make_node` resolves the actual input
  via `Stage.effective_input_slice` (`input_slice or state_slice`), never `state_slice` directly. A
  stage that transforms its own slice in place (`input_slice` unset) is the special case where both are
  equal."** — Conflict check: generalizes rather than contradicts Feature 02's existing Key Decision
  ("A stage whose `input_schema` equals its `output_schema`... receives not-yet-normalized data in the
  same slice fields it will overwrite"). That rule remains true, unchanged, for `IntakeStage` — it was
  always the same-slice special case of this more general rule, which nothing before now needed to
  state explicitly because no stage had read a slice other than its own. **Resolution:** restate the
  existing Key Decision as the special case of this new general one, in the same Key Decisions bullet,
  rather than leaving two independently-worded rules that could look like they conflict.
- [ ] **"A stage's own recoverable, per-spec-expected external-system failure (an LLM call failing
  after one retry, or returning an invalid/out-of-set response after one retry) must be encoded as data
  in the stage's own output slice — never raised as a `Stage.run()` exception — so it flows through the
  graph's existing conditional-confidence routing into Human Review instead of short-circuiting the
  entire run to `RunStatus.FAILED`/END via `_make_node`'s exception handler. Raising from `Stage.run()`
  stays reserved for genuinely unexpected/bug-level errors, never a failure mode a feature's own spec
  already anticipates."** — Conflict check: none found; generalizes into an explicit, project-wide rule
  what Feature 02's implementation plan only stated as a local risk-mitigation note for parsing
  edge cases. Feature 03 is the first stage to face a real *external-system* failure mode, so nothing
  in Key Decisions addressed this distinction until now.
- [ ] **"Real tool bindings for external systems (LLM calls, lookups, CRM writes) are registered into
  `ToolRegistry` via one dedicated module per external system under `app/orchestrator/tools/`, wired
  together by a single `register_default_tools(registry, settings)` factory that
  `build_production_graph()` calls — the tools-side analogue of the existing 'one file per stage under
  `app/orchestrator/stages/`' rule. A stage module still never constructs or imports a tool binding
  directly; it only ever reaches one through its `ScopedToolProxy`."** — Conflict check: none found;
  extends Feature 02's "one file per stage" convention to its natural analogue for tools, which nothing
  addressed because `build_production_graph()` has, until now, always constructed an empty
  `ToolRegistry()` — no prior stage needed a real tool binding.

Feature-Specific Requirements
- The exact system prompt text, the empty-message short-circuit's specific sentinel values
  (`"empty_message_short_circuit"`, `"classification_failed"`), and the fixed label set `{buyer,
  browser, spam}` are feature-local detail, not promoted to Key Decisions.
- The optional hosted-LLM-API fallback path named in the feature spec is intentionally **not** built
  this round: `.claude/portfolio-reference.md`'s existing Key Decision already states "If Tier 2's
  Classification Accuracy Benchmark (Feature 09) shows this model is insufficiently reliable, only then
  wire the optional `FALLBACK_LLM_API_KEY` path — do not add it preemptively." This plan satisfies the
  spec's "support an optional fallback path" language by leaving the seam open (a stage may hold more
  than one entry in `allowed_tools`; `fallback_llm_api_key` is already a config field) without invoking
  it — consistent with the standing Key Decision, which takes precedence over building it speculatively
  now.

Risks
- Risk: A local Ollama daemon unavailable in some environment (fresh clone, CI) would make every
  classification fail-closed to Human Review, silently masking an infra/config problem as a normal
  low-confidence result. Mitigation: the `model_used="classification_failed"` sentinel is queryable in
  `StageTrace` and distinguishable from a genuine low-confidence label — Feature 09's benchmark harness
  is the eventual place this gets surfaced, not this feature's job to add new alerting for.
- Risk: The new `input_slice` capability, if used carelessly by a future stage, could weaken the
  "declared slice" boundary the project's Critical risk depends on. Mitigation: `input_slice` stays a
  single explicit `ClassVar` (never a wildcard/multi-slice list), reviewed at Step 5.5 planning time for
  every future feature exactly as this plan does now — the boundary is widened from "one slice" to "one
  input slice + one output slice," never made implicit.
- Risk: Encoding an LLM failure as slice data instead of an exception could mask a genuine bug (e.g. a
  `TypeError` from broken tool wiring) inside what looks like an ordinary low-confidence routing
  outcome. Mitigation: only the two named per-spec failure modes (call exception, invalid response) are
  caught inside the bounded retry loop; any other exception is not caught and still propagates to
  `_make_node`'s existing FAILED/END handling, preserving Feature 02's "an unexpected error still halts
  the run visibly" guarantee.
- Risk: Ollama's default sampling could violate the spec's determinism acceptance criterion. Mitigation:
  `ollama_tools.classify_intent` fixes `temperature=0` and `format="json"` explicitly rather than
  relying on model defaults.

Acceptance Criteria
- [ ] A clearly buyer-intent message (fake tool returns `buyer` at high confidence) produces
  `intent_label="buyer"` with a high `confidence_score`.
- [ ] An empty or near-empty message body (`data.empty_message=True`) short-circuits without calling
  the tool and produces `confidence_score=0.0`, `intent_label=None`,
  `model_used="empty_message_short_circuit"`.
- [ ] A tool call that raises on both the initial attempt and the retry produces the
  `"classification_failed"` sentinel and does **not** raise out of `run()`.
- [ ] A tool call returning a label outside `{buyer, browser, spam}` on both attempts produces the same
  `"classification_failed"` sentinel, never a raised exception.
- [ ] A tool call that fails once then succeeds on retry returns the successful result — the
  retry-then-recover path is exercised by its own test, not only "always fails" / "always succeeds."
- [ ] `IntentClassificationStage.allowed_tools` contains only `"ollama_classify"` — a boundary test
  proves calling any other tool name through this stage's proxy raises `OutOfScopeToolError`.
- [ ] Repeated calls with the same fake-tool response produce an identical `ClassificationSlice`
  (determinism).
- [ ] `default_stages()["classification"]` is a real `IntentClassificationStage`, not `_StubStage`, and
  `build_production_graph()` registers a real `"ollama_classify"` tool via `register_default_tools`.
- [ ] A low-confidence or `"classification_failed"` result, once it passes through Enrichment, routes to
  Human Review via the existing (unmodified) `_route_after_enrich` — proven by a graph-level test, with
  no new conditional edges added to `graph.py`.

Validation Requirements
Step 7 must confirm, by grep and not just test pass/fail, that `intent_classification.py` never imports
`ollama` directly — it reaches the model only through `tools.call("ollama_classify", ...)`, the same
tool-scoping discipline check Feature 02's plan required for `intake.py`. Step 7 must also confirm the
updated `test_orchestrator_graph.py` test genuinely exercises the real classification stage's success
path (registers a fake tool) rather than passing for the old, no-longer-true reason (an unimplemented
stub). If a local Ollama with `llama3.2:3b` is reachable in the verification environment (per this
session's Step 4 deviation note), Step 7 may additionally run one real end-to-end smoke call through
`ollama_tools.classify_intent` and report whether the live model's output actually validates against
the fixed label set — informative for Feature 09's future benchmark, not required to pass this gate if
Ollama isn't reachable.

Predicted Footprint
Files predicted to change: 6 new (`app/orchestrator/tools/__init__.py`, `app/orchestrator/tools/
ollama_tools.py`, `app/orchestrator/stages/intent_classification.py`, `app/tests/
test_stage_intent_classification.py`, `app/tests/test_orchestrator_tools.py`, `app/tests/
test_orchestrator_contracts.py` extension counted as modify not new — see below) + 4 modified
(`app/orchestrator/contracts.py`, `app/orchestrator/graph.py`, `app/tests/test_orchestrator_graph.py`,
`app/tests/test_orchestrator_contracts.py`).
Systems predicted to touch: `Stage` contract (extended), graph node-input wiring, `ToolRegistry`
production population (first real tool bindings), a new `app/orchestrator/tools/` package. No
database/migration changes.

--- filled in later, by Step 7, once implementation is verified ---
Actual Footprint
Files actually changed: [pending Step 7]
Deviations from plan: [pending Step 7]
Rework required: [pending Step 7]
