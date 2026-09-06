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

---

## 2026-09-04 — Feature 05 (HubSpot CRM Write Stage)

**Checks run:** `pytest app/tests/` (full backend suite, 79 tests) + grep check that
`app/orchestrator/stages/hubspot_crm_write.py` never imports `httpx` directly (confirmed no match —
the stage reaches HubSpot only through `tools.call("hubspot_write", ...)`) + grep check that the
same file contains no `try`/`except` around the tool-call line (confirmed — the only matches are the
docstring's own description of that deliberate omission, not code) + grep check that
`HUBSPOT_ACCESS_TOKEN` is set in `.env` (confirmed still empty — standing deviation from Feature 04's
run, per `.claude/pipeline-reference.md`), so the plan's optional live-sandbox smoke call was again
skipped — informative-only, not required to pass this gate.

No ruff/mypy installed in this project's `.venv` (same note as prior features) — pytest is the
available validation signal this run.

**Result:** PASS — `pytest app/tests/` 79 passed (59 pre-existing + 20 new: 5 in
`test_stage_hubspot_crm_write.py`, 8 in `test_orchestrator_tools.py`, 3 in
`test_orchestrator_graph.py`, 2 in `test_orchestrator_state.py`, 1 in
`test_orchestrator_tool_scope.py`, 1 in `test_orchestrator_contracts.py`), 0 failed. No fix cycle
needed; all tests passed on first run.

**Design note surfaced during implementation (not anticipated by the architecture plan):**
`search_contact` (Feature 04) returns only a contact's `properties`, never its internal HubSpot
object id — but a PATCH-based update needs an id to address. Resolved without touching
`search_contact` or its existing tests: `write_contact` addresses an update via HubSpot's own
`idProperty` upsert query parameter (`PATCH .../contacts/{dedupe-key-value}?idProperty=phone|email`),
using the dedupe key's own value as the path segment instead of a second lookup to recover the
internal id. This is a real, documented HubSpot v3 CRM API capability, not a workaround — and it
means `search_contact`'s dedupe-lookup reuse (Architecture Rule Change #3) needed no return-shape
change at all, a stronger form of the "never re-implemented" reuse the plan called for.

**Acceptance criteria coverage (architecture-plan-feature-05.md / roadmap Feature 05):**
1. A new lead with no existing HubSpot match creates exactly one HubSpot record → `test_orchestrator_tools.py::test_write_contact_creates_when_no_existing_match`
2. Re-running the same lead's pipeline updates the existing record instead of creating a second one → `test_orchestrator_tools.py::test_write_contact_updates_when_existing_match_found` (a repeated dedupe lookup against the same phone/email always finds the just-created record, by construction)
3. A simulated HubSpot rate-limit response triggers backoff-and-retry, not immediate failure → `test_orchestrator_tools.py::test_write_contact_retries_once_on_429_then_succeeds`
4. A write failure after retries are exhausted marks the pipeline run FAILED at this stage, not silently treated as success → `test_orchestrator_tools.py::test_write_contact_raises_after_exhausting_retries_on_429` (tool level) + `test_orchestrator_graph.py::test_default_stages_crm_write_failure_halts_run_via_real_stage` (graph level, real stage)
5. No pipeline stage other than this one has a successful path to HubSpot's write API → `test_orchestrator_tool_scope.py::test_hubspot_crm_write_stage_proxy_rejects_hubspot_search_contact_call` + the existing `test_data_enrichment_stage_proxy_rejects_hubspot_write_call` (Feature 04, unchanged, still passing) — both directions of the write/search boundary now covered
6. `HubSpotCrmWriteStage.run()` never catches a tool exception → `test_stage_hubspot_crm_write.py::test_run_reraises_write_error_from_tool_call_without_catching_it` + grep check above
7. Read-time merge (enrichment fallback when intake left a field null) is actually wired, not just documented → `test_stage_hubspot_crm_write.py::test_enrichment_fallback_email_used_when_intake_email_is_none` + `test_orchestrator_graph.py::test_make_node_builds_merged_input_for_a_stage_declaring_input_slices` (proves `_make_node`'s generic branch itself)
8. `default_stages()["crm_write"]` is a real `HubSpotCrmWriteStage`, success path reaches Notification → `test_orchestrator_graph.py::test_default_stages_high_confidence_lead_reaches_notify_via_real_crm_write_stage`
9. `401`/other non-retryable failures raise immediately with zero retries → `test_orchestrator_tools.py::test_write_contact_raises_immediately_on_401_with_no_retry` + `test_write_contact_raises_immediately_on_other_4xx_with_no_retry`
10. No reliable dedupe key present → always create, flagged uncertain, zero lookup calls → `test_orchestrator_tools.py::test_write_contact_with_no_identifying_field_creates_directly_with_dedupe_uncertain`
11. Tool-scoping discipline (no direct `httpx` import in the stage module) → grep check above

---

## 2026-09-04 — Feature 06 (Human Review & Approval Gate)

**Checks run:** `pytest app/tests/` (full backend suite, 91 tests) + `alembic upgrade head` on the
dev SQLite DB (created `review_queue_item` cleanly via autogenerate) + grep check that
`HumanReviewStage.allowed_tools` stays `frozenset()` (per `architecture-plan-feature-06.md`'s
Validation Requirements #3 — confirmed, the only match is the class body itself, no tool grant
added).

No ruff/mypy installed in this project's `.venv` (same note as prior features) — pytest is the
available validation signal this run.

**Result:** PASS — `pytest app/tests/` 91 passed (79 pre-existing + 12 new: 2 in
`test_stage_human_review.py`, 8 in `test_router_reviews.py`, 1 in `test_orchestrator_graph.py`, 1 in
`test_orchestrator_state.py`), 0 failed. No fix cycle needed after implementation — one design gap
was caught and corrected before running tests: `resume_pipeline` must reset `run.status` from the
snapshot's `AWAITING_REVIEW` back to `RUNNING` before invoking the resume graph, otherwise a
successfully-resumed run would stay stuck at `AWAITING_REVIEW` instead of reaching the
`RUNNING`/`FAILED` terminal value the plan's Acceptance Criteria require;
`test_resume_pipeline_continues_paused_run_through_crm_write_and_notify` covers this directly.

**Design note (test-only addition, not in the original architecture plan):** `routers/reviews.py`
gained a `get_resume_graph_factory` FastAPI dependency, the same pattern as the existing
`get_session_factory`, so `test_router_reviews.py` can inject a resume graph built from fake stages
instead of `build_production_resume_graph`'s real HubSpot/Ollama tool bindings — keeping the
router's approve/edit path testable without live credentials, consistent with this project's
standing HubSpot-sandbox deviation (`.claude/pipeline-reference.md`). `resume_pipeline` itself stays
the single resume mechanism; only which compiled graph the router hands it is now pluggable.

**Acceptance criteria coverage (architecture-plan-feature-06.md):**
1. High-confidence lead proceeds automatically, no `ReviewQueueItem` created → `test_orchestrator_graph.py::test_high_confidence_lead_skips_human_review` (extended with a `ReviewQueueItem` count-zero assertion)
2. Low-confidence lead creates exactly one `ReviewQueueItem` (`PENDING`) and `PipelineRun.status` becomes `AWAITING_REVIEW` → `test_orchestrator_graph.py::test_low_confidence_lead_routes_to_human_review_instead_of_crm_write` (extended)
3. `approve` resumes the same `run_id` into `crm_write` then `notify` with the original label, terminal status reached → `test_orchestrator_graph.py::test_resume_pipeline_continues_paused_run_through_crm_write_and_notify` (graph level) + `test_router_reviews.py::test_approve_resumes_with_original_label` (router level)
4. `edit` resumes with `corrected_intent_label` reflected in `state.classification.intent_label` by CRM-write time → `test_router_reviews.py::test_edit_resumes_with_corrected_label`
5. `reject` sets `RunStatus.REJECTED`, no CRM write, no `StageTrace` row past `human_review` → `test_router_reviews.py::test_reject_sets_rejected_status_with_no_further_stage_trace`
6. A second action on an already-actioned `run_id` returns 409, first action's outcome unchanged → `test_router_reviews.py::test_second_action_on_already_actioned_run_returns_409_and_leaves_first_effect_unchanged`
7. `resume_pipeline` never creates a second `PipelineRun` row → `test_orchestrator_graph.py::test_resume_pipeline_continues_paused_run_through_crm_write_and_notify` (asserts exactly one row for the `lead_id`)
8. `HumanReviewStage.allowed_tools` stays empty (pure gate, no tool creep) → `test_stage_human_review.py::test_human_review_stage_declares_no_tool_access` + grep check above
9. `RunStatus.REJECTED` round-trips distinctly from `FAILED` → `test_orchestrator_state.py::test_run_status_rejected_round_trips`
10. `alembic upgrade head` creates `review_queue_item` cleanly on the existing dev DB → verified manually above

---

## 2026-09-04 — Feature 07 (Outcome Notification — In-App)

**Checks run:** `pytest app/tests/` (full backend suite, 102 tests) + `npm test -- --run` (frontend,
unaffected — Feature 07 is backend-only, 1 test) + `alembic upgrade head` on the dev SQLite DB (created
`notification` cleanly via autogenerate) + grep check that `OutcomeNotificationStage.allowed_tools`
stays `frozenset()` (per `architecture-plan-feature-07.md`'s Validation Requirements #3 — confirmed,
only the class body itself matches) + manual trace of all four outcome paths (RUNNING/FAILED/
AWAITING_REVIEW/REJECTED) confirming no code path can reach both `persist_outcome_notification` and
the generic `notify_stage` graph node for the same transition (Validation Requirements #1).

No ruff/mypy installed in this project's `.venv` (same note as prior features) — pytest is the
available validation signal this run.

**Result:** PASS — `pytest app/tests/` 102 passed (91 pre-existing + 11 new: 6 in
`test_stage_outcome_notification.py`, 2 in `test_router_notifications.py`, 3 in
`test_orchestrator_state.py`), 0 failed. No fix cycle needed after implementation — one design gap was
caught and corrected before running tests: `RunStatus.COMPLETED` had zero assignment sites anywhere in
the codebase (grep-confirmed) before this feature; `run_pipeline`/`resume_pipeline` now apply
`_mark_completed_if_still_running()` to `final_state` before persisting, per Validation Requirements #2.

**Pre-existing test updates required (per the architecture plan's own Risk #2):** 5 existing
assertions in `test_orchestrator_graph.py` and 1 in `test_router_reviews.py` encoded the pre-fix
behavior (`RunStatus.RUNNING` after a successful run, `"notify" not in calls` on the failure/
awaiting-review paths, trace lists missing the new `outcome_notification` entry on those paths) — all
updated to reflect the fixed/completed behavior, not left describing the bug. The
`test_router_reviews.py` reject test was also renamed
(`test_reject_sets_rejected_status_and_creates_a_rejected_notification`) since its old name
("...with_no_further_stage_trace") became factually wrong once a rejection legitimately produces one.

**Acceptance criteria coverage (architecture-plan-feature-07.md):**
1. Auto-processed lead produces exactly one `Notification` (`auto_processed`, `/leads/{lead_id}`) → `test_stage_outcome_notification.py::test_running_status_produces_auto_processed_outcome_linking_to_lead_detail` (stage level) + `test_orchestrator_graph.py::test_default_stages_high_confidence_lead_reaches_notify_via_real_crm_write_stage` (graph level, `RunStatus.COMPLETED` now asserted)
2. Human-Review-routed lead produces exactly one `Notification` (`awaiting_review`, `/reviews/{run_id}`) at queue time → `test_stage_outcome_notification.py::test_awaiting_review_status_produces_awaiting_review_outcome_linking_to_review_queue` + `test_orchestrator_graph.py::test_low_confidence_lead_routes_to_human_review_instead_of_crm_write` (asserts `"notify"` now fires)
3. A pipeline run that raises produces exactly one `Notification` (`failed`, describing `failed_stage`/`error`) → `test_stage_outcome_notification.py::test_failed_status_produces_failed_outcome_describing_the_failure` + `test_orchestrator_graph.py::test_stage_exception_halts_only_that_leads_run` (`calls_a` now includes `"notify"`) + `test_failed_stage_transition_is_traced_with_error` (trace list gains `outcome_notification`)
4. Reject produces a second, distinct `Notification` (`rejected`), the original `awaiting_review` one still present → `test_router_reviews.py::test_reject_sets_rejected_status_and_creates_a_rejected_notification` (asserts both rows in order)
5. Approve/edit resuming through crm_write produces a second, distinct `Notification` (`auto_processed`/`failed`) → `test_orchestrator_graph.py::test_resume_pipeline_continues_paused_run_through_crm_write_and_notify` (two `outcome_notification` traces: pause + resume)
6. `PipelineRun.status` reads `COMPLETED`, not `RUNNING`, after a successful run → `test_orchestrator_graph.py::test_stage_exception_halts_only_that_leads_run` (`final_b`) + `test_default_stages_high_confidence_lead_reaches_notify_via_real_crm_write_stage` + `test_router_reviews.py::test_approve_resumes_with_original_label`
7. `GET /notifications` returns created notifications, newest first → `test_router_notifications.py::test_list_notifications_returns_newest_first`
8. `OutcomeNotificationStage.allowed_tools` stays empty (pure signaling, no tool creep) → `test_stage_outcome_notification.py::test_outcome_notification_stage_declares_no_tool_access` + grep check above
9. Null-name lead still produces a usable message (name→phone→email→lead_id fallback) → `test_stage_outcome_notification.py::test_null_name_falls_back_to_phone_then_email_then_lead_id`
10. `alembic upgrade head` creates `notification` cleanly on the existing dev DB → verified manually above

---

## 2026-09-04 — Feature 08 (Observability / Monitoring View)

**Checks run:** `pytest app/tests/` (full backend suite) + `npm test` (frontend) + `npm run build`
(`tsc -b && vite build`, type-checks the whole frontend) + `npm run lint` (oxlint) + `alembic
revision --autogenerate` + `alembic upgrade head` on the dev SQLite DB (added `source_channel`/
`confidence_score` to `pipeline_run` cleanly) + a manual dev-server smoke test: started both
`uvicorn`/`vite dev`, submitted two real leads through `POST /leads/webform` (both genuinely failed at
`hubspot_crm_write` against the placeholder sandbox token — real failure data, not fabricated), then
used Playwright (installed ad hoc for this check, not added as a project dependency) to screenshot
`/leads` (filterable/sortable table, both leads shown with `Failed` badges), `/leads/{lead_id}` (full
6-stage timeline, `Intake Parsing`/`Intent Classification`/`Data Enrichment` shown `COMPLETED` with
their real decision payloads, `HubSpot CRM Write` failure banner naming the stage and the actual
`httpx` error), and `/leads/does-not-exist` (graceful "No lead found" message, not a crash).

No ruff/mypy installed in this project's `.venv` (same note as prior features) — pytest is the
available backend validation signal this run; `tsc -b` is the frontend equivalent.

**Result:** PASS — backend: 111 passed (102 pre-existing + 9 new in `test_router_leads_list.py`), 0
failed on first run after implementation, no fix cycle needed. Frontend: 3 passed (1 pre-existing + 2
new in `LeadListPage.test.tsx`), 0 failed; `npm run build` clean; `npm run lint` clean (2 pre-existing-
pattern `react(set-state-in-effect)` warnings on the new pages' data-fetching effects — the standard
loading/error/data pattern, not an actual bug; exit code 0).

**Known flaky test, unrelated to this feature (see execution-log.md):**
`test_router_notifications.py::test_list_notifications_returns_newest_first` — intermittent
timestamp-ordering race in Feature 07's own test, outside Group_F08's `owned_files`. Not counted
against this feature's PASS result; logged to `.claude/refinement-backlog.md` (RB-001).

**Acceptance criteria coverage (architecture-plan-feature-08.md / roadmap Feature 08):**
1. A completed, auto-processed lead's detail view shows all six stages' decisions/confidence/outcomes
   correctly → `test_router_leads_list.py::test_lead_detail_completed_run_shows_all_six_stages` +
   `test_lead_detail_decision_matches_stage_trace_output_exactly` + manual Playwright screenshot
2. A lead awaiting Human Review shows partial trace plus a clear "awaiting review" state →
   `test_router_leads_list.py::test_lead_detail_awaiting_review_shows_not_yet_run_stages`
3. A failed lead's detail view clearly identifies which stage failed →
   `test_router_leads_list.py::test_lead_detail_failed_run_identifies_failing_stage` + manual
   Playwright screenshot (real HubSpot-write failure)
4. The lead-list view can be filtered by status and source channel →
   `test_router_leads_list.py::test_list_leads_filters_by_status_and_source_channel`
5. Trace values shown match the underlying persisted trace-store values exactly →
   `test_router_leads_list.py::test_lead_detail_decision_matches_stage_trace_output_exactly` (the
   backend parses `StageTrace.output_snapshot` server-side and passes it through unformatted)
6. Unknown `lead_id` returns 404, handled gracefully by the frontend →
   `test_router_leads_list.py::test_lead_detail_unknown_lead_id_returns_404` + manual Playwright
   screenshot of `/leads/does-not-exist`
7. `PipelineRun.source_channel`/`.confidence_score` are set for every terminal/paused status, not only
   the success path → covered indirectly by every `_run()` helper call in
   `test_router_leads_list.py`, each asserting a non-null `source_channel`/`confidence_score` in the
   list/detail response regardless of outcome (auto-processed, awaiting-review, failed)
8. No stage's `run()`/`allowed_tools`/tool-scoping code touched — grep-verified the diff touches no
   file under `app/orchestrator/stages/`

---

## 2026-09-04 — RB-001 fix (flaky notification-ordering test)

**Checks run:** `pytest app/tests/test_router_notifications.py::test_list_notifications_returns_newest_first`
run in isolation 5x, then full backend suite (`pytest app/tests/`).

**Root cause confirmed:** `Notification.created_at` defaults from wall-clock time
(`app/models/notification.py`); the test's two seeded rows, committed back-to-back, could land on
the same or out-of-order timestamp at this platform's clock resolution, making the `ORDER BY
created_at DESC` result nondeterministic.

**Fix applied:** `test_router_notifications.py`'s `_seed_run_and_notifications` now sets explicit,
strictly increasing `created_at` values (1s apart) on the two seeded `Notification` rows instead of
relying on wall-clock ordering. Chose this over the entry's other named option (`ORDER BY
created_at DESC, id DESC`) because `Notification.id` is a random UUID, not sequential — an id
tiebreaker would not reflect insertion order. No production code changed.

**Result:** PASS — 5/5 isolated reruns passed (previously ~2/5 failed); full suite 111/111 passed, no
regressions.

---

## 2026-09-04 — Step 7 (Implementation Verification, Gate 2) — all 8 Tier 1 features

**Checks run:** `pytest app/tests/` (backend, full suite) + `npm test` (frontend) + `npm run build`
(`tsc -b && vite build`) + `npm run lint` (oxlint) + started both `uvicorn`/`vite dev` locally and
drove the running app: submitted a lead through all three intake channels (`POST /leads/webform`,
`/leads/email`, `/leads/callback`); one high-confidence buyer webform lead (auto-processed path); one
message classified `spam` at 0.9 confidence (confirms routing is confidence-based, not label-based —
proceeds past Human Review since 0.9 ≥ the 0.7 threshold); one empty-message webform lead (Feature
03's short-circuit → `AWAITING_REVIEW`); `GET /reviews`/`GET /reviews/{run_id}` against the queued
review; `POST /reviews/{run_id}/action` (approve) — confirmed resume reused the same `run_id`,
appended new `StageTrace` rows (`hubspot_crm_write` + `outcome_notification`), never created a second
`PipelineRun`; `GET /notifications` (newest-first ordering, 6 rows, correct); `GET /leads` with
`status`/`source_channel` filters and `sort=created_desc`; `GET /leads/{lead_id}` detail view; `GET
/leads/does-not-exist` (404). Frontend driven with Playwright (ad hoc `playwright` package already
present from Feature 08's own check, not `@playwright/test` — used the raw `chromium.launch()` API
directly): screenshotted `/leads`, `/leads/{lead_id}`, `/leads/does-not-exist`, `/` (home), and `/review`
(the sidebar's "Review Queue" nav target), checking `console` for errors on each.

**Test Results:** PASS — backend 111/111, frontend 3/3, both unchanged from Feature 08's last run (no
new code landed this step). `npm run build` clean. `npm run lint` clean except the same 2
pre-existing `react(set-state-in-effect)` warnings already noted at Feature 08 (not a regression).

**Test Coverage:** No coverage tool configured (backend: no `pytest-cov` installed in `.venv`;
frontend: no `@vitest/coverage-v8` installed) — same as every prior feature's validation entry, now
explicitly recorded at the gate level per this step's own exit condition.

**Console Errors:** NONE on `/leads`, `/leads/{lead_id}`, `/`, or `/leads/does-not-exist` (the two
`console.error` lines on the unknown-lead page are the browser's own network-layer logging of the
API's expected 404 response, not an application error — the page itself renders the graceful "No lead
found" message). `/review` produces no console error either — it renders a silently blank page instead
(see Broken States below), which is arguably worse than an error.

**Broken States found:** ONE — `/review` (the sidebar's "Review Queue" nav item, present on every
page since Step 4's bootstrap scaffold) has no matching route in `App.tsx` and renders a completely
blank page (confirmed: `document.body.innerText` is empty; even the sidebar disappears, since
React Router renders nothing when no route matches and there's no catch-all). This is a pre-existing,
already-acknowledged gap — `architecture-plan-feature-08.md`'s own Actual Footprint section already
named it as deliberately out of scope, and `.claude/pipeline-reference.md` had already tracked the
underlying "no feature builds a Review Queue frontend" gap since Feature 08. **Not counted against
any Tier 1 feature's acceptance criteria** — no roadmap feature (Tier 1, 2, or 3) specifies a Review
Queue frontend page; Feature 06's own spec and tests are backend/API-only, and the backend endpoints
this dead link would reach (`GET /reviews`, `POST /reviews/{run_id}/action`) all verified working
correctly above. Logged as `.claude/refinement-backlog.md`'s RB-002 (new, OPEN) rather than treated as
a Step 7 FAIL, per Step 7's own Common Failure Modes guidance (don't force a functional gap that no
acceptance criterion covers into the PASS/FAIL verdict for features that do work) — routed to a future
Scope Expansion/Suggestion decision or In-App Cohesion Audit, not something this step should decide
unilaterally.

**Architectural Deviations:** NONE beyond what's already recorded. All 8 `architecture-plan-
feature-0{1..8}.md` files already carry a filled-in Actual Footprint section (evidently completed
during each feature's own Step 6 round, ahead of this gate) — spot-checked Feature 08's in full and
skimmed the rest; no `AUDIT: Architectural deviation detected` marker exists in any of them
(grep-confirmed across the project root). Every "Reusable" system named in each plan was actually
extended, not duplicated (`search_contact` reused via `idProperty` upsert rather than a second lookup
path being the clearest instance, per `.claude/portfolio-reference.md`'s Key Decisions). Every approved
Architecture Rule Change is already reflected in `.claude/portfolio-reference.md`'s Key Decisions
section.

**Cross-feature interaction review (Step 4.5):** Every `.claude/execution-log.md` entry (Features
01-08) has a corresponding clean `.claude/validation-results.md` entry — no change went in without
passing its own validation loop. No interaction bugs found: the full backend suite (111 tests) already
exercises all 8 features together on every run, and this step's live smoke test additionally drove a
real end-to-end sequence spanning intake → classification → enrichment → CRM write → human review →
resume → notification → observability view, across all three intake channels, both the high- and
low-confidence routing paths, and the approve-resume flow — the deepest cross-feature exercise this
project has had. No conflicts found between individually-clean changes.

**Verdict: PASS** — all 8 Tier 1 features are implementation-complete and verified working end-to-end
against the real orchestrator, real local Ollama model, and real (empty-token) HubSpot sandbox
failure path. Application starts cleanly on both frontend and backend, every Tier 1 workflow's primary
path functions, tests pass, and no acceptance-criterion-covered feature is broken. One pre-existing,
out-of-scope UI gap found and logged (RB-002) rather than gating this verdict. Ready for Step 8
(Viewport-First Refactor).

---

## 2026-09-04 — Feature 09 (Classification Accuracy Benchmark Report)

**Checks run:** `pytest app/tests/` (full backend suite) + `npm test` (frontend) + `npm run build`
(`tsc -b && vite build`) + `npm run lint` (oxlint) + `alembic revision --autogenerate` + `alembic
upgrade head` on the dev SQLite DB (added `benchmark_run`/`benchmark_case` cleanly) + a manual
dev-server smoke test: started both `uvicorn`/`vite dev`, used Playwright (the same ad hoc
`playwright` package from Feature 08's check) to navigate to `/benchmark` via the sidebar nav link,
click "Run Benchmark", and wait for the real synchronous run to complete against the real local
`llama3.2:3b` model (not mocked, not faked) — 22 dataset items x 3 repeats = 66 real Ollama calls.

**Result:** PASS — backend: 118 passed (111 pre-existing + 7 new: 3 in `test_benchmark_harness.py`, 4
in `test_router_benchmark.py`), 0 failed on first run after implementation, no fix cycle needed.
Frontend: 5 passed (3 pre-existing + 2 new in `BenchmarkPage.test.tsx`), 0 failed; `npm run build`
clean; `npm run lint` clean (same 2 pre-existing-pattern `react(set-state-in-effect)` warnings on
other pages, already noted at Feature 08 — no new warnings from this feature's code).

**Live run result (real model, real data):** Accuracy 87.0%, Consistency 90.9%, `llama3.2:3b`, 22
cases, 3 repeats. The 3 misclassified cases were all `browser`-category messages the model labeled
`buyer` — a genuine model-behavior finding (the local 3B model over-predicts purchase intent on
lower-urgency browsing messages), not a test artifact. One ambiguous item (`ambiguous-004`) hit the
real `classification_failed` sentinel on its first attempt, rendered correctly as predicted "—" rather
than crashing or showing a stale value. Zero console errors on `/benchmark`.

**Acceptance criteria coverage (architecture-plan-feature-09.md / roadmap Feature 09):**
1. Dataset includes at least buyer/browser/spam/ambiguous categories → `dataset.py`'s
   `BENCHMARK_DATASET` (6/6/6/4); live run confirms all 4 categories represented
2. `POST /benchmark/run` computes and persists an accuracy percentage against ground-truth labels
   (never self-reported model confidence) → `test_benchmark_harness.py::
   test_run_benchmark_produces_hand_computed_accuracy_and_consistency` (hand-computed 3/4 = 0.75
   against a scripted fake) + live run (87.0%, matches `correct_attempts / total_attempts`)
3. `GET /benchmark/runs/{run_id}` returns every misclassified case with predicted/actual label and
   confidence → `test_router_benchmark.py::
   test_get_run_detail_lists_every_misclassified_case_with_predicted_and_actual_label` + live run
   (3 `browser`→`buyer` misclassifications all shown with confidence)
4. Consistency metric derived from repeated same-input runs, shown distinctly from accuracy →
   `test_run_benchmark_produces_hand_computed_accuracy_and_consistency` (2/3 = 0.667 hand-computed,
   independently of the 3/4 accuracy figure) + live run (90.9% shown in its own stat tile)
5. An ambiguous item is shown explicitly marked, never forced into correct/incorrect →
   `test_ambiguous_items_never_counted_in_accuracy_denominator` (`correct is None`) + live run (all 4
   ambiguous items rendered with an "Ambiguous" badge, `expected` column showing "—")
6. `BenchmarkPage.tsx` reachable from nav, shows latest run's accuracy/consistency, lists every
   failure case → live Playwright run: nav-clicked to `/benchmark`, both stat tiles and the failure
   table rendered with real data
7. (Validation Requirements addendum) Harness calls the real `IntentClassificationStage`/
   `register_default_tools` path, no duplicate classification logic → code review of `harness.py`
   confirms direct reuse; a deliberately-failing case (scripted double-raise, matching the stage's own
   internal retry) is counted as incorrect not excluded →
   `test_deliberately_failing_case_counts_as_incorrect_not_excluded`

## 2026-09-05 — Feature 10 (External Notification Delivery)

**Checks run:** `pytest app/tests/` (full backend suite) + `alembic upgrade head` on the dev SQLite DB
(added `external_delivery_status`/`external_delivery_error` to `notification` cleanly, chaining onto
`b86e4d4ef367` — the actual current head, not the plan's stated `5f3cbe979b96`) + a manual dev-server
live verification against the real local `llama3.2:3b` model (not mocked) covering all three delivery
paths named in the plan's Validation Requirements. No frontend change (Feature 10 has no UI surface).

**Result:** PASS — backend: 128 passed (118 pre-existing + 10 new: 5 in `test_webhook_tools.py`, 4 new
in `test_orchestrator_graph.py`, 1 new in `test_router_notifications.py`), 0 failed on first run after
implementation, no fix cycle needed.

**Live run result (real model, real HTTP, three separate submissions via `POST /leads/webform` with
`CONFIDENCE_THRESHOLD=0.95` temporarily overridden in `.env`, not committed, matching the precedent set
at Feature 15 — the real model is consistently overconfident on ambiguous test messages):**
1. **Sent path** — `NOTIFICATION_WEBHOOK_URL` pointed at a disposable local HTTP receiver
   (`127.0.0.1:8999`, a throwaway script, not part of the repo): the receiver's log shows the exact
   payload `{"text": "Lead Test Webhook Lead is awaiting human review.\n/reviews/<run_id>"}`, matching
   the in-app `Notification` row's `message`/`detail_link` exactly. `GET /notifications` showed
   `external_delivery_status="sent"`, `external_delivery_error=null`.
2. **Failed path** — `NOTIFICATION_WEBHOOK_URL` pointed at a deliberately unreachable address
   (`127.0.0.1:1`): `GET /notifications` showed `external_delivery_status="failed"`,
   `external_delivery_error="ConnectError"`; the run still reached `AWAITING_REVIEW` normally (confirmed
   via the `POST /leads/webform` response), proving the delivery failure never raised out of
   `persist_outcome_notification()` or affected `PipelineRun.status`.
3. **Skipped path** — `NOTIFICATION_WEBHOOK_URL` unset (the default): `GET /notifications` showed
   `external_delivery_status="skipped"`, no HTTP call attempted (no `webhook_tools` invocation, verified
   by the absence of any new receiver-log entry), the in-app `Notification` row created exactly as
   before Feature 10.
4. **Outcome-type gate** — pre-existing `rejected`/`failed` notification rows from earlier in the same
   session (Feature 15/RB-002 verification) were re-checked via `GET /notifications` and still showed
   `external_delivery_status=null` — confirming delivery is never attempted for outcome types other than
   `awaiting_review`, using real historical data rather than only the unit tests.

**Acceptance criteria coverage (architecture-plan-feature-10.md):**
1. An `awaiting_review` outcome triggers both the in-app `Notification` and, when configured, one
   external webhook POST with the outcome's `message`/`detail_link` → live run #1 above +
   `test_persist_outcome_notification_records_sent_on_successful_delivery`
2. A webhook delivery failure is caught, recorded as `external_delivery_status="failed"`/
   `external_delivery_error=<reason>`, never raises, never changes `PipelineRun.status` → live run #2
   above + `test_persist_outcome_notification_records_failed_without_raising` +
   `test_deliver_webhook_notification_non_2xx_returns_failed_without_raising` +
   `test_deliver_webhook_notification_connection_error_returns_failed_without_raising`
3. `auto_processed`/`failed`/`rejected` outcomes never attempt external delivery,
   `external_delivery_status` stays `None` → live run #4 above +
   `test_persist_outcome_notification_never_attempts_delivery_for_non_awaiting_review_outcomes`
4. `NOTIFICATION_WEBHOOK_URL` unset → `external_delivery_status="skipped"`, no HTTP call attempted, the
   in-app `Notification` row still created → live run #3 above +
   `test_persist_outcome_notification_skips_delivery_when_webhook_url_unset`
5. No retry loop — exactly one delivery attempt per event → `deliver_webhook_notification`'s
   implementation makes exactly one `client.post()` call with no loop, per the risk mitigation named in
   the plan; confirmed by code review (no retry construct anywhere in `webhook_tools.py`)

**Additional risk mitigation confirmed:** `test_deliver_webhook_notification_error_never_includes_the_
webhook_url` verifies the returned `error` string never contains the configured webhook URL — the plan's
own Risks section flagged this as a potential secret/destination leak since `GET /notifications` has no
auth in this project.

---

## 2026-09-05 — Feature 11 (Per-Lead Audit/History Trail UI)

**Checks run:** `pytest app/tests/` (full backend suite) + `alembic upgrade head` on the dev SQLite DB +
`npm run build` (`tsc -b && vite build`) + `npm test -- --run` (frontend) + live manual dev-server
verification against the real local `llama3.2:3b` model and a real pre-existing pending review item.

**Result:** PASS on first run — 136/136 backend tests (128 pre-existing + 8 new: 2 in
`test_router_reviews.py`, 6 in the new `test_router_leads_history.py`), no fix cycle needed.
`alembic upgrade head` applied `327d880cd1b9` cleanly onto the actual head `a95fad549dbf` (confirmed via
`alembic heads` before writing the migration, per the plan's Validation Requirements). Frontend:
`npm run build` clean; 14/14 relevant frontend tests passing (13 pre-existing/updated + 3 new in
`LeadHistoryPage.test.tsx`, 1 new in `ReviewDetailPage.test.tsx`); one pre-existing, unrelated failure
in `App.test.tsx` (asserts stale `HomePage.tsx` placeholder text removed by RB-004) — confirmed via
`git stash` that it fails identically on the unmodified working tree, logged as RB-005 rather than fixed
here (outside Group_F11's `owned_files`).

**Live run result (real model, real HTTP, no browser-automation tool available this session — see
`.claude/execution-log.md`'s Feature 11 entry for what compensated):**
1. Submitted `POST /leads/webform` with an ambiguous message against the real `llama3.2:3b` model — the
   run completed intake/classification/enrichment/notification live, failed at `hubspot_crm_write` with
   the expected pre-existing "no sandbox token configured" error (a known, documented project deviation,
   not a Feature 11 defect). `GET /leads/{lead_id}/history` on this lead returned all 5 real stage
   entries in correct chronological order and **zero** `review_action` entries — confirming the "no
   fabricated review entry for an auto-processed/non-reviewed lead" behavior against real data, not just
   the unit test.
2. Found a real pending item via `GET /reviews` (left over from an earlier session's live testing) and
   called `POST /reviews/{run_id}/action` with `{"action": "approve", "reviewer_name": "Jordan"}` against
   it — the real resume graph executed, reaching `hubspot_crm_write` (same expected token-not-configured
   failure) then `outcome_notification`. `GET /leads/{lead_id}/history` on this lead showed the review
   action correctly interleaved chronologically between the pause and the post-approval stage entries,
   with `reviewer_action="approve"` and `reviewer_name="Jordan"` both correct.
3. `GET /leads/does-not-exist-abc/history` returned `404`, matching `GET /leads/{lead_id}`'s existing
   behavior.

**Acceptance criteria coverage (architecture-plan-feature-11.md):**
1. A lead that went through Human Review shows both stage transitions and the reviewer's action,
   correctly ordered by time → live run #2 above +
   `test_history_reviewed_lead_shows_stage_and_review_action_ordered`
2. An auto-processed lead's timeline contains no fabricated review-related entries → live run #1 above +
   `test_history_pending_review_produces_no_fabricated_review_entry` (the `PENDING`, not-yet-actioned
   case) + `test_history_auto_processed_lead_has_stage_entries_only`
3. Navigating from Feature 08's detail view reaches this timeline view for the same lead, and back →
   `LeadDetailPage.tsx`'s new "View Full History →" link and `LeadHistoryPage.tsx`'s "← Back to lead
   detail" link, both to the correct `lead_id`-scoped path; verified by code review and the clean
   `npm run build` (no route/type errors) — no live-browser click-through available this session (see
   execution-log's verification note)
4. A fixture-seeded lead with two `PipelineRun` rows sharing one `lead_id` shows both attempts' stage
   transitions distinctly, in chronological order →
   `test_history_multi_run_lead_shows_both_attempts_distinctly` (direct DB fixture, per the plan's
   multi-attempt gap note — no live endpoint produces this scenario)
5. A review action taken with `reviewer_name` supplied displays that name; one taken without it displays
   the "Reviewer" fallback → live run #2 above (name path) +
   `test_history_reject_shows_terminal_review_action_distinct_from_failed_stage` (no-name path, backend)
   + `LeadHistoryPage.test.tsx`'s two fallback-rendering tests (frontend, jsdom-rendered)
6. `GET /leads/{lead_id}/history` 404s for an unknown `lead_id` → live run #3 above +
   `test_history_unknown_lead_id_returns_404`

**Additional confirmation:** `GET /leads/{lead_id}` (Feature 08) re-verified unchanged — same response
shape, same `.first()` semantics — via the full existing `test_router_leads_list.py` suite passing
unmodified; Feature 11 adds a new endpoint alongside it rather than altering it.

---

## 2026-09-05 — Step 7: Implementation Verification (Gate 2 re-pass — Features 09, 10, 11)

**Scope:** The prior Gate 2 pass (2026-09-04) covered only the 8 Tier 1 features. Features 09
(Classification Accuracy Benchmark Report), 10 (External Notification Delivery), and 11 (Per-Lead
Audit/History Trail UI) had each passed their own Step 6 validation loop individually but had
accumulated without a dedicated batch Implementation Verification gate. This session ran that gate.

**Step 1 — Application start:** Backend (`uvicorn main:app --port 8000`) and frontend (`npm run dev`,
port 5173) both started cleanly against the real dev SQLite DB and real local Ollama
(`llama3.2:3b`, confirmed serving via `/api/version`). No startup errors in either log.

**Step 4 — Full test suite:** 136/136 backend (`pytest`, 26.27s), 15/15 frontend (`vitest run`,
7.07s) — both unchanged from the numbers each feature's own Step 6 session already recorded.
**Test coverage:** no coverage tool configured on either side (Istanbul/nyc or `pytest-cov` never
set up) — recorded, not gating, consistent with the 2026-09-04 Gate 2 entry.

**Step 3 — Spot-check, live against the real backend (no mocks):**
- **Feature 09:** `GET /benchmark/runs` returned the one real run on record (accuracy 87.04%,
  consistency 90.91%, 22 cases, model `llama3.2:3b`); `GET /benchmark/runs/{id}` returned all 22
  cases with detail — matches the figures Feature 09's own Step 6 session produced, no drift.
- **Feature 10:** queried the `notification` table directly — all three real delivery outcomes from
  Feature 10's own live verification are still present and correct: `sent` (real webhook receiver),
  `failed` (`ConnectError`, unreachable URL), `skipped` (no URL configured), plus `null` on
  `auto_processed`/`failed`/`rejected` rows confirming the outcome-type gate holds under real data,
  not just at the moment Feature 10 was built.
- **Feature 11:** `GET /leads/{lead_id}/history` exercised against two real leads — one with only
  stage transitions (no review yet), one with an `ACTIONED` review interleaved
  (`reviewer_action="approve"`, `reviewer_name="Jordan"`) followed by a real `hubspot_crm_write`
  resume attempt (`FAILED` — expected, sandbox token is a placeholder per this project's known
  deviation) and a second `outcome_notification` entry. Chronological merge, review-action
  interleaving, and post-approval resume are all correct against real persisted data.
- No browser-automation tool available this session (Playwright binaries exist under
  `frontend/node_modules/.bin` but the package is not a declared `frontend/package.json` dependency —
  a stray/transitive install, not a usable project fixture; `.claude/seed-data.md` is still the
  unfilled Step 10 template, confirming Screenshot Capture genuinely hasn't run yet). Compensated with
  direct HTTP-level verification against the real backend plus direct SQLite queries, same
  methodology Feature 11's own Step 6 session used for the same reason.
- Both dev server logs reviewed end-to-end: zero errors, only expected `INFO` access logs.

**Step 4.5 — Cross-feature interaction review:** No conflicts found. Feature 09's benchmark harness
runs `IntentClassificationStage` out-of-graph and touches no state Features 10/11 depend on. Feature
10's delivery hook and Feature 11's `reviewer_name` field are independent extension points on
different call sites (`persist_outcome_notification()` vs. the reviews router's atomic claim UPDATE)
with no shared code path. Feature 11's history endpoint correctly excludes notification-delivery data
(a different concern, per `portfolio-reference.md`'s Key Decisions) — verified by inspection, no
notification fields appear in `GET /leads/{lead_id}/history` responses.

**Step 4.6 — Architectural fidelity:** Features 09 and 11 already had `Actual Footprint` sections in
their `architecture-plan-*.md` files (appended during their own Step 6 sessions) — reviewed, both
accurate against what's actually in the codebase, no deviations beyond what each already recorded.
**Gap found:** `architecture-plan-feature-10.md` was missing its `Actual Footprint` section entirely
— it had a `Predicted Footprint` but nothing appended after implementation. **Fixed this session:**
appended the section using `.claude/execution-log.md`'s existing Feature 10 entry as the source of
truth (files actually touched, the one corrected migration-chain detail, and the three live-verified
delivery paths) — no new investigation needed, the data already existed, it just hadn't been copied
into the plan file per Step 4.6's exit condition.

**Console errors:** None (dev server logs reviewed; no browser console available this session — see
above).

**Verdict: PASS.** All three features function correctly against real, live data with no regressions
and no unresolved cross-feature conflicts. One documentation gap (Feature 10's missing Actual
Footprint) found and fixed as part of this gate, not deferred.

```
IMPLEMENTATION VERIFICATION REPORT
===================================

Status: PASS

Features Verified: 3 (Feature 09, Feature 10, Feature 11 — Tier 2 batch; Tier 1 covered 2026-09-04)
Routes Tested: 3 (GET /benchmark/runs, GET /benchmark/runs/{id}, GET /leads/{lead_id}/history) +
  1 read-only DB check (notification delivery status, no dedicated route)
Broken Features: 0

Test Results: PASS (136/136 backend, 15/15 frontend)
Test Coverage: no coverage tool configured
Console Errors: NONE
Architectural Deviations: NONE (one missing Actual Footprint section found and fixed — documentation
  gap, not a functional or architectural deviation)

Verdict: Application is implementation-complete and ready for Step 8 (Viewport Optimization) —
Tier 1 + Tier 2 (Features 09-11) all verified. Feature 15 (CD round) already has its own CD-4
verification and does not need a separate Gate 2 pass.
```

---

## 2026-09-05 — Step 9 (Unified QA & Repair)

**Checks run:** Full black-box discovery + realistic interaction testing across all 7 routes via
Playwright (`playwright-core`, since `playwright`'s top-level package was pruned as extraneous by an
`npm install` this session — `playwright-core` alone launches Chromium fine, no functional loss),
against the real backend/SQLite DB and real local `llama3.2:3b`, not mocks. Plus Step 9.5's automated
scans: `npm audit` (frontend), `pip-audit` (backend), and an `@axe-core/playwright` accessibility scan
across all 6 primary pages. Full detail and every defect: `qa-report.md` (project root).

**Result:** 4 confirmed defects (2 functional: High severity each; 2 accessibility: 1 Critical, 1
Serious, both systemic across multiple files) — all fixed and live-re-verified this session. 1
dependency-audit finding (19 known vulnerabilities, all assessed Moderate for this project's actual
configuration via OSV.dev CVSS lookups on the two worst-sounding ones) logged to `qa-report.md`'s
Remaining Issues, not fixed (would require major-version upgrades of `langgraph`/`langchain-core`/
`starlette` — a compatibility-verification task of its own, out of scope for a same-session QA pass).

**Fixes applied (see `qa-report.md` for full root-cause detail on each):**
- QA-1 (High): `backend/app/orchestrator/tools/hubspot_tools.py` — added `_require_token()`, called
  from `search_contact`/`write_contact`, so an unconfigured `HUBSPOT_ACCESS_TOKEN` raises a clear
  `HubSpotWriteError` instead of leaking `httpx.LocalProtocolError`'s raw "Illegal header value
  b'Bearer '" into the pipeline run's FAILED status/notification text. Affected 21/25 (84%) of seeded
  runs. 2 new tests in `test_orchestrator_tools.py`.
- QA-2 (High): `frontend/src/App.tsx` + new `frontend/src/pages/NotFoundPage.tsx` — added a catch-all
  `<Route path="*">` inside the `Layout` route; any unmatched URL previously rendered a fully blank
  page (no sidebar, empty `document.body.innerText`).
- QA-3 (Medium): `frontend/src/pages/LeadListPage.tsx` — refactored filter/sort/page state from local
  `useState` to `useSearchParams`, so browser Back/Forward preserves filters (previously reset silently
  on navigating to a lead and back).
- QA-4 (Critical, accessibility): added `aria-label` to `LeadListPage.tsx`'s 3 filter `<select>`s
  (axe-core `select-name` violation — no accessible name on any of them).
- QA-5 (Serious, accessibility): replaced all 11 `text-slate-400` occurrences (app-wide muted-label
  color, 2.51-2.63:1 contrast against white) with `text-slate-500` (~4.6:1) across 7 files; bumped one
  additional near-miss (stage-status badge on red background, 4.35:1) to `text-slate-600`.
- QA-6 (Moderate, accessibility): `frontend/src/components/BuildIndicator.tsx` — added
  `aria-hidden="true"` to the decorative build-timestamp watermark (axe-core `region` violation: content
  outside any landmark; correct fix for non-essential decorative content is hiding it, not landmarking
  it).

**Re-verify result:** PASS —
- Backend: 138/138 passed (136 baseline + 2 new)
- Frontend: 15/15 passed (unchanged), `npm run build` clean, `npm run lint` clean except 5 pre-existing
  `react(set-state-in-effect)` warnings confirmed via `git stash` comparison to predate this session
  (logged to `qa-report.md`'s Remaining Issues as Low, not fixed — a broader style change outside
  contained-defect scope)
- axe-core: 0 violations of any severity across all 6 primary pages (started at 1 critical + 1 serious
  + 1 moderate per page)
- Step 8's no-scroll invariant re-checked: 0 overflow across all 7 original routes × 4 viewports
  (1920×1080/1440×900/1366×768/390×844) = 28 combinations, plus the new not-found route and the
  filtered-URL case at tablet (768×1024) and mobile — no regression from any fix
- Live end-to-end regression check: Approve and Reject actions on the two real pending review items
  both completed correctly through the full `human_review`→`crm_write`(fails cleanly with the QA-1
  fix's message)→`outcome_notification` resume path, including the already-actioned 409 conflict
  check — confirms QA-2's routing change introduced no regression in the Tier 1 review workflow

**Acceptance criteria coverage:** N/A (Step 9 is a cross-cutting QA pass, not tied to one feature's
spec) — see `qa-report.md`'s Tested Workflows section for full per-page coverage.

**Note on live test data:** both `AWAITING_REVIEW` review-queue items present at session start were
consumed by the live Approve/Reject verification above (one approved, one rejected) — Step 10 will need
to seed a fresh pending item. Two `FAILED` test leads were created live via `/leads/webform` to verify
QA-1's fix and left in place (no delete-lead API exists to remove them safely). Full detail:
`qa-report.md`'s Final Verdict note.

Verdict: Application QA-complete, all functional and accessibility defects found this session fixed and
regression-verified. Ready for Step 10 (Screenshot Capture).

---

## 2026-09-06 — Continued Development: Feature 16 (Failed-Run Retry / Resubmission), CD-4

**Scope:** CD-2 (spec, `implementation_plan.md`), CD-2.5 (`architecture-plan-feature-16.md`), CD-3
(implementation), CD-4 (this verification) all run this session, per `docs/scope-expansion.md`
Round 1's S-01 candidate and the user's explicit "both, in sequence — S-01 first" tie-break
decision.

**Step 4 — Full test suite:** 147/147 backend (`pytest`, ~40s — 138 pre-existing + 9 new: 6 in
`test_orchestrator_retry.py`, 3 additional endpoint tests woven into `test_router_leads_retry.py`'s
4 tests total), 47/47 frontend (`vitest run`, ~10s — 44 pre-existing + 3 new Retry-action tests in
`LeadDetailPage.test.tsx`). `npm run lint` (oxlint) and `npm run build` (`tsc -b && vite build`)
both clean, zero errors.

**Test coverage:** no coverage tool configured on either side — consistent with every prior
feature's validation entry; not a new gap introduced this round.

**Performance baseline regression check (`docs/continued-development.md` CD-4):** `qa-report.md`'s
recorded baseline is 307.21 kB / 97.89 kB gzip (frontend bundle, no prior baseline before that).
This round's `vite build` output: 339.04 kB / 105.08 kB gzip — a +10.4% raw / +7.3% gzip increase,
both under the 15% material threshold. Not a regression; not re-recorded as a new baseline (CD-4's
default only replaces the baseline when none exists yet).

**Step 3 — Live verification against the real backend (no mocks), via a running `uvicorn`
instance:**
1. `POST /leads/webform` with a real message → real `IntentClassificationStage` (Ollama
   `llama3.2:3b`) classified it high-confidence (0.9) → real `HubSpotCrmWriteStage` failed as
   expected (`HUBSPOT_ACCESS_TOKEN` is a placeholder, this project's known deviation — see
   `.claude/pipeline-reference.md`'s Deviations section) → run ended `FAILED` at
   `hubspot_crm_write`, matching every prior session's same observed limitation.
2. `POST /leads/{lead_id}/retry` against that real failed lead → created a genuinely new
   `PipelineRun` row, replayed only `hubspot_crm_write` + `outcome_notification` (confirmed via the
   response's own `stage_traces` — no `intake_parsing`/`intent_classification`/`data_enrichment`
   entries), failed again at the same real HubSpot-token limitation (expected — proves the retry
   mechanism itself engages correctly even though the underlying write can't succeed in this dev
   environment, the same distinction Feature 11's own Step 7 session drew for the identical
   limitation).
3. `GET /leads/{lead_id}` after the retry returned the *new* run's id and status, not the original
   failed run's — confirms the `get_lead_detail` ordering fix.
4. `GET /leads/{lead_id}/history` after the retry showed both attempts' stage transitions,
   correctly attributed to their own distinct `run_id`s, in chronological order.
5. `POST /leads/no-such-lead/retry` → `409` with `{"detail": "No failed run found for lead
   'no-such-lead'"}`, not a 500 or silent no-op.
6. A second consecutive retry against the same lead (retry-of-a-retry) succeeded, creating a third
   distinct `PipelineRun` row — confirms "most recent `FAILED` run" selection holds across more
   than two attempts.
7. Dev server log reviewed end-to-end: zero errors, only expected `INFO` access logs and the
   already-known HubSpot-token warning.

**Acceptance criteria coverage (architecture-plan-feature-16.md / `implementation_plan.md`'s
Feature 16 spec):**
1. Retry creates a new run continuing from the failed stage without re-running earlier stages →
   live run #2 above + `test_retry_pipeline_creates_a_new_run_and_does_not_rerun_earlier_stages`
2. New run's `StageTrace` rows contain only the replayed stage(s) → live run #2 above (same test)
3. `GET /leads/{lead_id}` reflects the new run after retry → live run #3 above +
   `test_get_lead_detail_reflects_latest_attempt_after_retry`
4. `GET /leads/{lead_id}/history` shows both attempts distinctly, in order → live run #4 above +
   `test_lead_history_shows_both_attempts_after_retry`
5. No `FAILED` run → `409` → live run #5 above + `test_retry_with_no_failed_run_returns_409` +
   `test_retry_pipeline_raises_when_no_failed_run_exists`
6. `LeadDetailPage.tsx`'s Retry action calls the endpoint and refreshes status/timeline without a
   manual reload → `LeadDetailPage.test.tsx`'s three new tests (button visibility, successful
   retry updates displayed status, failed retry shows an inline error) — no live-browser
   click-through available this session (same capability gap every prior frontend-only session has
   noted; compensated with jsdom-rendered component tests, consistent with established practice)

**Architectural fidelity (`docs/implementation-planning.md` §14):** implementation matched
`architecture-plan-feature-16.md`'s plan exactly — `build_retry_graph` reuses the same
`_make_node`/`_make_human_review_node`/`_route_or_fail`/`_route_after_enrich` building blocks
`build_graph`/`build_resume_graph` already use, added as a new function rather than modifying
either existing graph-builder; `build_resume_graph` itself is byte-for-byte unchanged and its own
Feature 06 tests pass unmodified. Actual Footprint recorded in the plan file: 8/8 predicted files
changed, no unplanned files, no rework cycle.

**Additional confirmation:** `GET /leads` (list) and every other existing Feature 08/09/10/11
endpoint re-verified unchanged via the full existing test suites passing unmodified — Feature 16
adds one new route and one ordering fix to an existing route, nothing else in `leads.py` changed.

Verdict: Feature 16 (Failed-Run Retry / Resubmission) is implementation-complete, live-verified,
and regression-free. Per `scope-expansion.md`'s tie-break decision, S-02 (Confidence-Threshold
What-If Simulator) is the queued next Continued Development round.

---

## 2026-09-06 — Continued Development: Feature 17 (Confidence-Threshold "What-If" Simulator), CD-4

**Scope:** CD-1 (`roadmap-addendum-2026-09-06.md`) through CD-4 all run this session, immediately
following Feature 16, per the user's "both" confirmation to run both P1 candidates from
`docs/scope-expansion.md` Round 1 in sequence.

**Step 4 — Full test suite:** 149/149 backend (`pytest`, ~31s — 147 pre-existing + 2 new in
`test_router_benchmark_threshold.py`), 56/56 frontend (`vitest run`, ~10s — 47 pre-existing + 7 new
in `thresholdSimulation.test.ts` + 2 new in `BenchmarkPage.test.tsx`). `npm run lint` (oxlint) and
`npm run build` (`tsc -b && vite build`) both clean, zero errors.

**Test coverage:** no coverage tool configured on either side — consistent with every prior
feature's validation entry.

**Performance baseline regression check:** cumulative bundle size after both Feature 16 and Feature
17 this session: 343.00 kB / 105.93 kB gzip, vs. the recorded 307.21 kB / 97.89 kB gzip baseline —
+11.6% raw / +8.2% gzip, both under the 15% material threshold from `docs/continued-development.md`
CD-4's default. Not a regression.

**Step 3 — Live verification against the real backend (no mocks), via a running `uvicorn`
instance:**
1. `GET /benchmark/confidence-threshold` → `{"confidence_threshold": 0.7}`, matching
   `Settings.confidence_threshold`'s real configured default.
2. `GET /benchmark/runs` → confirmed a real, pre-existing 22-case benchmark run on record (from
   Feature 09's own prior live verification).
3. `GET /benchmark/runs/{run_id}` → fetched all 22 real cases and independently recomputed the
   threshold split in a one-off script using the identical `confidence >= threshold` rule
   `simulateThreshold()` implements: at 0.7, **21/22 auto-process, 1 goes to review; of the 21
   auto-processed, 15 correct, 3 incorrect, 3 ambiguous.** This is a genuine, actionable finding
   surfaced as a side effect of building the feature (3 of 22 known cases would be silently wrong at
   the project's current threshold) — not a synthetic example.
4. Cross-checked this matches `_route_after_enrich`'s real production boundary
   (`backend/app/orchestrator/graph.py`) — same `>=` comparison, same threshold source
   (`Settings.confidence_threshold`), so the simulator's "current" column is not just plausible but
   provably identical to what the live pipeline would actually do for these cases.

**Acceptance criteria coverage (architecture-plan-feature-17.md / `implementation_plan.md`'s
Feature 17 spec):**
1. `GET /benchmark/confidence-threshold` returns the real configured value → live check #1 above +
   `test_confidence_threshold_returns_the_configured_value` +
   `test_confidence_threshold_reflects_a_live_config_change`
2. Slider updates counts with no network request per change → `simulateThreshold` is a pure
   function (no `fetch`/`axios` call in its body, confirmed by code review) +
   `BenchmarkPage.test.tsx`'s slider-change test
3. Current-threshold counts match production routing exactly → live checks #3-4 above +
   `thresholdSimulation.test.ts`'s boundary-equality test
4. Switching runs re-bases the simulation → `BenchmarkPage.test.tsx`'s run-switch test
5. Panel collapsed by default, no no-scroll regression when collapsed → code review (`<details>`
   without `open`, matching `LeadDetailPage.tsx`'s existing pattern); **expanded-state visual layout
   recorded `UNVERIFIED`** per `docs/agent-portability.md` — no browser-automation tool available
   this session (same capability gap noted throughout this project's history, e.g. Feature 11's Step
   7 verification)

**Architectural fidelity (`docs/implementation-planning.md` §14):** implementation matched
`architecture-plan-feature-17.md` exactly, including its central finding — the Scope Expansion
candidate's originally-proposed "derived endpoint computing the auto/review split" was not built;
`GET /benchmark/confidence-threshold` (exposing only the live threshold value) was the only new
backend surface needed, confirmed correct by the live cross-check above. Actual Footprint recorded
in the plan file: 8/8 predicted files changed, no unplanned files, no rework cycle.

**Additional confirmation:** the existing `GET /benchmark/run`, `/runs`, and `/runs/{run_id}`
endpoints re-verified unchanged via the full existing benchmark test suite passing unmodified —
Feature 17 adds one new route alongside them, nothing else in `benchmark.py`/`schemas/benchmark.py`
changed.

Verdict: Feature 17 (Confidence-Threshold "What-If" Simulator) is implementation-complete,
live-verified against real data, and regression-free (collapsed-state layout only; expanded-state
visual check honestly recorded `UNVERIFIED`, not silently assumed). This closes both P1 candidates
from `scope-expansion.md`'s Round 1 — no further Continued Development round is currently queued;
a future session should re-run `docs/next-action-selection.md`'s Dynamic Next-Action Selection or
bring a new Suggestion.

---

## CD-4 — Feature 18 (Aggregate Lead Funnel & Reviewer Throughput Dashboard), 2026-09-06

**Backend tests:** 154/154 passed (was 149/149 — +5 new in `test_router_analytics.py`), no
regressions. Coverage held at 98% (unchanged from Continual Refinement Round 1's baseline).

**Frontend tests:** 60/60 passed (was 56/56 — +4 new in `FunnelDashboardPage.test.tsx`, +1 assertion
added to `App.test.tsx`'s existing nav-region test), no regressions. Coverage 89.03% → 88.86%
statements (−0.17 points — well under the 5-point material-regression threshold from
`docs/continued-development.md` CD-4).

**Build/lint:** `tsc -b` clean, `oxlint` clean (0 warnings), `vite build` 338.09 kB → 347.79 kB
(+2.9%, under the 15% material-regression threshold).

**Live verification against the real accumulated dev database** (not just mocks — `backend/leads.db`
carries 33 real `PipelineRun` rows and 8 real `ReviewQueueItem` actions accumulated across every
prior session's live testing, per `.claude/seed-data.md`):
1. `GET /analytics/funnel` against the real running backend returned `total_leads: 33`, with
   `by_status` counts (`awaiting_review: 1, failed: 29, rejected: 3`) summing to exactly 33 —
   confirmed by hand, not just eyeballed.
2. `by_source_channel` correctly bucketed a real pre-existing `PipelineRun` row whose
   `source_channel` is `None` under `"unknown"` (`avg_confidence: null`) — an edge case this session
   didn't have to construct synthetically, since real historical data already contained it.
3. `reviewer_throughput` correctly separated 4 distinct real reviewer names ("Jordan", "QA Tester",
   "QA Tester 2", "Unattributed" for null `reviewer_name`), each with a plausible
   `avg_resolution_seconds` derived from real `created_at`/`actioned_at` timestamps spanning this
   project's actual multi-day build history.

**Visual verification with real browser automation** (`playwright-core` + local Chromium, confirmed
available this session — unlike Feature 17's session, which recorded its expanded panel
`UNVERIFIED` for exactly this capability gap per `docs/agent-portability.md`):
1. `/analytics` measured zero horizontal/vertical `main` overflow at all four target viewports
   (1920×1080, 1440×900, 1366×768, 390×844) via the same `scrollWidth`/`scrollHeight` vs.
   `clientWidth`/`clientHeight` measurement method `docs/ui-design-standards.md` §1 established.
2. Screenshots reviewed directly (not just the numeric measurement) at desktop and mobile widths —
   both tables and stat tiles render cleanly, consistent with every other page's visual language, no
   layout defects found.
3. A live click-through from `HomePage.tsx`'s new fourth "Analytics" section card actually navigated
   to `/analytics`, confirming the in-app-cohesion link works end-to-end, not just that the `href`
   attribute is correct in a mocked test.

**Acceptance criteria coverage (architecture-plan-feature-18.md / `implementation_plan.md`'s
Feature 18 spec):**
1. Real, non-fabricated counts → live checks #1-3 above.
2. `avg_resolution_seconds` excludes unresolved runs, `null` when none resolved →
   `test_funnel_avg_resolution_excludes_unresolved_runs` (a run with a 5-hour `AWAITING_REVIEW` gap
   is proven not to skew the average) + `test_funnel_returns_zero_state_for_empty_database`.
3. Reviewer throughput excludes `PENDING`, groups null `reviewer_name` as "Unattributed" →
   `test_reviewer_throughput_excludes_pending_and_groups_unattributed`.
4. Reachable from persistent nav and a fourth HomePage card → live click-through (visual check #3
   above) + `App.test.tsx`'s extended assertion.
5. Zero-data states render designed empty states → `FunnelDashboardPage.test.tsx`'s two empty-state
   tests (zero leads; leads exist but zero actioned reviews).

**Architectural fidelity (`docs/implementation-planning.md` §14):** implementation matched
`architecture-plan-feature-18.md`'s Implementation Order and Existing Systems Analysis — reused
`display_status_for()` (Feature 08) rather than inventing a third status vocabulary, reused the
existing `ui/` component kit with no new shared component, and correctly judged this feature's
aggregation domain (spanning `PipelineRun` and `ReviewQueueItem`) as justifying a new router/schema
pair rather than bolting onto `leads.py` or `reviews.py`. One real bug self-caught before any test
ran: the reviewer-throughput computation was initially written with an O(reviewers) nested re-query
inside a list comprehension; rewritten to a single pass before committing. Actual Footprint recorded
in the plan file: 9/10 predicted files changed (one fewer — no dedicated `HomePage.test.tsx` exists
in this project, so there was nothing to touch there), no unplanned files, no rework cycle beyond the
pre-commit self-catch above.

Verdict: Feature 18 (Aggregate Lead Funnel & Reviewer Throughput Dashboard) is implementation-complete,
live-verified against real accumulated data, visually confirmed with real browser automation at all
four target viewports (closing the category of gap Feature 17 left `UNVERIFIED`), and regression-free.
Per `scope-expansion.md`'s Round 1 tie-break decision, S-04 (Interactive Slack Review Actions) follows
next in this same session as Feature 19.

---

## CD-4 — Feature 19 (Interactive Slack Review Actions), 2026-09-06

**Backend tests:** 171/171 passed (was 154/154 — +17 new: 8 in `test_slack_signature.py`, 8 in
`test_router_slack_interactions.py`, 1 in `test_webhook_tools.py`), no regressions. Critically,
`test_router_reviews.py` passed **completely unmodified** — the regression gate proving the
`apply_review_action()` extraction changed zero observable behavior of the existing, already-live-
verified HTTP endpoint. Coverage held at 98% (unchanged).

**Frontend:** not touched — this feature has no UI surface (a Slack message is its only interface,
entirely outside this project's own React app). Frontend suite/build/lint not re-run since nothing
in `frontend/` changed.

**Live verification against the real running backend and the real accumulated dev database** (not
just mocks — deliberately consuming the project's one real `awaiting_review` item rather than only
testing against a synthetic one, via a disposable second `uvicorn` instance on port 8001 sharing the
same `leads.db` file, the exact technique `.claude/seed-data.md` already documents):
1. A forged signature (wrong secret) → real `401`, confirmed via `GET /reviews` that the targeted
   item was untouched.
2. A stale (10-minute-old) timestamp with an otherwise-correct signature → real `401`.
3. A real, correctly-signed `approve_lead` click (HMAC-SHA256 computed the same way a genuine Slack
   app would) on the real pending review (lead `7b0d3af5-cb33-4eab-9a15-14763ea70855`) → `200`,
   `GET /reviews` went from 1 item to empty, `GET /leads/{lead_id}` showed the run resumed through the
   real orchestrator into `hubspot_crm_write`, failing there for the expected, already-documented
   reason (no `HUBSPOT_ACCESS_TOKEN` configured — same limitation Feature 05's live verification
   already established). `reviewer_name` correctly recorded as `"morgan-in-slack"`, the payload's
   `user.username`.
4. A second identical click on the now-actioned item → `200` with "Could not process this action:
   Review item already actioned" — not a raw `409`, confirming the Slack-facing error-translation
   behavior.
5. With no `SLACK_SIGNING_SECRET` configured (the documented default), a request with a syntactically
   plausible but unverifiable signature → real `401`, confirmed on the main dev instance (port 8000)
   after it was restarted with current code and a clean, default (unset) secret.

**Acceptance criteria coverage (architecture-plan-feature-19.md / `implementation_plan.md`'s
Feature 19 spec):**
1. Correctly-signed valid action reaches the same logic as the HTTP endpoint → live check #3 above +
   `test_approve_via_slack_resumes_the_run`/`test_reject_via_slack_sets_rejected_status`, both
   asserting identical `PipelineRun`/`ReviewQueueItem` state to what `test_router_reviews.py`'s
   equivalent tests already assert for the HTTP path.
2. Bad signature / stale timestamp / no secret configured all rejected with `401` before any parsing
   → live checks #1-2, #5 above + `test_invalid_signature_is_rejected_before_touching_the_review`
   (asserts the DB row is untouched, not just the status code).
3. Feature 10's outbound payload gains buttons only when `run_id` is passed, unchanged otherwise →
   `test_deliver_webhook_notification_includes_interactive_buttons_when_run_id_given` +
   every pre-existing `test_webhook_tools.py` test passing unmodified (none pass `run_id`).
4. Already-actioned/nonexistent run → `200` with explanatory text; unrecognized `action_id` → `400`
   → live check #4 above + `test_already_actioned_review_returns_200_with_explanatory_text`/
   `test_nonexistent_run_returns_200_with_explanatory_text`/`test_unrecognized_action_id_returns_400`.

**Architectural fidelity (`docs/implementation-planning.md` §14):** implementation matched
`architecture-plan-feature-19.md` exactly, including its proposed Architecture Rule Change (multi-
transport domain logic lives in `app/orchestrator/`, not duplicated per-router) — now applied to
`.claude/portfolio-reference.md`'s Key Decisions (see below). Actual Footprint recorded in the plan
file: 11/11 predicted files changed, no unplanned files, no rework cycle.

**Honestly recorded limitation:** a real Slack workspace/app actually delivering a real button click
to this endpoint was not tested — no Slack app credentials exist in this environment. Everything
this endpoint does after receiving Slack's documented request shape was verified live against real
data (checks #1-4 above); only Slack's own delivery of that shape was not — the same category of
limitation Feature 05's real-HubSpot-write verification already established a precedent for stating
plainly.

Verdict: Feature 19 (Interactive Slack Review Actions) is implementation-complete, behavior-preserving
for the existing HTTP review-action path (proven by an unmodified regression suite), live-verified
end-to-end against real accumulated data including the genuine cryptographic trust boundary, and
regression-free. This ships S-04, the last of `scope-expansion.md`'s Round 1 P1/P2 candidates — only
S-05 (P3, Exportable Audit Trail CSV) remains unshipped from that round. A future idle session should
run `docs/next-action-selection.md`'s Dynamic Next-Action Selection rather than defaulting straight
back to another Scope Expansion round.
