# Portfolio Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-05 (Step 6 — Feature 10, External Notification Delivery, Group_F10
COMPLETED. Extended `persist_outcome_notification()` with a best-effort, never-raising external
webhook delivery gated to `awaiting_review` only; new `webhook_tools.py`, two new nullable
`Notification` columns, one new `notification_webhook_url` setting. Architecture Map rows updated for
`config.py`, `graph.py`, `orchestrator/tools/`, `models/notification.py`, `schemas/notification.py`,
and `alembic/`. Live-verified against the real local model across all three delivery paths (sent/
failed/skipped) — see `.claude/execution-log.md`/`validation-results.md`'s Feature 10 entries. Prior
update: `.claude/refinement-backlog.md`'s RB-004 — `HomePage.tsx` rewritten from Step 4's bootstrap
placeholder into a real landing page linking to `/leads`, `/reviews`, and `/benchmark`. Prior to that:
RB-003 — Architecture Map backfilled with the remaining Feature 08 rows [`routers/leads.py`,
`LeadListPage.tsx`, `LeadDetailPage.tsx`, `HomePage.tsx`, `lib/api.ts`, `lib/stageOrder.ts`] and the two
previously-uncited migrations, plus rewording the three stale directory-level placeholder rows to
present tense.)

Read this before opening source files. Only open the actual code when this doc doesn't answer the
question.

---

## Project Overview

**What it does:** A multi-stage AI agent that ingests inbound sales leads (web form, email, or
missed-call callback), classifies intent/urgency, enriches missing data, writes the result into a
real CRM (HubSpot's free developer sandbox), and routes low-confidence cases to a human reviewer
instead of acting on them blindly. Each pipeline stage is a genuinely separate unit with its own
scoped tool access and its own piece of state — not one large prompt relabeled as "agents."

**Key constraints:** Full stack must run free by default (no paid CRM tier, no paid vector DB); any
paid LLM API is an optional, explicitly-justified fallback only. The per-stage tool/state boundary
must be architecturally real under code inspection — this is the project's Critical risk. The
Multi-Agent Orchestration stretch goal is explicitly out of scope this round (locked in
`implementation_plan.md`) — do not re-add mid-build.

**Success criteria:** All Tier 1 features (8) working end-to-end against the real HubSpot sandbox
with idempotent writes; a measured (not assumed) classification-accuracy benchmark; an
observability view usable as a live client-conversation walkthrough; ≥9.0/10 at the Step 13
portfolio gate (Mode: STANDARD).

---

## Architecture Map

| Path | Purpose |
|---|---|
| `backend/main.py` | FastAPI app entrypoint — CORS, router registration |
| `backend/app/core/config.py` | Pydantic settings (env-driven): DB URL, Ollama config, HubSpot token, confidence threshold, `notification_webhook_url` (Feature 10, unset by default) |
| `backend/app/database/session.py` | SQLAlchemy engine/session/Base (SQLite dev DB: `backend/leads.db`) |
| `backend/app/models/` | SQLAlchemy ORM models (lead records, stage traces, review queue — populated in Step 6) |
| `backend/app/schemas/` | Pydantic request/response schemas (populated in Step 6) |
| `backend/app/routers/` | FastAPI route modules — `health.py` scaffolded; per-feature routers added in Step 6 |
| `backend/app/orchestrator/contracts.py` | `Stage` ABC contract every pipeline stage implements (input/output schema, `allowed_tools`, `state_slice`) |
| `backend/app/orchestrator/state.py` | `LeadPipelineState` — one Pydantic slice per stage (intake, classification, enrichment, crm_write, review, notification) + run metadata |
| `backend/app/orchestrator/tool_scope.py` | `ToolRegistry`/`ScopedToolProxy` — the enforced per-stage tool-access boundary; a stage only ever reaches a tool through its scoped proxy |
| `backend/app/orchestrator/errors.py` | `OutOfScopeToolError`, `StageExecutionError`, `StateValidationError` |
| `backend/app/orchestrator/graph.py` | LangGraph `StateGraph` wiring the 6 stages, `run_pipeline()`/`resume_pipeline()` entry points; `persist_outcome_notification()` fires the notification stage directly for the three terminal transitions (failure, awaiting-review, reject) that never reach the graph's own `notify_stage` node; `_mark_completed_if_still_running()` is the sole place `RunStatus.COMPLETED` is assigned; also where Feature 10's external delivery hook lives, gated to `outcome_type == "awaiting_review"` only, calling `webhook_tools.py` directly (bypassing `ToolRegistry`/`ScopedToolProxy` — see Key Decisions) |
| `backend/app/orchestrator/stages/intent_classification.py` | Feature 03's `IntentClassificationStage` — calls `ollama_classify` via the scoped tool proxy, retry-once-then-fail-closed |
| `backend/app/orchestrator/stages/data_enrichment.py` | Feature 04's `DataEnrichmentStage` — calls `hubspot_search_contact` via the scoped tool proxy; exact-key phone/email match or `difflib`-scored fuzzy name match, merges only fields Intake left null, never raises |
| `backend/app/orchestrator/stages/hubspot_crm_write.py` | Feature 05's `HubSpotCrmWriteStage` — write-only (`hubspot_write` alone); reads both `intake` and `enrichment` via `input_slices`; calls `tools.call("hubspot_write", ...)` with no try/except so a write failure halts the run |
| `backend/app/orchestrator/stages/human_review.py` | Feature 06's `HumanReviewStage` — pure gate, no tool access; unconditionally returns `ReviewSlice(queued=True, ...)` (the routing decision was already made by `_route_after_enrich`) |
| `backend/app/orchestrator/stages/outcome_notification.py` | Feature 07's `OutcomeNotificationStage` — pure signaling, no tool access; maps `run.status` to one of `auto_processed`/`awaiting_review`/`rejected`/`failed` and builds `message`/`detail_link` |
| `backend/app/orchestrator/tools/` | Real tool bindings for external systems, one module per system (`ollama_tools.py`, `hubspot_tools.py`, `webhook_tools.py`), wired by `register_default_tools()`; `hubspot_tools.py` holds both `search_contact` (read-only) and `write_contact` (write-only, retry-with-backoff) |
| `backend/app/orchestrator/tools/webhook_tools.py` | Feature 10's `deliver_webhook_notification()` — single-attempt, never-raising POST of a Slack-compatible payload to an operator-configured incoming webhook; NOT registered through `ToolRegistry` (called directly by `persist_outcome_notification()` — see Key Decisions); `error` built from status code/exception type only, never the webhook URL itself |
| `backend/app/models/pipeline_run.py` | `PipelineRun`/`StageTrace` SQLAlchemy models — every stage transition's persisted trace |
| `backend/app/models/review_queue.py` | Feature 06's `ReviewQueueItem` — a reviewer's actionable task for one paused run, carrying its own full-state resume snapshot (`state_snapshot`), distinct from the `PipelineRun`/`StageTrace` execution log |
| `backend/app/models/notification.py` | Feature 07's `Notification` — a persisted in-app notification per outcome event; `run_id` FK is not unique (a run can produce more than one over its lifetime); no addressee field (no `User`/auth model exists); Feature 10 added two nullable columns, `external_delivery_status`/`external_delivery_error` (`None` = never attempted — every outcome type other than `awaiting_review`) |
| `backend/app/schemas/pipeline.py` | Pydantic request/response schemas for triggering/querying a pipeline run |
| `backend/app/schemas/review.py` | Feature 06's `ReviewActionRequest`/`ReviewQueueItemOut` — reviewer-facing request/response shapes |
| `backend/app/schemas/notification.py` | Feature 07's `NotificationOut` — response shape for `GET /notifications`; Feature 10 added `external_delivery_status`/`external_delivery_error` (optional, `null` for pre-Feature-10 rows) |
| `backend/app/routers/reviews.py` | Feature 06: `GET /reviews`, `GET /reviews/{run_id}`, `POST /reviews/{run_id}/action` — concurrency-safe claim via an atomic `UPDATE ... WHERE status='PENDING'`; approve/edit re-enter the orchestrator via `resume_pipeline()`, reject sets `RunStatus.REJECTED` directly and also calls `persist_outcome_notification()` |
| `backend/app/routers/notifications.py` | Feature 07: `GET /notifications` (list, newest first) |
| `backend/app/routers/leads.py` | Feature 08: `GET /leads` (list, paginated, denormalized `source_channel`/`confidence_score` for filter/sort), `GET /leads/{lead_id}` (detail — full stage-trace timeline via `STAGE_ORDER`/`_STAGE_LABELS`, mirrored on the frontend by `lib/stageOrder.ts`) |
| `backend/alembic/` | DB migrations, wired to `app.database.session.Base` and `settings.database_url`; `245c694fed3d_*` creates `pipeline_run`/`stage_trace`; `68de6a50cacb_*` creates `review_queue_item`; `5f3cbe979b96_*` creates `notification`; `9217c457cc82_*` (Feature 08) adds `pipeline_run.source_channel`/`.confidence_score`; `b86e4d4ef367_*` (Feature 09) creates `benchmark_run`/`benchmark_case`; `a95fad549dbf_*` (Feature 10) adds `notification.external_delivery_status`/`.external_delivery_error` |
| `frontend/src/components/` | Shared UI: `BuildIndicator.tsx`, `Layout.tsx` (persistent sidebar nav — Leads/Reviews/Benchmark) |
| `frontend/src/pages/` | Route-level pages — each has its own row below: `HomePage.tsx`, `LeadListPage.tsx`/`LeadDetailPage.tsx` (Feature 08), `BenchmarkPage.tsx` (Feature 09), `ReviewQueuePage.tsx`/`ReviewDetailPage.tsx` (Feature 15) |
| `frontend/src/pages/HomePage.tsx` | Index route (`/`) — landing page linking to Observability (`/leads`), Review Queue (`/reviews`), and Benchmark (`/benchmark`); replaced Step 4's bootstrap placeholder per `.claude/refinement-backlog.md`'s RB-004 (COMPLETED) |
| `frontend/src/pages/LeadListPage.tsx` | Feature 08: paginated lead list against `GET /leads`, filterable by status/channel |
| `frontend/src/pages/LeadDetailPage.tsx` | Feature 08: per-lead detail + full stage-trace timeline against `GET /leads/{lead_id}` |
| `frontend/src/lib/` | API client and typed helpers — `api.ts` (fetch wrappers for every backend endpoint: leads/reviews/notifications/benchmark) and `stageOrder.ts` (see below) |
| `frontend/src/lib/api.ts` | Typed `fetch` helpers for every backend endpoint this frontend calls (leads, reviews, notifications, benchmark) |
| `frontend/src/lib/stageOrder.ts` | Feature 08: static TypeScript mirror of the backend's `graph.py` `STAGE_ORDER` (deliberately duplicated — TS can't import a Python constant) — used to render `LeadDetailPage.tsx`'s stage timeline in canonical order |
| `backend/app/benchmark/dataset.py` | Feature 09's `BENCHMARK_DATASET` — 22 labeled `DatasetItem`s (buyer/browser/spam/ambiguous), ships as a Python-literal fixture |
| `backend/app/benchmark/harness.py` | Feature 09's `run_benchmark()` — builds one `ToolRegistry`/`register_default_tools()` per run, invokes `IntentClassificationStage().run()` directly (out-of-graph single-stage invocation, see Key Decisions), computes attempt-level accuracy and item-level consistency |
| `backend/app/models/benchmark.py` | Feature 09's `BenchmarkRun`/`BenchmarkCase` — `BenchmarkCase.attempts_json` is the source of truth per repeat; `predicted_label`/`confidence`/`correct` reflect the first attempt only, the representative prediction the failure table shows |
| `backend/app/schemas/benchmark.py` | Feature 09's `BenchmarkRunSummaryOut` (list, no case detail)/`BenchmarkRunOut` (detail, full `cases`)/`BenchmarkCaseOut` |
| `backend/app/routers/benchmark.py` | Feature 09: `POST /benchmark/run` (synchronous), `GET /benchmark/runs`, `GET /benchmark/runs/{run_id}` |
| `frontend/src/pages/BenchmarkPage.tsx` | Feature 09: "Run Benchmark" trigger, accuracy/consistency/model stat tiles, ambiguous-or-misclassified case table |
| `frontend/src/pages/ReviewQueuePage.tsx` | Feature 15 (CD round, addendum): PENDING review-queue list, reading `GET /reviews` |
| `frontend/src/pages/ReviewDetailPage.tsx` | Feature 15: per-item detail + approve/reject/edit action form against `GET /reviews/{run_id}`/`POST /reviews/{run_id}/action`; surfaces the backend's 409 "already actioned" response as a distinct message, not a generic error |

*(Fill in further as each remaining feature's own Step 6 group lands — don't pre-guess a structure
that doesn't exist yet.)*

---

## Development Workflow

- **Run locally (backend):** `cd backend && .venv\Scripts\Activate.ps1 && uvicorn main:app --reload` (port 8000)
- **Run locally (frontend):** `cd frontend && npm run dev` (port 5173)
- **Test (backend):** `cd backend && pytest`
- **Test (frontend):** `cd frontend && npm test`
- **Build (frontend):** `cd frontend && npm run build`
- **Lint (frontend):** `cd frontend && npm run lint`
- **DB migrations:** `cd backend && alembic revision --autogenerate -m "..."` then `alembic upgrade head`
- **Local LLM:** `ollama serve` (background), model pulled per `.env`'s `OLLAMA_MODEL`
- **Deploy / publish:** not yet applicable — see Step 14-16 for portfolio documentation/publish steps

---

## Key Decisions

- **HubSpot integration via direct `httpx` calls, not the official `hubspot-api-client` SDK** — this
  developer's proven pattern is tested FastAPI backends making live third-party API calls directly
  (per `project-definition.md`'s Value Proposition); the official SDK is a heavier dependency for no
  added portfolio-signal value. Auth: Private App access token (Bearer), set via
  `HUBSPOT_ACCESS_TOKEN` — see `backend/.env.example`.
- **Local-first LLM via Ollama, hosted-API fallback is conditional, not default** — `OLLAMA_MODEL`
  defaults to `llama3.2:3b`, chosen for reasonable local tool-calling capability without a large
  download. If Tier 2's Classification Accuracy Benchmark (Feature 09) shows this model is
  insufficiently reliable, only then wire the optional `FALLBACK_LLM_API_KEY` path — do not add it
  preemptively.
- **SQLite for local dev, PostgreSQL DSN swap-in for later** — `DATABASE_URL` defaults to
  `sqlite:///./leads.db`; matches this developer's existing pattern (see sibling project
  `sales-crm-lead-management`) and keeps the stack free-by-default per `project-definition.md`'s
  Constraints.
- **Orchestration library: LangGraph** — a genuine state-machine graph (not a single prompt) is the
  architectural foundation the project's Critical risk depends on; LangGraph gives per-node
  tool-scoping primitives directly, per `roadmap.md` Feature 01's Key Components.
- **Bootstrap (Step 4) intentionally ships no pipeline-stage logic** — only a health-check route, DB
  session wiring, and an empty `app/orchestrator/` package. Feature implementation (all 14
  `implementation_plan.md` features) is Step 6's job, per `prompts/04`'s own "What This Stage Does
  NOT" boundary.
- **Every pipeline stage implements the Stage contract (`app/orchestrator/contracts.py`) and receives
  tools only through `app/orchestrator/tool_scope.py`'s scoped proxy** — a stage module must never
  import or call another stage's tool binding directly. This is what makes the per-stage tool/state
  boundary architecturally real under code inspection, not cosmetic — the project's Critical risk.
  Set by Feature 01's implementation plan (`architecture-plan-feature-01.md`).
- **Stage execution/transition data persists via `PipelineRun`/`StageTrace`
  (`app/models/pipeline_run.py`)** — any future stage's execution record belongs there, not a bespoke
  per-feature log table. Set by Feature 01's implementation plan (`architecture-plan-feature-01.md`).
- **Each pipeline stage's real (non-stub) implementation lives in its own module under
  `app/orchestrator/stages/`, one file per stage, implementing the `Stage` contract.** Feature 01
  intentionally shipped no stage logic (only stubs inside `graph.py` itself); this fixes where real
  per-stage business logic belongs before Features 03-07 each face the same question independently.
  Set by Feature 02's implementation plan (`architecture-plan-feature-02.md`).
- **A stage may declare `input_slice` (`Stage`'s `ClassVar[str | None]`, default `None`) when it reads
  a different `LeadPipelineState` slice than the one it writes; `app/orchestrator/graph.py`'s
  `_make_node` resolves actual input via `Stage.effective_input_slice` (`input_slice or state_slice`),
  never `state_slice` directly.** A stage whose `input_schema` equals its `output_schema` and which
  leaves `input_slice` unset (e.g. `IntakeStage`) is the special case where both are equal: it receives
  not-yet-normalized data in the same slice fields it will overwrite — whoever constructs the initial
  `LeadPipelineState` seeds those fields with raw/unprocessed data, and the stage transforms them in
  place. This is how raw external input (e.g. a raw email's text) enters the graph without a separate
  pre-parsing layer duplicating the stage's own logic, and how a later stage (e.g. Feature 03's
  `IntentClassificationStage`, which reads `intake` but writes `classification`) can read a different
  slice than it owns without a wildcard/multi-slice mechanism. Set by Feature 02's implementation plan
  (`architecture-plan-feature-02.md`); generalized by Feature 03's (`architecture-plan-feature-03.md`).
- **A stage's own external-system failure is encoded as data in its output slice, never raised, when
  the owning feature's spec wants the pipeline to continue past it (e.g. route to Human Review, or
  proceed as a no-op) — regardless of whether the spec anticipates the failure. A stage raises from
  `run()`, letting `_make_node`'s existing exception handler set `RunStatus.FAILED`/END, when the
  owning feature's spec wants this lead's run to halt at this stage instead — this includes
  spec-anticipated, intentionally-terminal failures (e.g. a write failing after retries are exhausted,
  or an invalid/expired auth token), not only genuinely unexpected bugs.** Set by Feature 03's
  implementation plan (`architecture-plan-feature-03.md`); broadened by Feature 04's
  (`architecture-plan-feature-04.md`) to reflect a second real instance (a lookup timeout) of the
  continue-past-it case. **Reworded by Feature 05's implementation plan
  (`architecture-plan-feature-05.md`)** after its own spec exposed a real contradiction in the prior
  wording ("never a failure mode a feature's own spec already anticipates" literally forbade Feature
  05's own required behavior — a spec-anticipated write failure that must halt the run). The
  distinguishing test was never "does the spec anticipate this failure" — every recoverable failure
  above was also spec-anticipated — it's "does the spec want the run to continue past it or halt for
  this lead." This supersedes the prior wording; it is not a second rule standing beside it.
- **Real tool bindings for external systems (LLM calls, lookups, CRM writes) are registered into
  `ToolRegistry` via one dedicated module per external system under `app/orchestrator/tools/`, wired
  together by a single `register_default_tools(registry, settings)` factory that
  `build_production_graph()` calls** — the tools-side analogue of the "one file per stage" rule below.
  A stage module still never constructs or imports a tool binding directly; it only ever reaches one
  through its `ScopedToolProxy`. Set by Feature 03's implementation plan
  (`architecture-plan-feature-03.md`).
- **A read-only tool and a write tool for the same external system may share one `tools/<system>.py`
  module but must be registered under distinct tool names and granted to different stages'
  `allowed_tools` — never the same name gating both.** Concretely: `hubspot_search_contact` (Feature
  04, `data_enrichment`) and `hubspot_write` (Feature 05, `hubspot_crm_write` — name fixed in advance by
  `app/tests/test_orchestrator_tool_scope.py`) will share `hubspot_tools.py` as two independently-scoped
  bindings. This is what makes "Enrichment cannot reach CRM write" true under code inspection, the
  read/write-scoping analogue of the one-module-per-external-system rule above for the first external
  system two different stages both touch. Set by Feature 04's implementation plan
  (`architecture-plan-feature-04.md`).
- **A "merged lead record" spanning more than one `LeadPipelineState` slice is a read-time concept, not
  a write-time one — a stage never writes into another stage's owned slice to represent a merge.** A
  downstream consumer needing the full record (CRM Write, Notification, observability) treats the
  owning slice's fields as primary and falls back to another named slice's own fields for whatever the
  owner left null — e.g. Feature 05 reads `IntakeSlice` fields first, falling back to
  `EnrichmentSlice.resolved_fields` for anything `IntakeSlice` left `None`. This doesn't change the
  existing "each stage reads/writes only its own declared slice" boundary (`LeadPipelineState`'s
  docstring) — it's the first explicit statement of how a multi-slice merge happens within that
  boundary, since Feature 04 is the first feature whose spec used "merge into the lead record" language
  spanning two slices it doesn't jointly own. Set by Feature 04's implementation plan
  (`architecture-plan-feature-04.md`).
- **A stage that needs read access to more than one `LeadPipelineState` slice declares `input_slices:
  ClassVar[tuple[str, ...]]` (plural, additive companion to the existing singular `input_slice`), and
  its `input_schema` must be a merge-only Pydantic model whose field names exactly match those slice
  names — `app/orchestrator/graph.py`'s `_make_node` builds it generically:
  `stage.input_schema(**{name: getattr(state, name) for name in stage.input_slices})`.** Write access is
  unaffected — `_make_node` still writes only `{stage.state_slice: output}`. The per-stage *read*
  boundary has never been runtime-enforced the way `allowed_tools` is (`ScopedToolProxy` enforces tool
  access at call time; `input_slice`/`input_slices` has only ever been a declared contract) — this
  extends that declared-read side to a documented multi-slice case, not a new enforcement mechanism.
  `input_slices` defaults to `None`; the original singular `input_slice`/`effective_input_slice`
  mechanism (Feature 02/03) is unchanged and stays in active use by `IntentClassificationStage` and
  `DataEnrichmentStage`. Set by Feature 05's implementation plan (`architecture-plan-feature-05.md`),
  building the mechanism Feature 04's "merged lead record is read-time" Key Decision (above) had already
  anticipated needing.
- **A tool binding's dedupe-before-write mechanism reuses an existing read-only lookup tool as a direct
  in-module function call, never a second registered tool exposed to the writing stage's
  `allowed_tools`.** Concretely: `hubspot_tools.write_contact` calls `search_contact` directly;
  `HubSpotCrmWriteStage.allowed_tools` is `frozenset({"hubspot_write"})` only, never
  `"hubspot_search_contact"`. This is the corollary the existing "distinct tool names, granted to
  different stages' `allowed_tools`" Key Decision (Feature 04, above) implied but didn't spell out: the
  write-side stage gets no search access at all, even though its underlying tool internally needs to
  search for dedupe purposes — reuse happens at the Python function level, not the tool-scoping level,
  so the write-only boundary the project's Critical risk depends on stays real under code inspection.
  Set by Feature 05's implementation plan (`architecture-plan-feature-05.md`).
- **A HubSpot record update addresses the contact by its own dedupe-key *value* via HubSpot's
  `idProperty` upsert query parameter (`PATCH .../contacts/{phone-or-email-value}?idProperty=phone|
  email`), never by looking up the contact's internal HubSpot object id first.** Discovered during
  Feature 05's Step 6 implementation, not anticipated by its architecture plan:
  `hubspot_search_contact` (Feature 04) returns only a matched contact's `properties`, never its
  internal id, and changing that return shape would have broken Feature 04's own existing tests for
  no Feature-05-specific benefit. `idProperty` is a real, documented HubSpot v3 CRM API upsert
  capability — using it means `write_contact`'s dedupe-lookup reuse of `search_contact` (the Key
  Decision above) needed zero changes to `search_contact` itself, a stronger form of "never
  re-implemented" reuse than the plan anticipated. Any future stage needing an existing HubSpot
  record's actual internal id (not just whether a match exists) should follow this same pattern —
  address by a known unique property's value via `idProperty`, not by extending `search_contact`'s
  return shape.
- **A paused pipeline run's resumable state is persisted as one full `LeadPipelineState` JSON snapshot
  on the owning feature's own domain row (e.g. `ReviewQueueItem.state_snapshot`), never reconstructed
  by replaying `StageTrace` rows** — the same snapshot technique `StageTrace` already uses
  (`model_dump_json()`), applied at the run level instead of per-stage, whenever a future feature needs
  to pause and later resume a run. This does not compete with the "execution data persists via
  PipelineRun/StageTrace" Key Decision above — that rule governs the execution log; this rule governs a
  domain-specific task queue's own resume payload, a genuinely different concern. Set by Feature 06's
  implementation plan (`architecture-plan-feature-06.md`).
- **Resuming a paused run re-enters the same orchestrator abstraction — the existing `Stage` contract,
  `ToolRegistry`, and `_make_node` trace-writing — via a second, smaller compiled graph starting at the
  paused stage, rather than a bespoke code path in the API/router layer that calls stage tools
  directly.** The resume graph's nodes are the exact same `Stage` instances as the primary graph, so
  every existing per-stage tool/state boundary guarantee carries over unchanged; a router must never
  call a tool binding or a stage's `run()` directly to "fast-path" a resume. Set by Feature 06's
  implementation plan (`architecture-plan-feature-06.md`).
- **`RunStatus.FAILED` is reserved for a stage raising during execution; a reviewer's explicit rejection
  is `RunStatus.REJECTED` — a distinct, valid terminal outcome, never recorded as `FAILED`.** This is a
  different axis than the existing failure-handling Key Decision above (which governs whether a stage
  raises vs. returns data during stage execution) — a human decision made after a stage has already
  completed is never itself a stage failure. Set by Feature 06's implementation plan
  (`architecture-plan-feature-06.md`).
- **A pipeline run's terminal status is set exactly once, at the point where that outcome becomes
  known** — `RunStatus.FAILED` inside `_make_node`'s exception handler, `RunStatus.AWAITING_REVIEW`
  inside `_make_human_review_node`, `RunStatus.REJECTED` inside `routers/reviews.py`'s reject branch,
  and `RunStatus.COMPLETED` by `run_pipeline`/`resume_pipeline` whenever the graph returns with
  `run.status` still `RUNNING` (the only way `RUNNING` can reach that point is that no other terminal
  path fired). No other code should independently decide a run is "done". This generalizes rather than
  contradicts the FAILED/REJECTED Key Decision above — that rule established the FAILED/REJECTED
  distinction; this one completes the enum by stating where COMPLETED and AWAITING_REVIEW are each
  authoritatively set, since COMPLETED wasn't a problem until Feature 07's outcome-typing needed it
  (nothing in the codebase had ever assigned `RunStatus.COMPLETED` before Feature 07). Set by Feature
  07's implementation plan (`architecture-plan-feature-07.md`).
- **An outcome-notification call site is one of exactly two shapes: (a) the existing generic per-stage
  graph node (`_make_node`), used only for the one transition that already flows through `notify_stage`
  in normal execution (crm_write success); (b) a direct call to `persist_outcome_notification()` at
  each of the other terminal-transition points (stage failure, human-review queueing, reviewer
  rejection) that don't otherwise reach that node.** A future outcome-consuming feature — Feature 10
  (External Notification Delivery) explicitly says it "subscribes to the same outcome events Feature 07
  consumes" — extends `persist_outcome_notification()` and its three direct call sites, not a new
  parallel notification mechanism. Set by Feature 07's implementation plan
  (`architecture-plan-feature-07.md`).
- **Notification `detail_link` values follow a fixed convention: `/leads/{lead_id}` for outcomes tied
  to a lead's CRM/detail record (`auto_processed`, `failed`), `/reviews/{run_id}` for outcomes tied to
  the review queue (`awaiting_review`, `rejected`).** Any future frontend route for these views
  (Feature 08's lead detail page; the existing review queue) must match these exact paths rather than
  the notification layer adapting to whatever route the frontend happens to choose. Set by Feature 07's
  implementation plan (`architecture-plan-feature-07.md`).
- **A `PipelineRun`'s post-persistence display status — used by any read-only view built after a run
  has terminated or paused (e.g. Feature 08's monitoring view) — is computed by its own mapping
  (`COMPLETED`->`auto_processed`, `FAILED`->`failed`, `AWAITING_REVIEW`->`awaiting_review`,
  `REJECTED`->`rejected`, `RUNNING`->`in_progress`), kept separate from Feature 07's
  `_OUTCOME_TYPE_BY_STATUS`.** That map is evaluated only at `notify_stage`/
  `persist_outcome_notification()` call time, before `RunStatus.COMPLETED` is ever assigned, so it has
  no `COMPLETED` entry and treats `RUNNING` as the success case — correct only at that specific call
  point. A post-persistence reader asking "what happened to this run" needs the opposite: `COMPLETED`
  means done-successfully, `RUNNING` means still in progress. These two mappings answer different
  questions at different points in a run's lifecycle and must never be unified into one shared
  function. Set by Feature 08's implementation plan (`architecture-plan-feature-08.md`).
- **`PipelineRun` carries denormalized, read-optimized columns (`source_channel`, `confidence_score`)
  set exactly once, at the same final-commit point in `run_pipeline()` that already persists
  `.status`, purely so a list/query view can filter and sort without parsing `StageTrace.
  output_snapshot` JSON per request.** `StageTrace`'s own snapshots remain the sole authoritative
  record of what each stage actually produced — this does not compete with the existing "execution
  data persists via PipelineRun/StageTrace" Key Decision above, it's a read-path optimization derived
  from data `StageTrace` already owns. Any future feature needing to filter/sort a lead list by a value
  a specific stage produces should add a similarly-scoped denormalized column here, set at the same
  commit point, rather than parsing trace JSON at query time or inventing a second query-optimized
  store. Set by Feature 08's implementation plan (`architecture-plan-feature-08.md`).
- **A harness that needs to invoke a single orchestrator stage in isolation (outside the compiled
  graph) for a non-test purpose builds its own `ToolRegistry`, calls the existing
  `register_default_tools(registry, settings)` factory, and invokes `stage.run(input, registry.
  scoped_proxy(stage.allowed_tools, stage.name))` directly — never reimplementing the stage's decision
  logic, never bypassing `ScopedToolProxy`, and never registering a second, parallel tool binding for
  the same external system.** This is the production-benchmark analogue of the pattern
  `app/tests/test_stage_intent_classification.py` already uses with fake tool functions, now used with
  the real registered tools outside a test for the first time. Any future feature needing to invoke a
  stage standalone (a different benchmark, a manual replay/debug tool) should follow this same
  construction rather than inventing a new one. Set by Feature 09's implementation plan
  (`architecture-plan-feature-09.md`).
- **A `tools/` binding invoked by non-Stage orchestrator plumbing (e.g.
  `persist_outcome_notification()`) is called directly by that plumbing, not through
  `ToolRegistry`/`ScopedToolProxy`** — the scoped-proxy boundary exists specifically to enforce a
  *Stage's* declared `allowed_tools`, which doesn't apply to code that isn't a Stage's own `run()`. This
  is a clarification of the existing "stage module ... only ever reaches [a tool] through its
  `ScopedToolProxy`" rule's scope (Feature 03), not a new exception to it — `persist_outcome_notification`
  already bypassed the scoped-proxy pattern for its direct `Notification` DB write before this rule was
  ever stated explicitly. Set by Feature 10's implementation plan (`architecture-plan-feature-10.md`).
- **A side-channel delivery invoked from `persist_outcome_notification()` (or any future
  outcome-consuming extension) must be internally exception-safe — return a status, never raise — so a
  downstream delivery failure can never affect already-decided pipeline or in-app-notification state.
  Its result is recorded as data on the owning `Notification` row, never a separate log table.** This is
  adjacent to, not a restatement of, the existing "a stage's own external-system failure is encoded as
  data, never raised" Key Decision (Features 03-05) — that rule governs a *Stage's* `run()` deciding
  whether to halt *this lead's run*; this rule governs plumbing invoked strictly *after* a stage has
  already completed, where halting was never an option. Set by Feature 10's implementation plan
  (`architecture-plan-feature-10.md`).
