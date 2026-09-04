IMPLEMENTATION PLAN
====================

Feature / Round: Feature 05 — HubSpot CRM Write Stage
Classification: New feature, Cross-system integration, Architecture change
Planning Depth: Deep — this is the project's own stated highest-risk external integration, and the
analysis below surfaces two genuine architecture gaps the existing design doesn't yet cover: (1) this
stage needs read access to two `LeadPipelineState` slices at once, which the current singular
`input_slice` mechanism can't express, and (2) the existing "recoverable failure → encode as data,
never raise" Key Decision, read literally, contradicts what this feature's own spec explicitly wants
(a genuine write failure must halt the run). Both need an explicit, conflict-checked resolution before
Step 6 writes code — exactly what Deep tier exists for.

Objective
Replace `graph.py`'s "crm_write" stub with a real `HubSpotCrmWriteStage` that performs an idempotent,
retry-safe create-or-update against HubSpot's real sandbox from the merged intake+enrichment record,
using write-only tooling no other stage can reach.

Existing Systems Analysis
- Reusable:
  - `app/orchestrator/state.py`'s `CrmWriteSlice` — already exists (`hubspot_record_id`,
    `write_status`) from Feature 01's bootstrap; extended, not replaced (see Modify below).
  - `app/orchestrator/tools/hubspot_tools.py`'s `search_contact(...)` — the new write tool's dedupe
    lookup reuses this function directly as a module-internal Python call (not a second registered
    tool), so the CRM Write stage never gains registry-level search access — see Architecture Rule
    Change #3 below for why that distinction matters.
  - `app/orchestrator/tools/__init__.py`'s existing shared `httpx.Client(timeout=5.0)` instance
    (constructed for `search_contact` in Feature 04) — the new `hubspot_write` registration reuses the
    same client, no second one constructed.
  - `app/core/config.py`'s `hubspot_base_url`/`hubspot_access_token` — as-is, no new config field.
  - `app/orchestrator/graph.py`'s `_STAGE_ORDER` (already lists `("crm_write", "hubspot_crm_write",
    "Feature 05")`) and the `crm_write_stage` → `_route_or_fail("notify")` edge — both already wired
    by Feature 01; no routing change needed, only the stub swap.
  - **Naming precedent already fixed by Feature 04's plan**: `test_orchestrator_tool_scope.py` already
    uses the tool name `"hubspot_write"` and the stage name `"hubspot_crm_write"` in tests written
    ahead of this feature. Both reused verbatim, not re-decided.
  - `app/orchestrator/tools/hubspot_tools.py`'s existing `_HttpClient`/`_HttpResponse` `Protocol`s — the
    new `write_contact` reuses the same injected-client-double testing pattern `search_contact`
    established, no new fake-client shape invented.
- Duplication Risk Flagged: none found — no create/update/retry/backoff code exists anywhere yet
  (grep-confirmed: `hubspot_tools.py` currently contains only `search_contact` and its two Protocols).
- Modify:
  - `app/orchestrator/state.py`'s `CrmWriteSlice` — needs `dedupe_key_used`, `dedupe_uncertain`, and
    `retry_count`, none of which exist today, to satisfy the spec's dedupe-uncertainty and
    retry-visibility requirements. Also needs a new small merge schema (see New below) and a doc-comment
    fix (see Architecture Rule Change #2 — `write_status` in practice never becomes `"failed"`, since a
    failed write raises instead of returning a slice).
  - `app/orchestrator/contracts.py`'s `Stage` — needs a new `input_slices` companion field (see
    Architecture Rule Change #1). Additive; the existing singular `input_slice` is unchanged and stays
    in active use by Feature 03/04.
  - `app/orchestrator/graph.py`'s `_make_node` — needs one new branch to build a merged multi-slice
    input when a stage declares `input_slices`; `default_stages()["crm_write"]` becomes
    `HubSpotCrmWriteStage()`.
  - `app/orchestrator/tools/hubspot_tools.py` — gains `write_contact(...)` and `HubSpotWriteError`.
  - `app/orchestrator/tools/__init__.py` — `register_default_tools` gains a second HubSpot registration
    (`"hubspot_write"`) alongside the existing `"hubspot_search_contact"`.
- New:
  - `app/orchestrator/stages/hubspot_crm_write.py` — `HubSpotCrmWriteStage`.
  - `app/orchestrator/state.py`'s `MergedIntakeEnrichment` — a minimal read-time merge schema (see
    Architecture Rule Change #1), not a new persisted slice.
- Navigation Relationships Flagged: none — backend-only, matches Features 01-04; no UI surface yet.

System Impact Map
```
FEATURE 05 — HubSpot CRM Write Stage
│
├── Backend
│   ├── app/orchestrator/stages/hubspot_crm_write.py (new) — HubSpotCrmWriteStage: builds the merged
│   │     record (intake primary, enrichment.resolved_fields fallback), calls the write-only tool,
│   │     never catches the failure-after-retries-exhausted case (see Architecture Rule Change #2)
│   ├── app/orchestrator/tools/hubspot_tools.py (modify) — write_contact(...): dedupe-lookup-then-
│   │     create-or-update, retry-with-backoff on 429/5xx, immediate raise on 401/403/other 4xx
│   ├── app/orchestrator/tools/__init__.py (modify) — registers "hubspot_write" on the existing shared
│   │     httpx.Client
│   ├── app/orchestrator/contracts.py (modify) — Stage gains input_slices (plural companion to
│   │     input_slice)
│   ├── app/orchestrator/state.py (modify) — CrmWriteSlice gains dedupe_key_used/dedupe_uncertain/
│   │     retry_count; new MergedIntakeEnrichment schema
│   └── app/orchestrator/graph.py (modify) — _make_node's new multi-slice branch;
│         default_stages()["crm_write"] = HubSpotCrmWriteStage()
│
├── Database
│   └── none — CrmWriteSlice persists via Feature 01's existing StageTrace mechanism unchanged
│
├── Existing Systems (reused, not duplicated)
│   ├── app/orchestrator/tools/hubspot_tools.py — search_contact (Feature 04), called internally by
│   │     write_contact for the dedupe lookup, never re-implemented
│   ├── app/orchestrator/tool_scope.py — ToolRegistry/ScopedToolProxy (as-is; still the sole
│   │     enforcement point for write-only scoping)
│   ├── app/orchestrator/graph.py — _STAGE_ORDER, crm_write_stage's existing _route_or_fail("notify")
│   │     edge (unmodified)
│   └── app/core/config.py — hubspot_base_url, hubspot_access_token (as-is)
│
├── Navigation
│   └── none this feature — backend only
│
└── AI
    └── none — deterministic dedupe + HTTP retry logic, no LLM call
```

Implementation Order (Dependency Graph)
1. **app/orchestrator/contracts.py** — add `input_slices: ClassVar[tuple[str, ...] | None] = None` to
   `Stage`, directly beside the existing `input_slice`. No change to `effective_input_slice` or any
   existing behavior — every current stage leaves this `None` and is unaffected. Existing files:
   `contracts.py`. New files: none. Dependencies: none. Validation: extend
   `test_orchestrator_contracts.py` with a construction test asserting `input_slices` defaults to
   `None` on a stage that doesn't set it (mirrors the existing `input_slice` default test).
2. **app/orchestrator/state.py** — extend `CrmWriteSlice` with `dedupe_key_used: str | None = None`,
   `dedupe_uncertain: bool = False`, `retry_count: int = 0`; fix its `write_status` comment to read
   `# "created" | "updated" — never "failed": a failed write raises instead of returning a slice, see
   architecture-plan-feature-05.md`. Add `MergedIntakeEnrichment(BaseModel)` with fields `intake:
   IntakeSlice` and `enrichment: EnrichmentSlice` — field names chosen to exactly match the slice names
   `HubSpotCrmWriteStage.input_slices` will declare, since step 3 builds it generically by name.
   Existing files: `state.py`. New files: none. Dependencies: step 1 (uses no new contracts.py symbol
   directly, but logically follows it in review order). Validation: extend
   `test_orchestrator_state.py` with a default-construction test for the three new `CrmWriteSlice`
   fields and a construction test for `MergedIntakeEnrichment`.
3. **app/orchestrator/graph.py** — in `_make_node`, replace the single line `slice_in =
   getattr(state, stage.effective_input_slice)` with: if `stage.input_slices is not None`, build
   `slice_in = stage.input_schema(**{name: getattr(state, name) for name in stage.input_slices})`;
   else keep the existing single-slice line unchanged. This is fully generic — it works for any future
   multi-slice stage, not just this one, by relying on `input_schema`'s field names matching
   `input_slices`' slice names. Existing files: `graph.py`. New files: none. Dependencies: steps 1-2.
   Validation: existing `test_orchestrator_graph.py` tests continue passing unmodified (no stage today
   sets `input_slices`, so the new branch is never taken by them). Add one new test constructing a
   minimal multi-slice fake stage directly against `_make_node` (or `build_graph`) to prove the merge
   branch itself, independent of Feature 05's own stage.
4. **app/orchestrator/tools/hubspot_tools.py** (modify) — add `class HubSpotWriteError(Exception)` and
   `write_contact(client, base_url, token, *, phone=None, email=None, properties: dict, max_retries:
   int = 3, base_delay: float = 0.5, sleep=time.sleep) -> dict`. Behavior: one retryable "attempt" =
   dedupe lookup (reuses `search_contact(client, base_url, token, phone=phone, email=email)` directly,
   exact-key only — deliberately no name-fuzzy fallback here, see Risks) followed by a PATCH (if a
   match was found) or POST (if not) to `{base_url}/crm/v3/objects/contacts[/{id}]` with
   `{"properties": properties}`. If neither `phone` nor `email` is given, skip the dedupe lookup
   entirely and go straight to POST, setting `dedupe_uncertain=True`. Wrap the whole attempt (lookup +
   write) in a loop up to `max_retries + 1` times: on an `httpx.HTTPStatusError` whose status is `429`
   or in `[500, 600)`, call `sleep(float(exc.response.headers.get("Retry-After", base_delay * 2 **
   attempt)))` and retry; on `401`/`403`, raise `HubSpotWriteError(f"HubSpot auth failed
   ({status}): ...")` immediately, no retry; on any other 4xx, raise `HubSpotWriteError(f"HubSpot
   write rejected ({status}): ...")` immediately, no retry; once `max_retries` is exhausted on a
   retryable error, raise `HubSpotWriteError(f"HubSpot write failed after {max_retries} retries:
   ...")`. Returns `{"id": ..., "status": "created" | "updated", "dedupe_key_used": "phone" | "email" |
   None, "dedupe_uncertain": bool, "retry_count": int}` on success. Existing files: `hubspot_tools.py`
   (add to, `search_contact` untouched), `tool_scope.py`/`core/config.py` (as-is). New files: none.
   Dependencies: none beyond already-pinned `httpx`; `sleep` injected (defaults to `time.sleep`) so
   tests never incur real delay. Validation: unit tests using the existing fake-client-double pattern:
   an exact-match hit → PATCH/`"updated"`; no match → POST/`"created"`; a 429-then-200 sequence →
   retried once, `retry_count == 1`, succeeds; a 429 on every attempt through `max_retries` → raises
   `HubSpotWriteError`; a 401 on the first attempt → raises `HubSpotWriteError` immediately with zero
   sleep calls; neither phone nor email given → POST directly, `dedupe_uncertain=True`, zero lookup
   calls made.
5. **app/orchestrator/tools/__init__.py** — `register_default_tools` adds
   `registry.register("hubspot_write", functools.partial(write_contact, http_client,
   settings.hubspot_base_url, settings.hubspot_access_token))`, reusing the same `http_client` variable
   already constructed for `"hubspot_search_contact"`. Existing files: `tool_scope.py` (as-is). New
   files: none. Modified files: `tools/__init__.py`. Dependencies: step 4. Validation: extend
   `test_orchestrator_tools.py`'s `register_default_tools` test to also assert `"hubspot_write"` is
   registered and distinct from `"hubspot_search_contact"`.
6. **app/orchestrator/stages/hubspot_crm_write.py** (new) — `HubSpotCrmWriteStage(Stage[
   MergedIntakeEnrichment, CrmWriteSlice])`: `name = "hubspot_crm_write"`, `input_schema =
   MergedIntakeEnrichment`, `output_schema = CrmWriteSlice`, `allowed_tools =
   frozenset({"hubspot_write"})`, `state_slice = "crm_write"`, `input_slices = ("intake",
   "enrichment")`. `run(data, tools) -> CrmWriteSlice`:
   - `phone = data.intake.phone or data.enrichment.resolved_fields.get("phone")`; same pattern for
     `email`; `name = data.intake.name or data.enrichment.resolved_fields.get("name")` — the exact
     "intake primary, enrichment fallback" rule `.claude/portfolio-reference.md`'s existing Key
     Decision (set by Feature 04's plan) already states.
   - `properties = {"email": email, "phone": phone, "firstname": name}` (feature-local field mapping,
     not architectural — see Feature-Specific Requirements).
   - `result = tools.call("hubspot_write", phone=phone, email=email, properties=properties)` — **no
     try/except.** A `HubSpotWriteError` (or any other exception) propagates straight out of `run()`,
     deliberately, per Architecture Rule Change #2 below.
   - Return `CrmWriteSlice(hubspot_record_id=result["id"], write_status=result["status"],
     dedupe_key_used=result["dedupe_key_used"], dedupe_uncertain=result["dedupe_uncertain"],
     retry_count=result["retry_count"])`.
   Existing files: `state.py` (step 2), `contracts.py` (step 1). New files:
   `app/orchestrator/stages/hubspot_crm_write.py`. Dependencies: steps 1-5. Validation: unit tests per
   Acceptance Criteria below, using a fake `"hubspot_write"` tool function registered directly into a
   `ToolRegistry` (no real HubSpot call in the core suite, matching Features 03/04's pattern), plus one
   boundary test (extending `test_orchestrator_tool_scope.py`'s existing pattern) proving this stage's
   real `allowed_tools` cannot reach `"hubspot_search_contact"`.
7. **app/orchestrator/graph.py** — add `from app.orchestrator.stages.hubspot_crm_write import
   HubSpotCrmWriteStage`; `default_stages()["crm_write"] = HubSpotCrmWriteStage()`. No routing change —
   `crm_write_stage`'s existing `_route_or_fail("notify")` edge already sends any `RunStatus.FAILED`
   straight to `END`, which is exactly what a raised `HubSpotWriteError` now produces via `_make_node`'s
   existing exception handler. Existing files: `graph.py`. New files: none. Dependencies: steps 1-6.
   Validation: existing `test_orchestrator_graph.py` fake-stage tests continue passing (its
   `_FakeStage`-based `crm_write` fixture is unaffected). Add one new test chaining real
   `IntentClassificationStage` → real `DataEnrichmentStage` → real `HubSpotCrmWriteStage` (fake
   `"hubspot_write"` tool) to prove the real stage's success path reaches `notify_stage`, mirroring
   Feature 04's own graph-level chaining test; add a second new test where the fake `"hubspot_write"`
   tool raises `HubSpotWriteError`, proving `final.run.status == RunStatus.FAILED` and
   `final.run.failed_stage == "hubspot_crm_write"` — the real-stage analogue of the fake-stage version
   of this exact assertion `test_orchestrator_graph.py` already has today.

Architecture Rule Changes
- [ ] **"A stage that needs read access to more than one `LeadPipelineState` slice declares
  `input_slices: ClassVar[tuple[str, ...]]` (plural), and its `input_schema` must be a merge-only
  Pydantic model whose field names exactly match those slice names. `app/orchestrator/graph.py`'s
  `_make_node` builds it generically: `stage.input_schema(**{name: getattr(state, name) for name in
  stage.input_slices})`. Write access is unaffected — `_make_node` still writes only `{stage.state_slice:
  output}`, so a multi-slice-reading stage can still write to exactly one slice."** — Conflict check:
  none found. This is additive: the existing singular `input_slice`/`effective_input_slice` mechanism
  (Feature 02/03) is completely unchanged and stays in active use by `IntentClassificationStage` and
  `DataEnrichmentStage` (`input_slices` defaults to `None`, and `_make_node`'s original single-slice
  branch is preserved verbatim for both). Worth naming explicitly: the per-stage **read** boundary has
  never been runtime-enforced the way `allowed_tools` is (`ScopedToolProxy` enforces tool access at
  call time; `input_slice`/`input_slices` has only ever been a declared contract, checked by review and
  by `_make_node`'s own construction logic, not by a hard runtime gate). This change doesn't alter that
  asymmetry — it only extends the declared-read side to a documented multi-slice case, for the first
  time needed because Feature 05 is the first stage whose spec genuinely requires two upstream slices
  (Feature 04's own "merged lead record is read-time" Key Decision already anticipated this need without
  yet building the mechanism for it).
- [ ] **CONFLICT DETECTED AND RESOLVED — "recoverable failure, never raise" reworded.** Existing Key
  Decision (Feature 03, broadened by Feature 04): "...Raising from `Stage.run()` stays reserved for
  genuinely unexpected/bug-level errors, never a failure mode a feature's own spec already anticipates."
  Feature 05's own spec explicitly anticipates a failure mode (a write failing after retries are
  exhausted) and explicitly wants it to **halt** the run ("marks the lead's pipeline run as FAILED at
  this stage rather than silently proceeding to Notification as if the write succeeded") — read
  literally, the existing rule's last clause forbids exactly what this feature's spec requires.
  **Resolution — generalize the rule; the deciding question was never "does the spec anticipate this
  failure," it's "does the spec want the run to continue past it or halt for this lead."** Every
  recoverable failure Features 03/04 encoded as data (a classification call failing twice, an
  enrichment lookup timing out) was *also* explicitly spec-anticipated — the real distinguishing
  property is that those specs wanted the pipeline to keep moving (route to Review, or proceed as a
  no-op). Feature 05's spec wants the opposite: this lead's run stops here. Reworded Key Decision: "A
  stage's own external-system failure is encoded as data in its output slice, never raised, when the
  owning feature's spec wants the pipeline to continue past it (e.g. route to Human Review, or proceed
  as a no-op) — regardless of whether the spec anticipates the failure. A stage raises from `run()`,
  letting `_make_node`'s existing exception handler set `RunStatus.FAILED`, when the owning feature's
  spec wants this lead's run to halt at this stage instead — this now includes spec-anticipated,
  intentionally-terminal failures (e.g. Feature 05's exhausted-retry write failure, or an invalid/
  expired auth token), not only genuinely unexpected bugs." This is a wording generalization of an
  existing rule, not two rules standing side by side — the old wording is superseded, not kept
  alongside the new one.
- [ ] **"A tool binding's dedupe-before-write mechanism reuses an existing read-only lookup tool as a
  direct in-module function call, never a second registered tool exposed to the writing stage's
  `allowed_tools`."** Concretely: `write_contact` calls `search_contact` directly inside
  `hubspot_tools.py`; `HubSpotCrmWriteStage.allowed_tools` is `frozenset({"hubspot_write"})` only, never
  `"hubspot_search_contact"`. — Conflict check: none found; this is required by the existing Key
  Decision (Feature 04) that `hubspot_search_contact` and `hubspot_write` must be "granted to different
  stages' `allowed_tools` — never the same name gating both" — this rule states the corollary those
  words implied but didn't spell out: the write-side stage doesn't get search access *at all*, even
  though its underlying tool internally needs to search for dedupe purposes. Reuse happens at the Python
  function level, not the tool-scoping level, so the write-only boundary the spec explicitly requires
  ("no other stage may call HubSpot's write API directly") stays real under code inspection without also
  quietly widening what the write stage itself can reach.

Feature-Specific Requirements
- `_MAX_RETRIES = 3`, `_BASE_DELAY = 0.5` (module constants in `hubspot_tools.py`) and the
  `properties = {"email": ..., "phone": ..., "firstname": name}` field mapping (no last-name splitting
  — `IntakeSlice` only ever has one `name` field) are feature-local detail, not promoted to Key
  Decisions.
- Dedupe lookup for the write path is exact-key only (phone or email) — deliberately **no** name-fuzzy
  fallback, unlike Enrichment's read-side fuzzy match. See Risks below for why.
- `retry_count` is recorded in `CrmWriteSlice` purely for observability (Feature 08's trace view); it
  is never used to alter routing.

Risks
- Risk: A name-fuzzy dedupe match on the write path could update the wrong person's live CRM record —
  a materially worse mistake than Enrichment's read-side false-positive merge (which only ever affects
  this project's own local state, not a real external record). Mitigation: write-side dedupe is
  exact-key only (phone/email); if neither is available, always create a new record and set
  `dedupe_uncertain=True` rather than guessing, exactly as the spec's edge case requires.
- Risk: A broad "retry the whole attempt" loop (dedupe lookup + write together) could double-create a
  contact if the dedupe lookup itself flakes independently of the write. Mitigation: the dedupe lookup
  is a read; re-running it on retry is idempotent by construction — the actual write-or-create decision
  is re-evaluated fresh each attempt from the latest lookup result, so a stale first-attempt lookup
  never causes a duplicate create on a later attempt.
- Risk: `HUBSPOT_ACCESS_TOKEN` isn't set in this environment yet (`.claude/pipeline-reference.md`'s
  standing Deviations note, already true for Feature 04's read access). A real write call will fail
  auth until a human provisions the sandbox token. Mitigation: unit tests use a fake tool/client double
  throughout, matching Features 03/04's approach; this is the same standing deviation, now also true
  for write access, not a new blocker.
- Risk: Treating auth failures (401/403) as immediately-raised, non-retryable could mask a transient
  token-refresh race in a real deployment. Mitigation: out of scope for a sandbox Private App token
  (which doesn't expire on a refresh cycle the way OAuth access tokens do); if this project later moves
  to OAuth, that's a future architecture-plan's problem, not a reason to add retry complexity here now.
- Risk: The generalized `input_slices` mechanism (Architecture Rule Change #1) could be over-used by a
  future feature to bypass the "only reads what it needs" discipline by requesting many slices at once.
  Mitigation: `_make_node`'s implementation only ever includes slices a stage explicitly names in
  `input_slices` — nothing accidental leaks in — and Step 7/CD-4's review of any future plan using this
  mechanism should treat a long `input_slices` tuple as a code-smell worth questioning, the same way an
  overly broad `allowed_tools` set already would be.

Acceptance Criteria
- [ ] A fake `"hubspot_write"` tool returning `{"id": "hs-1", "status": "created", ...}` for a lead
  with no existing match produces `CrmWriteSlice(hubspot_record_id="hs-1", write_status="created", ...)`.
- [ ] A fake `"hubspot_write"` tool simulating a retried-then-succeeded write (`retry_count=1`,
  `status="updated"`) is reflected verbatim in the returned `CrmWriteSlice`.
- [ ] `write_contact` unit tests (not the stage): a 429-then-200 HTTP sequence retries exactly once and
  succeeds with `retry_count == 1`; a 429 on every attempt through `max_retries` raises
  `HubSpotWriteError`; a 401 on the first attempt raises `HubSpotWriteError` immediately with zero
  `sleep` calls recorded.
- [ ] `HubSpotCrmWriteStage.run()` re-raises a `HubSpotWriteError` from the tool call — it does **not**
  catch it — and a graph-level test confirms this produces `final.run.status == RunStatus.FAILED` and
  `final.run.failed_stage == "hubspot_crm_write"`, never a silent `notify_stage` transition.
- [ ] `HubSpotCrmWriteStage.allowed_tools` contains only `"hubspot_write"` — a boundary test proves
  calling `"hubspot_search_contact"` through this stage's proxy raises `OutOfScopeToolError`.
- [ ] A merged-record test (real `_make_node` construction, not just the stage in isolation) proves a
  lead whose `IntakeSlice.email` is `None` but whose `EnrichmentSlice.resolved_fields["email"]` is set
  reaches `HubSpotCrmWriteStage.run()` with that enrichment-sourced email — proving the read-time merge
  Feature 04's Key Decision described is now actually wired, not just documented.
- [ ] A lead with neither phone nor email present calls `write_contact` with `dedupe_uncertain=True`
  and makes zero dedupe-lookup calls (verified via the fake client's call log).

Validation Requirements
Step 7 must confirm, by grep and not just test pass/fail, that `hubspot_crm_write.py` never imports
`httpx` directly — it reaches HubSpot only through `tools.call("hubspot_write", ...)`. Step 7 must also
confirm `HubSpotCrmWriteStage.run()` genuinely contains no `try/except` around the `tools.call(...)`
line (the deliberate deviation from Features 03/04's pattern — Architecture Rule Change #2), and that
the new graph-level FAILED-path test exercises the real stage, not a fake substitution. If
`HUBSPOT_ACCESS_TOKEN` is set in the verification environment, Step 7 may additionally run one real
create call through `hubspot_tools.write_contact` against the sandbox and report the result —
informative only, not required to pass this gate, mirroring Features 03/04's optional-live-smoke-call
precedent.

Predicted Footprint
Files predicted to change: 2 new (`app/orchestrator/stages/hubspot_crm_write.py`,
`app/tests/test_stage_hubspot_crm_write.py`) + 7 modified (`app/orchestrator/contracts.py`,
`app/orchestrator/state.py`, `app/orchestrator/graph.py`, `app/orchestrator/tools/hubspot_tools.py`,
`app/orchestrator/tools/__init__.py`, `app/tests/test_orchestrator_contracts.py`,
`app/tests/test_orchestrator_state.py`, `app/tests/test_orchestrator_tools.py`,
`app/tests/test_orchestrator_tool_scope.py`, `app/tests/test_orchestrator_graph.py`) — 9 files modified
in total once fully counted.
Systems predicted to touch: `Stage` contract (additive `input_slices`), `CrmWriteSlice` (extended),
`hubspot_tools.py` (second binding), `ToolRegistry` production population (third real tool),
`default_stages()`, `_make_node` (new generic multi-slice branch). No database/migration changes.

--- filled in later, by Step 7, once implementation is verified ---
Actual Footprint
Files actually changed: matches Predicted Footprint exactly — 2 new
(`app/orchestrator/stages/hubspot_crm_write.py`, `app/tests/test_stage_hubspot_crm_write.py`) + 9
modified (`app/orchestrator/contracts.py`, `app/orchestrator/state.py`, `app/orchestrator/graph.py`,
`app/orchestrator/tools/hubspot_tools.py`, `app/orchestrator/tools/__init__.py`,
`app/tests/test_orchestrator_contracts.py`, `app/tests/test_orchestrator_state.py`,
`app/tests/test_orchestrator_tools.py`, `app/tests/test_orchestrator_tool_scope.py`,
`app/tests/test_orchestrator_graph.py` — 10 modified once fully counted, one more than predicted:
`.claude/portfolio-reference.md` also gained a Key Decision entry, not itself a code file).
Deviations from plan: One genuine implementation-time discovery not anticipated by this plan's
Existing Systems Analysis: `search_contact` returns only a matched contact's `properties`, never its
internal HubSpot object id, which `write_contact`'s PATCH-based update needs to address the record.
Resolved without modifying `search_contact` or its existing tests — `write_contact` addresses an
update via HubSpot's own `idProperty` upsert query parameter (the dedupe key's own value as the path
segment) instead of a second lookup to recover the id. Recorded as a new Key Decision in
`.claude/portfolio-reference.md` (see Step 6's `execution-log.md` entry). No other deviation from the
Implementation Order's 7 steps.
Rework required: none — all 79 tests (59 pre-existing + 20 new) passed on the first `pytest` run; no
fix cycle needed.
