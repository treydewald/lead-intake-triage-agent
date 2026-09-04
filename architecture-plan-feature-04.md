IMPLEMENTATION PLAN
====================

Feature / Round: Feature 04 — Data Enrichment Stage
Classification: New feature, Cross-system integration
Planning Depth: Standard — reuses the `input_slice`/tool-registry machinery Feature 03 already
generalized (no `Stage` contract change needed), but introduces the project's first HubSpot
integration code and a new cross-slice question ("what does 'merge into the lead record' mean when
each stage only owns one slice") that needs an explicit architecture answer before Step 6 writes code.

Objective
Replace `graph.py`'s "enrichment" stub with a real `DataEnrichmentStage` that fills missing lead
fields via a read-only HubSpot contact search (exact match on phone/email when available, a
confidence-scored fuzzy name match otherwise), merging only fields Intake Parsing left null and never
raising on a lookup failure — while remaining architecturally incapable of reaching HubSpot's write
path, which stays exclusively Feature 05's.

Existing Systems Analysis
- Reusable:
  - `app/orchestrator/state.py`'s `EnrichmentSlice` — already exists with `resolved_fields`/`sources`;
    extended (see Modify below), not replaced.
  - `app/orchestrator/contracts.py`'s `input_slice`/`effective_input_slice` (Feature 03) — Enrichment
    is the second stage that reads a different slice than it writes (`intake` in, `enrichment` out);
    no contract change needed, this is exactly the mechanism it exists for.
  - `app/orchestrator/graph.py`'s `default_stages()` stub-swap point and `_STAGE_ORDER` (already lists
    `("enrichment", "data_enrichment", "Feature 04")`) — no graph-shape or routing change; enrichment's
    own success/failure never needs a new conditional edge, since `_route_after_enrich` already routes
    purely on `classification.confidence_score`, set by the upstream stage.
  - `app/orchestrator/tool_scope.py`'s `ToolRegistry`/`ScopedToolProxy` — reused as-is.
  - `app/orchestrator/tools/` one-module-per-external-system convention (Feature 03) — HubSpot's
    binding goes in a new sibling module, same pattern as `ollama_tools.py`.
  - `Settings.hubspot_base_url` / `Settings.hubspot_access_token` (`app/core/config.py`) — already
    present from Step 4 bootstrap; no new config field needed. `httpx` is already pinned
    (`backend/requirements.txt`) — no new dependency.
  - The project's existing recoverable-failure Key Decision (Feature 03) — a lookup timeout is another
    instance of "encode as output-slice data, never raise," not a new rule (see Architecture Rule
    Change #2, a wording generalization, not a new rule).
  - **Naming precedent found in `app/tests/test_orchestrator_tool_scope.py`** (already present, written
    ahead of this feature): `test_classification_stage_proxy_rejects_hubspot_write_call` and
    `test_out_of_scope_call_is_rejected_not_silently_ignored` both register a tool named
    `"hubspot_write"` and assert a `"data_enrichment"`-named proxy with an empty `allowed_tools` cannot
    reach it. This fixes two things ahead of time: Feature 05's eventual write tool must be named
    `"hubspot_write"` (reused verbatim, not invented differently), and confirms `"data_enrichment"` is
    the correct stage `name`. It does not by itself require a HubSpot-backed lookup — but it makes one
    a strong, low-risk choice: this plan's own new `"hubspot_search_contact"` tool can never collide
    with, or be mistaken for, `"hubspot_write"`, and the boundary test between them becomes a direct,
    concrete demonstration of the project's stated Critical risk using two tools on the *same* external
    system rather than two unrelated ones.
- Duplication Risk Flagged: none found — no lookup/search code or HubSpot client code exists anywhere
  yet (grep-confirmed: `hubspot` only appears in config, `state.py` doc-comments, and test fixture
  strings, never in a real tool binding).
- Modify:
  - `app/orchestrator/state.py`'s `EnrichmentSlice` — needs `attempted_fields`, `match_confidence`,
    `conflicts`, and `lookup_error`, none of which exist today, to satisfy the spec's edge cases (a
    field left missing, a fuzzy match's confidence, a conflicting-but-not-merged value, and a lookup
    failure) without any of them raising an exception (see Architecture Rule Change #2).
  - `app/orchestrator/tools/__init__.py` — `register_default_tools` gains a second registration
    alongside the existing Ollama one.
  - `app/orchestrator/graph.py` — `default_stages()["enrichment"]` becomes `DataEnrichmentStage()`
    (one line + one import; no other change, per the Reusable findings above).
- New:
  - `app/orchestrator/tools/hubspot_tools.py` — `search_contact(...)`, read-only.
  - `app/orchestrator/stages/data_enrichment.py` — `DataEnrichmentStage`.
- Navigation Relationships Flagged: none — backend-only, matches Features 01-03; no UI surface yet.

System Impact Map
```
FEATURE 04 — Data Enrichment Stage
│
├── Backend
│   ├── app/orchestrator/stages/data_enrichment.py (new) — DataEnrichmentStage: detects missing
│   │     fields, picks exact-key or fuzzy-name query, applies match-confidence threshold, merges
│   │     without overwriting, records conflicts/lookup_error instead of raising
│   ├── app/orchestrator/tools/hubspot_tools.py (new) — search_contact(client, base_url, token, *,
│   │     phone=None, email=None, name=None) -> dict | None; one CRM Search API call, no confidence
│   │     logic (kept in the stage, same thin-tool principle as ollama_tools.classify_intent)
│   ├── app/orchestrator/tools/__init__.py (modify) — registers "hubspot_search_contact" alongside
│   │     the existing "ollama_classify"
│   ├── app/orchestrator/state.py (modify) — EnrichmentSlice gains attempted_fields, match_confidence,
│   │     conflicts, lookup_error
│   └── app/orchestrator/graph.py (modify) — default_stages()["enrichment"] = DataEnrichmentStage()
│
├── Database
│   └── none — EnrichmentSlice persists via Feature 01's existing StageTrace mechanism unchanged
│
├── Existing Systems (reused, not duplicated)
│   ├── app/orchestrator/contracts.py — Stage.input_slice/effective_input_slice (as-is, Feature 03)
│   ├── app/orchestrator/tool_scope.py — ToolRegistry/ScopedToolProxy (as-is)
│   ├── app/orchestrator/graph.py — _STAGE_ORDER, default_stages() swap point, _route_after_enrich
│   │     (unmodified — still routes purely on classification.confidence_score)
│   └── app/core/config.py — hubspot_base_url, hubspot_access_token (as-is)
│
├── Navigation
│   └── none this feature — backend only
│
└── AI
    └── none — this feature is deterministic lookup + string-similarity scoring (stdlib difflib), not
          an LLM call; no new AI system introduced
```

Implementation Order (Dependency Graph)
1. **app/orchestrator/state.py** — extend `EnrichmentSlice` with `attempted_fields: list[str] =
   Field(default_factory=list)`, `match_confidence: float | None = None`, `conflicts: dict[str, Any] =
   Field(default_factory=dict)`, `lookup_error: str | None = None`, alongside the existing
   `resolved_fields`/`sources`. Existing files: `state.py`. New files: none. Dependencies: none.
   Validation: extend `test_orchestrator_state.py` with a default-construction test for the four new
   fields (empty list/dict, `None`) — no existing test references `EnrichmentSlice`'s shape today
   (grep-confirmed), so nothing breaks.
2. **app/orchestrator/tools/hubspot_tools.py** (new) — `search_contact(client: httpx.Client,
   base_url: str, token: str | None, *, phone: str | None = None, email: str | None = None, name:
   str | None = None) -> dict | None`: builds one CRM Search API request (`POST
   {base_url}/crm/v3/objects/contacts/search`) — an `EQ` filter on `phone` or `email` when given
   (preferred, checked in that order), else a `CONTAINS_TOKEN` filter on `name`; `Authorization:
   Bearer {token}` header. Returns `results[0]["properties"]` (a plain dict of whatever HubSpot
   returns) if any result exists, else `None`. Raises on HTTP/timeout error — deliberately not caught
   here, matching `classify_intent`'s thin-binding precedent; the stage owns all failure handling.
   `tools/__init__.py`: `register_default_tools` additionally constructs one shared
   `httpx.Client(timeout=5.0)` and calls `registry.register("hubspot_search_contact",
   functools.partial(search_contact, client, settings.hubspot_base_url,
   settings.hubspot_access_token))`. Existing files: `tool_scope.py` (as-is), `core/config.py` (as-is).
   New files: `app/orchestrator/tools/hubspot_tools.py`. Modified files: `app/orchestrator/tools/
   __init__.py`. Dependencies: none beyond already-pinned `httpx`. Validation: unit tests for
   `search_contact` using an injected fake `httpx.Client` double (same lightweight style as Feature
   03's fake Ollama client — no mocking library) covering an exact-match hit, a no-result response, and
   an HTTP-error passthrough; extend `test_orchestrator_tools.py`'s `register_default_tools` test to
   also assert `"hubspot_search_contact"` is registered.
3. **app/orchestrator/stages/data_enrichment.py** (new) — `DataEnrichmentStage(Stage[IntakeSlice,
   EnrichmentSlice])`: `name = "data_enrichment"`, `input_schema = IntakeSlice`, `output_schema =
   EnrichmentSlice`, `input_slice = "intake"`, `state_slice = "enrichment"`, `allowed_tools =
   frozenset({"hubspot_search_contact"})`. `run(data, tools) -> EnrichmentSlice`:
   - `missing = [f for f in ("name", "phone", "email") if getattr(data, f) is None]`; if empty, return
     `EnrichmentSlice()` (no-op pass-through — the graph's existing `_write_trace` still logs a trace
     entry for every node unconditionally, satisfying the "still logs a trace entry" edge case with no
     stage-level code needed for it).
   - Pick the query: `phone` if present, else `email` if present (both exact-key, `match_confidence =
     1.0` on any hit), else `name` if present (fuzzy path — see below), else return
     `EnrichmentSlice(attempted_fields=missing)` (nothing to search by).
   - Call `tools.call("hubspot_search_contact", **{key: value})` inside a `try/except Exception`; on
     exception, return `EnrichmentSlice(attempted_fields=missing, lookup_error=str(exc))` — never
     raise (Architecture Rule Change #2).
   - `None` result -> `EnrichmentSlice(attempted_fields=missing)`.
   - Name-query path only: compute `confidence = difflib.SequenceMatcher(None, data.name.lower(),
     str(match.get("name", "")).lower()).ratio()`; if `confidence < _MATCH_CONFIDENCE_THRESHOLD`
     (module constant, `0.85`), return `EnrichmentSlice(attempted_fields=missing,
     match_confidence=confidence)` without merging anything.
   - Otherwise walk `("name", "phone", "email")`: a candidate value present in the match result and
     currently `None` on `data`, and in `missing`, goes into `resolved_fields`/`sources` (source =
     `"hubspot_search_contact"`); a candidate value present but *conflicting* with an already-populated
     `data` field goes into `conflicts`, never overwriting; a candidate absent or matching is skipped.
     Return the assembled `EnrichmentSlice(resolved_fields=..., sources=..., attempted_fields=missing,
     match_confidence=confidence, conflicts=...)`.
   Existing files: `state.py` (step 1), `contracts.py` (as-is). New files:
   `app/orchestrator/stages/data_enrichment.py`. Dependencies: steps 1-2. Validation: unit tests per
   Acceptance Criteria below, using a fake tool function registered directly into a `ToolRegistry` (no
   real HubSpot call in the core test suite, matching Feature 03's pattern).
4. **app/orchestrator/graph.py** — add `from app.orchestrator.stages.data_enrichment import
   DataEnrichmentStage`; `default_stages()["enrichment"] = DataEnrichmentStage()`. No other change —
   `_make_node` already resolves `effective_input_slice` generically (Feature 03), and
   `_route_after_enrich` already routes on `classification.confidence_score` alone, so a real
   Enrichment stage's success or failure never needs a new edge. Existing files: `graph.py`. New
   files: none. Dependencies: steps 1-3. Validation: existing `test_orchestrator_graph.py` tests
   continue passing unmodified (its `_FakeStage` fixtures are unaffected). Add one new test: a real
   `IntentClassificationStage` (fake `"ollama_classify"` tool, high confidence) chained into a real
   `DataEnrichmentStage` (fake `"hubspot_search_contact"` tool returning `None` — an all-fields-present
   lead, so a no-op) reaches the still-stubbed `crm_write_stage`, proving the real Enrichment stage's
   success path — not just its unit tests in isolation — reaches the next node correctly, mirroring how
   Feature 03's graph-level test proved the same for classification.

Architecture Rule Changes
- [ ] **"A 'merged lead record' spanning more than one `LeadPipelineState` slice is a read-time
  concept, not a write-time one: a stage never writes into another stage's owned slice to represent a
  merge. Any downstream consumer that needs the full record (CRM Write, Notification, observability)
  treats the owning slice's fields as primary and falls back to another named slice's own fields for
  whatever the owner left null — e.g. Feature 05 reads `IntakeSlice` fields first, falling back to
  `EnrichmentSlice.resolved_fields` for anything `IntakeSlice` left `None`."** — Conflict check: none
  found; this doesn't change or contradict `LeadPipelineState`'s existing docstring ("each stage
  reads/writes only its own declared slice") — it's the first explicit statement of how a *multi-slice*
  merge the docstring's own boundary still allows, since Enrichment is the first feature whose spec uses
  "merge into the lead record" language spanning two slices it doesn't jointly own.
- [ ] **Wording generalization only** (not a new rule): the existing Key Decision "A stage's own
  recoverable, per-spec-expected external-system failure ... must be encoded as data in the stage's own
  output slice, never raised" currently parenthesizes only LLM-call examples. Reworded to: "(e.g., an
  LLM call failing after one retry, an external lookup timing out, or a returned invalid/out-of-set
  response)" — Conflict check: none; Enrichment's lookup-timeout handling is a second real instance of
  the same already-general principle, so the parenthetical is broadened to reflect that rather than the
  rule being restated separately for Enrichment.
- [ ] **"A read-only tool and a write tool for the same external system may share one `tools/
  <system>.py` module (per the existing one-module-per-external-system convention) but must be
  registered under distinct tool names and granted to different stages' `allowed_tools` — never the
  same name gating both."** Concretely: `hubspot_search_contact` (this feature, `data_enrichment`) and
  `hubspot_write` (Feature 05, `hubspot_crm_write` — name fixed by the pre-existing anticipatory tests
  in `test_orchestrator_tool_scope.py`) will eventually live in the same `hubspot_tools.py` module but
  are two independently-scoped bindings. — Conflict check: none found; extends Feature 03's "one
  tools/ module per external system" convention with the read/write-scoping analogue needed the first
  time two different stages touch the same external system, which nothing addressed until now (Ollama
  has only ever had one binding).

Feature-Specific Requirements
- `_MATCH_CONFIDENCE_THRESHOLD = 0.85` and the exact-key-first / fuzzy-name-fallback query order are
  feature-local detail, not promoted to Key Decisions.
- The fuzzy-match confidence score is computed entirely in `DataEnrichmentStage` via stdlib
  `difflib.SequenceMatcher` — no new dependency, and keeps `search_contact` a dumb, swappable binding
  per the existing thin-tool principle.
- Classification's output (`ClassificationSlice`) is never read by this stage — the feature spec's
  "lead record with classification result attached" phrasing describes the conceptual lead-through-
  pipeline, not a literal input to Enrichment's logic, which only ever needs `IntakeSlice` fields.

Risks
- Risk: `HUBSPOT_ACCESS_TOKEN` isn't set in this environment yet (`.claude/pipeline-reference.md`'s
  existing Deviations note — Feature 05 already flagged this as an out-of-band manual step). A real
  search call will fail auth until a human provisions the sandbox token. Mitigation: unit tests use a
  fake tool/client double, matching Feature 03's approach; this is the same standing deviation, now
  also true for read access, not a new blocker.
- Risk: The fuzzy name-match path could produce a false-positive merge (wrong person, similar name).
  Mitigation: threshold set high (`0.85`), and the fuzzy path only runs when neither phone nor email is
  available — an exact identifier is always preferred and treated as definitive (`confidence = 1.0`).
- Risk: HubSpot's Search API response shape (`results[0]["properties"]`) could be mis-parsed silently.
  Mitigation: `search_contact`'s unit tests pin the exact fake response shape used; any KeyError/shape
  mismatch propagates as an exception, caught by the stage as `lookup_error` — visible in the trace,
  never silently swallowed.
- Risk: Adding a `try/except Exception` broadly in the stage risks also swallowing genuine bugs (e.g. a
  `TypeError` from bad tool wiring) as if they were ordinary lookup failures. Mitigation: this mirrors
  Feature 03's already-accepted precedent for the exact same tradeoff (an LLM call's retry loop), and
  the resulting `lookup_error` field stays distinguishable and queryable in `StageTrace` — a Feature 09-
  style benchmark/observability pass is the right place to catch a pattern of unexpected errors, not a
  narrower catch clause here.

Acceptance Criteria
- [ ] A lead record missing `email`, with `phone` present, where the fake `hubspot_search_contact` tool
  returns a match containing `email`, ends up with `resolved_fields["email"]` set and
  `sources["email"] == "hubspot_search_contact"`.
- [ ] A lead record with `name`/`phone`/`email` all already present returns `EnrichmentSlice()`
  unchanged (no tool call made) and the graph's existing per-node trace logging still records an entry
  for it (no stage-level code needed — verified at the graph-test level, not the stage-unit level).
- [ ] A fake tool that raises (simulating a timeout) produces `lookup_error` set and does **not** raise
  out of `run()`, and does not set `RunStatus.FAILED`.
- [ ] `DataEnrichmentStage.allowed_tools` contains only `"hubspot_search_contact"` — a boundary test
  proves calling `"hubspot_write"` through this stage's proxy raises `OutOfScopeToolError` (this test
  can literally extend the pre-existing `test_out_of_scope_call_is_rejected_not_silently_ignored`
  pattern in `test_orchestrator_tool_scope.py`, now against the real stage instead of a bare
  `frozenset()`).
- [ ] A fake match containing a field that conflicts with an already-populated `data` field lands in
  `conflicts`, never in `resolved_fields`, and the already-populated field is unchanged.
- [ ] A name-only query (no phone/email) whose fake match's name similarity scores below `0.85`
  produces no merged fields and a recorded `match_confidence` below threshold.
- [ ] A name-only query scoring at or above `0.85` merges fields exactly as the phone/email path does.
- [ ] `default_stages()["enrichment"]` is a real `DataEnrichmentStage`, not `_StubStage`, and
  `build_production_graph()` registers a real `"hubspot_search_contact"` tool via
  `register_default_tools`.

Validation Requirements
Step 7 must confirm, by grep and not just test pass/fail, that `data_enrichment.py` never imports
`httpx` directly — it reaches HubSpot only through `tools.call("hubspot_search_contact", ...)`, the
same tool-scoping discipline check Features 02/03 required. Step 7 must also confirm the updated
`test_orchestrator_graph.py` test genuinely chains a real `IntentClassificationStage` into a real
`DataEnrichmentStage` (not two more stub substitutions). If `HUBSPOT_ACCESS_TOKEN` is set in the
verification environment, Step 7 may additionally run one real search call through
`hubspot_tools.search_contact` against the sandbox and report the result — informative only, not
required to pass this gate, mirroring Feature 03's optional-live-smoke-call precedent.

Predicted Footprint
Files predicted to change: 4 new (`app/orchestrator/tools/hubspot_tools.py`,
`app/orchestrator/stages/data_enrichment.py`, `app/tests/test_stage_data_enrichment.py`, one new test
function added to `app/tests/test_orchestrator_tool_scope.py` counted as modify not new — see below) +
5 modified (`app/orchestrator/state.py`, `app/orchestrator/tools/__init__.py`,
`app/orchestrator/graph.py`, `app/tests/test_orchestrator_state.py`,
`app/tests/test_orchestrator_tools.py`, `app/tests/test_orchestrator_graph.py`,
`app/tests/test_orchestrator_tool_scope.py`).
Systems predicted to touch: `EnrichmentSlice` (extended), a new `app/orchestrator/tools/hubspot_tools.py`
binding (first HubSpot code in the project), `ToolRegistry` production population (second real tool),
`default_stages()`. No database/migration changes, no `Stage` contract changes.

--- filled in later, by Step 7, once implementation is verified ---
Actual Footprint
Files actually changed: [pending Step 7]
Deviations from plan: [pending Step 7]
Rework required: [pending Step 7]
