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
