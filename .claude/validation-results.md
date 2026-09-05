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
