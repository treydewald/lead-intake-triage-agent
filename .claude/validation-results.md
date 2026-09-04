# Validation Results Log — Lead Intake Triage Agent

Full process: `docs/plan-execute-review.md` §Post-Change Validation Loop /
`docs/token-discipline.md` §3 (cached-result reuse). One entry per validation run.

---

## 2026-09-04 — Feature 01 (Pipeline Orchestration Layer)

**Checks run:** `pytest app/tests/` (full backend suite, 16 tests) + `alembic upgrade head` on a
fresh SQLite DB + `alembic check` (schema-drift check)

**Result:** FAIL (first pass) — 6 of 16 tests failed:
- `test_orchestrator_graph.py` (5 tests): `ValueError: 'intake' is already being used as a state
  key` — graph node names ("intake", "crm_write") collided with `LeadPipelineState`'s own field
  names; langgraph forbids a node sharing a state-schema key.
- `test_health.py::test_health_check`: `TypeError: 'module' object is not callable` — in the new
  `conftest.py` fixture, `import app.models` (added for the DB fixture) ran *after*
  `from main import app`, rebinding the local name `app` to the `app` package and clobbering the
  FastAPI instance the `client` fixture depends on.

**Fix applied:**
- Renamed all six graph node names to `<slice>_stage` (e.g. `intake_stage`, `crm_write_stage`),
  distinct from the state's field names, updating the corresponding `path_map` targets.
- Reordered `conftest.py`'s imports so `import app.models` runs before `from main import app`.
- Also added `model_config = {"protected_namespaces": ()}` to `ClassificationSlice` to silence a
  pydantic warning on its `model_used` field (no behavior change).

**Re-verify result:** PASS — `pytest app/tests/` 16 passed, 0 failed, 2 warnings (both pre-existing
library deprecation notices, unrelated to this change). `alembic upgrade head` created
`pipeline_run`/`stage_trace` cleanly on a fresh SQLite DB; `alembic check` reported "No new
upgrade operations detected" (migration matches the models exactly).

**Acceptance criteria coverage (architecture-plan-feature-01.md):**
1. Out-of-scope tool call rejected → `test_orchestrator_tool_scope.py::test_classification_stage_proxy_rejects_hubspot_write_call`
2. High-confidence lead skips Human Review → `test_orchestrator_graph.py::test_high_confidence_lead_skips_human_review`
3. Low-confidence lead routes to Human Review, not CRM Write → `test_orchestrator_graph.py::test_low_confidence_lead_routes_to_human_review_instead_of_crm_write`
4. Stage exception halts only that lead's run → `test_orchestrator_graph.py::test_stage_exception_halts_only_that_leads_run`
5. Every stage transition produces a queryable `StageTrace` row → `test_orchestrator_graph.py::test_every_stage_transition_produces_a_queryable_stage_trace` + `test_failed_stage_transition_is_traced_with_error`
6. `alembic upgrade head` creates tables cleanly on a fresh SQLite DB → verified manually above

---

## 2026-09-04 — Feature 02 (Intake Parsing & Normalization Stage)

**Checks run:** `pytest app/tests/` (full backend suite, 29 tests) + grep check that
`app/orchestrator/stages/intake.py` never imports a tool binding directly (per
`architecture-plan-feature-02.md`'s Validation Requirements — only a `TYPE_CHECKING`-guarded
`ScopedToolProxy` type annotation import is present, no `ToolRegistry`/tool-call usage).

No ruff/mypy installed in this project's `.venv` (not part of Step 4's bootstrap) — pytest is the
available validation signal this run; lint/typecheck were skipped rather than silently assumed
clean.

**Result:** PASS — `pytest app/tests/` 29 passed (20 pre-existing + 9 new), 0 failed, 2 warnings
(same pre-existing library deprecation notices as Feature 01's run, unrelated to this change). No
fix cycle needed; all tests passed on first run.

**Acceptance criteria coverage (architecture-plan-feature-02.md / roadmap Feature 02):**
1. Web-form payload with all fields → fully-populated `IntakeSlice` → `test_stage_intake.py::test_web_form_payload_with_all_fields_is_fully_populated`
2. Raw email text → extracted sender fields + full body retained → `test_stage_intake.py::test_raw_email_text_extracts_sender_fields_and_retains_body`
3. Callback transcript, no extractable fields → transcript retained as `message_body` → `test_stage_intake.py::test_callback_transcript_with_no_extractable_fields_retains_transcript`
4. Every record tagged with correct `source_channel` → `test_stage_intake.py::test_every_record_is_tagged_with_correct_source_channel`
5. Empty message body doesn't raise, `empty_message=True` → `test_stage_intake.py::test_empty_message_body_does_not_raise_and_is_flagged`
6. Malformed email fallback (all structured fields null, full raw text as body) → `test_stage_intake.py::test_malformed_email_falls_back_to_raw_text_with_null_structured_fields` (the specific edge case the plan's Validation Requirements flagged as most likely to be silently skipped)
7. All-fields-missing → `low_identifiability=True` → `test_stage_intake.py::test_all_identifying_fields_missing_is_flagged_low_identifiability` (the plan's other flagged edge case)
8. `IntakeStage` has no successful path to any tool call → `test_stage_intake.py::test_intake_stage_has_no_successful_path_to_any_tool_call`
9. `default_stages()["intake"]` is a real `IntakeStage`, existing graph tests still pass → all pre-existing `test_orchestrator_graph.py` tests pass unchanged + new `test_default_stages_web_form_payload_reaches_classify_with_normalized_intake`
10. Three router endpoints reachable and return a `PipelineRunOut` → `test_router_leads.py` (all three channels)

---

## 2026-09-04 — Feature 03 (Intent Classification Stage)

**Checks run:** `pytest app/tests/` (full backend suite, 44 tests) + grep check that
`app/orchestrator/stages/intent_classification.py` never imports `ollama` directly (per
`architecture-plan-feature-03.md`'s Validation Requirements — `grep -n "import ollama\|from ollama"`
returned no match, confirming the stage reaches the model only through
`tools.call("ollama_classify", ...)`) + a real end-to-end smoke call through
`ollama_tools.classify_intent` against the local `llama3.2:3b` daemon (reachable in this
environment per `.claude/pipeline-reference.md`'s Step 4 deviation note).

**Result:** PASS — `pytest app/tests/` 44 passed (29 pre-existing + 15 new: 8 in
`test_stage_intent_classification.py`, 3 in `test_orchestrator_tools.py`, 2 in
`test_orchestrator_contracts.py`, 2 new + 1 modified in `test_orchestrator_graph.py`), 0 failed. No
fix cycle needed on the final run; two new graph-level tests initially failed (`review.queued` was
`False`) because the still-stubbed `human_review` stage (Feature 06 not yet built) raised
`NotImplementedError` when invoked unfaked — fixed by also faking the `review` stage in those two
tests, same pattern already used for `enrichment`, then re-verified clean.

**Live-model smoke test (informative, not gating):** `classify_intent(client, "llama3.2:3b", "Hi, I
am ready to buy 3 units right now, please send me a quote and invoice today.")` against the real
local daemon returned `{'intent_label': 'buyer', 'confidence_score': 0.9}` — validates against the
fixed `{buyer, browser, spam}` label set. Useful signal for Feature 09's future benchmark; not a
substitute for the fake-tool unit/graph tests, which remain the gating suite.

**Acceptance criteria coverage (architecture-plan-feature-03.md / roadmap Feature 03):**
1. Clear buyer-intent message → `buyer` label, high confidence → `test_stage_intent_classification.py::test_clear_buyer_message_produces_buyer_label_with_high_confidence`
2. Empty/near-empty message body → low-confidence result, no tool call → `test_stage_intent_classification.py::test_empty_message_short_circuits_without_calling_tool`
3. LLM call failure (both attempts) → `classification_failed` sentinel, no raise → `test_stage_intent_classification.py::test_tool_call_raising_on_both_attempts_produces_classification_failed_sentinel` + `test_run_never_raises_out_of_run_for_expected_failure_modes`
4. Out-of-set label response (both attempts) → same sentinel → `test_stage_intent_classification.py::test_invalid_label_on_both_attempts_produces_classification_failed_sentinel`
5. Fails once then succeeds on retry → successful result → `test_stage_intent_classification.py::test_tool_call_fails_once_then_succeeds_on_retry_returns_successful_result`
6. `allowed_tools` boundary (`ollama_classify` only) → `test_stage_intent_classification.py::test_allowed_tools_contains_only_ollama_classify`
7. Determinism (same fake-tool response → identical result) → `test_stage_intent_classification.py::test_repeated_calls_with_same_response_produce_identical_result`
8. `default_stages()["classification"]` is real, `build_production_graph()` registers a real tool → `test_default_stages_web_form_payload_reaches_classify_with_normalized_intake` (fakes only the tool, exercises the real stage's success path) + `test_orchestrator_tools.py::test_register_default_tools_registers_ollama_classify`
9. Low-confidence/failed result reaches Human Review via unmodified `_route_after_enrich`, no new graph edges → `test_low_confidence_classification_from_real_stage_reaches_human_review` + `test_classification_failed_sentinel_from_real_stage_reaches_human_review`
10. Tool-scoping discipline (no direct `ollama` import in the stage module) → grep check above

---

## 2026-09-04 — Feature 04 (Data Enrichment Stage)

**Checks run:** `pytest app/tests/` (full backend suite, 59 tests) + grep check that
`app/orchestrator/stages/data_enrichment.py` never imports `httpx` directly (per
`architecture-plan-feature-04.md`'s Validation Requirements — confirmed no match, the stage reaches
HubSpot only through `tools.call("hubspot_search_contact", ...)`). `HUBSPOT_ACCESS_TOKEN` is empty in
this environment's `.env` (standing deviation, `.claude/pipeline-reference.md`), so the plan's
optional live-sandbox smoke call was skipped — informative-only, not required to pass this gate.

No ruff/mypy installed in this project's `.venv` (same as Feature 02's note) — pytest is the
available validation signal this run.

**Result:** PASS — `pytest app/tests/` 59 passed (44 pre-existing + 15 new: 8 in
`test_stage_data_enrichment.py`, 5 in `test_orchestrator_tools.py`, 1 in
`test_orchestrator_tool_scope.py`, 1 in `test_orchestrator_state.py`, plus 1 modified in
`test_orchestrator_graph.py`), 0 failed. No fix cycle needed; all tests passed on first run.

**Acceptance criteria coverage (architecture-plan-feature-04.md / roadmap Feature 04):**
1. Missing `email`, resolvable via phone-keyed lookup → merged + tagged with source → `test_stage_data_enrichment.py::test_missing_email_resolved_via_phone_exact_match`
2. All fields already present → unchanged no-op, no tool call made → `test_stage_data_enrichment.py::test_all_fields_present_is_a_no_op_pass_through` (trace-entry-still-logged edge case verified at the graph level, per plan, via the existing unconditional `_write_trace` call)
3. External lookup tool raises (simulated timeout) → `lookup_error` set, does not raise out of `run()` → `test_stage_data_enrichment.py::test_lookup_failure_is_encoded_as_lookup_error_not_raised`
4. `DataEnrichmentStage.allowed_tools` boundary (`hubspot_search_contact` only, `hubspot_write` rejected) → `test_orchestrator_tool_scope.py::test_data_enrichment_stage_proxy_rejects_hubspot_write_call`
5. Conflicting already-populated field is recorded, never overwritten → `test_stage_data_enrichment.py::test_conflicting_field_is_recorded_not_merged`
6. Fuzzy name match below threshold → no merge → `test_stage_data_enrichment.py::test_name_only_query_below_threshold_produces_no_merge`
7. Fuzzy name match at/above threshold → merges as phone/email path does → `test_stage_data_enrichment.py::test_name_only_query_at_or_above_threshold_merges_fields`
8. `default_stages()["enrichment"]` is a real `DataEnrichmentStage`, `build_production_graph()` registers a real `"hubspot_search_contact"` tool → `test_orchestrator_graph.py::test_default_stages_web_form_payload_reaches_enrichment_with_normalized_intake` + `test_orchestrator_tools.py::test_register_default_tools_registers_hubspot_search_contact`
9. Tool-scoping discipline (no direct `httpx` import in the stage module) → grep check above
