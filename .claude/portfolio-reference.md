# Portfolio Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-06 (Continued Development — Feature 16, Failed-Run Retry/Resubmission,
COMPLETED. New `POST /leads/{lead_id}/retry`, generalizing Feature 06's resume-graph pattern to
start from whichever stage failed, reconstructing pre-failure state from `StageTrace.
output_snapshot` rather than a stored full-state snapshot. First feature to actually create a
second `PipelineRun` row for one `lead_id`, which exposed and fixed a latent gap in Feature 08's
`GET /leads/{lead_id}` (`.first()` with no `ORDER BY` — see Key Decisions' amended entry). New
"Retry" action on `LeadDetailPage.tsx`'s failed-state banner. Verified live against the real
backend (placeholder HubSpot token still fails CRM Write as expected, proving the retry mechanism
itself works correctly even though the write can't succeed in this dev environment) plus 147/147
backend and 47/47 frontend tests, no regressions. S-02 (Confidence-Threshold What-If Simulator)
remains queued as the next CD round per `scope-expansion.md`'s tie-break decision. Prior update:
Step 12 — Batch Backlog Processor COMPLETED, Round 5: closed the
project-wide page-height/whitespace gap across all 7 primary desktop pages (pixel-measured 30-57%→
2-3% empty), closed as a side effect the two remaining mobile density exceptions (Benchmark 94px→0px,
Lead Detail 303px→15px). New reusable measurement script `.claude/skills/measure-page-whitespace.py`.
Routes to Step 11, Round 6. See Key Decisions for the page-shell stretch pattern and three CSS pitfalls
found while building it. Prior update: Step 12 — Batch Backlog Processor COMPLETED, Round 4: fixed
`TrendChart.tsx`'s axis-label distortion at its real root cause (non-uniform SVG scaling, not
font-size/contrast — see Key Decisions), added composition content to Home/Review Queue/
`LeadHistoryPage.tsx`, and closed most of a mobile (390×844) overflow regression across 6 pages via a
real mobile card-list for `LeadListPage.tsx`/`ReviewQueuePage.tsx`'s tables plus a `StatCard.tsx` fix —
two pages (`LeadDetailPage.tsx`, `BenchmarkPage.tsx`) kept as documented exceptions, see Key Decisions.
Routes to Step 11, Round 5. Prior update: Step 12, Round 1-3 — Batch Backlog Processor COMPLETED,
portfolio backlog P1-01 through P1-04. Added `ReviewQueueItemOut.message_body` (P1-01, backend) plus a
shared
`frontend/src/components/ui/` kit — `PageHeader`/`Card`/`StatCard`/`States` — and `lucide-react`
iconography applied across all 7 pages (P1-02/P1-03), and real-data stat rows plus two-column layouts
on Home/Lead List/Review Queue/Lead Detail/Review Detail (P1-04). No-scroll constraint re-verified and
holds at all three desktop widths (Lead List's root gap tightened `gap-5`→`gap-4` to stay within it —
see Key Decisions). Architecture Map rows updated for `schemas/review.py`, `routers/reviews.py`,
`frontend/src/components/`. Prior update: Step 8 — Viewport-First Refactor COMPLETED. No-scroll
constraint achieved across all 7 pages × 4 target viewports, one documented exception on
`LeadHistoryPage.tsx` for multi-entry histories — see Key Decisions. Prior update: Step 6 — Feature 11, Per-Lead Audit/History
Trail UI, Group_F11 COMPLETED. New `GET /leads/{lead_id}/history` merges every `PipelineRun` row for a `lead_id` with any
`ACTIONED` `ReviewQueueItem`; new nullable `reviewer_name` column on `ReviewQueueItem`; new
`LeadHistoryPage.tsx`, bidirectionally linked with `LeadDetailPage.tsx`; optional "Your name" input on
`ReviewDetailPage.tsx`. Architecture Map rows updated for `models/review_queue.py`,
`schemas/pipeline.py`, `schemas/review.py`, `routers/reviews.py`, `routers/leads.py`, `alembic/`,
`LeadDetailPage.tsx`, `ReviewDetailPage.tsx`, `lib/api.ts`, plus the new `LeadHistoryPage.tsx` row. No
browser-automation tool was available this session (see `.claude/execution-log.md`'s Feature 11 entry)
— verified instead via real live backend calls against the real local model and a real pending review
item, plus jsdom-rendered component tests. One pre-existing, unrelated test failure found and logged as
`.claude/refinement-backlog.md`'s RB-005 (`App.test.tsx` asserts stale pre-RB-004 placeholder text), not
fixed here (outside Group_F11's `owned_files`). Prior update: Feature 10, External Notification
Delivery, Group_F10 COMPLETED. Extended `persist_outcome_notification()` with a best-effort,
never-raising external webhook delivery gated to `awaiting_review` only; new `webhook_tools.py`, two new
nullable `Notification` columns, one new `notification_webhook_url` setting. Live-verified against the
real local model across all three delivery paths (sent/failed/skipped) — see
`.claude/execution-log.md`/`validation-results.md`'s Feature 10 entries. Prior to that:
`.claude/refinement-backlog.md`'s RB-004 — `HomePage.tsx` rewritten from Step 4's bootstrap placeholder
into a real landing page linking to `/leads`, `/reviews`, and `/benchmark`. Prior to that: RB-003 —
Architecture Map backfilled with the remaining Feature 08 rows [`routers/leads.py`, `LeadListPage.tsx`,
`LeadDetailPage.tsx`, `HomePage.tsx`, `lib/api.ts`, `lib/stageOrder.ts`] and the two previously-uncited
migrations, plus rewording the three stale directory-level placeholder rows to present tense.)

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
| `backend/app/orchestrator/graph.py` | LangGraph `StateGraph` wiring the 6 stages, `run_pipeline()`/`resume_pipeline()` entry points; `persist_outcome_notification()` fires the notification stage directly for the three terminal transitions (failure, awaiting-review, reject) that never reach the graph's own `notify_stage` node; `_mark_completed_if_still_running()` is the sole place `RunStatus.COMPLETED` is assigned; also where Feature 10's external delivery hook lives, gated to `outcome_type == "awaiting_review"` only, calling `webhook_tools.py` directly (bypassing `ToolRegistry`/`ScopedToolProxy` — see Key Decisions); Feature 16 added `build_retry_graph()`/`retry_pipeline()` — continues a FAILED run from the stage that raised, into a new `PipelineRun` row, by replaying earlier stages' `StageTrace.output_snapshot` values rather than a stored full-state snapshot |
| `backend/app/orchestrator/stages/intent_classification.py` | Feature 03's `IntentClassificationStage` — calls `ollama_classify` via the scoped tool proxy, retry-once-then-fail-closed |
| `backend/app/orchestrator/stages/data_enrichment.py` | Feature 04's `DataEnrichmentStage` — calls `hubspot_search_contact` via the scoped tool proxy; exact-key phone/email match or `difflib`-scored fuzzy name match, merges only fields Intake left null, never raises |
| `backend/app/orchestrator/stages/hubspot_crm_write.py` | Feature 05's `HubSpotCrmWriteStage` — write-only (`hubspot_write` alone); reads both `intake` and `enrichment` via `input_slices`; calls `tools.call("hubspot_write", ...)` with no try/except so a write failure halts the run |
| `backend/app/orchestrator/stages/human_review.py` | Feature 06's `HumanReviewStage` — pure gate, no tool access; unconditionally returns `ReviewSlice(queued=True, ...)` (the routing decision was already made by `_route_after_enrich`) |
| `backend/app/orchestrator/stages/outcome_notification.py` | Feature 07's `OutcomeNotificationStage` — pure signaling, no tool access; maps `run.status` to one of `auto_processed`/`awaiting_review`/`rejected`/`failed` and builds `message`/`detail_link` |
| `backend/app/orchestrator/tools/` | Real tool bindings for external systems, one module per system (`ollama_tools.py`, `hubspot_tools.py`, `webhook_tools.py`), wired by `register_default_tools()`; `hubspot_tools.py` holds both `search_contact` (read-only) and `write_contact` (write-only, retry-with-backoff) |
| `backend/app/orchestrator/tools/webhook_tools.py` | Feature 10's `deliver_webhook_notification()` — single-attempt, never-raising POST of a Slack-compatible payload to an operator-configured incoming webhook; NOT registered through `ToolRegistry` (called directly by `persist_outcome_notification()` — see Key Decisions); `error` built from status code/exception type only, never the webhook URL itself |
| `backend/app/models/pipeline_run.py` | `PipelineRun`/`StageTrace` SQLAlchemy models — every stage transition's persisted trace |
| `backend/app/models/review_queue.py` | Feature 06's `ReviewQueueItem` — a reviewer's actionable task for one paused run, carrying its own full-state resume snapshot (`state_snapshot`), distinct from the `PipelineRun`/`StageTrace` execution log; Feature 11 added a nullable `reviewer_name` column (self-reported, no auth model — see Key Decisions) |
| `backend/app/models/notification.py` | Feature 07's `Notification` — a persisted in-app notification per outcome event; `run_id` FK is not unique (a run can produce more than one over its lifetime); no addressee field (no `User`/auth model exists); Feature 10 added two nullable columns, `external_delivery_status`/`external_delivery_error` (`None` = never attempted — every outcome type other than `awaiting_review`) |
| `backend/app/schemas/pipeline.py` | Pydantic request/response schemas for triggering/querying a pipeline run; Feature 11 added `TimelineEntryOut`/`LeadHistoryOut` — one flat entry shape carrying both stage and review-action fields as optional |
| `backend/app/schemas/review.py` | Feature 06's `ReviewActionRequest`/`ReviewQueueItemOut` — reviewer-facing request/response shapes; Feature 11 added `ReviewActionRequest.reviewer_name` (optional); Step 12 (portfolio backlog P1-01) added `ReviewQueueItemOut.message_body` (optional) |
| `backend/app/schemas/notification.py` | Feature 07's `NotificationOut` — response shape for `GET /notifications`; Feature 10 added `external_delivery_status`/`external_delivery_error` (optional, `null` for pre-Feature-10 rows) |
| `backend/app/routers/reviews.py` | Feature 06: `GET /reviews`, `GET /reviews/{run_id}`, `POST /reviews/{run_id}/action` — concurrency-safe claim via an atomic `UPDATE ... WHERE status='PENDING'`; approve/edit re-enter the orchestrator via `resume_pipeline()`, reject sets `RunStatus.REJECTED` directly and also calls `persist_outcome_notification()`; Feature 11's `reviewer_name` is persisted in the same atomic `UPDATE`, no second write; Step 12 added `_to_review_out()`, parsing `message_body` out of `state_snapshot` for both GET endpoints (read-only projection, not a new source of truth — see Key Decisions) |
| `backend/app/routers/notifications.py` | Feature 07: `GET /notifications` (list, newest first) |
| `backend/app/routers/leads.py` | Feature 08: `GET /leads` (list, paginated, denormalized `source_channel`/`confidence_score` for filter/sort), `GET /leads/{lead_id}` (detail — full stage-trace timeline via `STAGE_ORDER`/`_STAGE_LABELS`, mirrored on the frontend by `lib/stageOrder.ts`; ordered `.order_by(created_at.desc()).first()` since Feature 16 — see Key Decisions); Feature 11 added `GET /leads/{lead_id}/history` — merges every `PipelineRun` row for a `lead_id` (never `.first()` — see Key Decisions) with any `ACTIONED` `ReviewQueueItem`, sorted by `created_at`; Feature 16 added `POST /leads/{lead_id}/retry` — retries the lead's most recent `FAILED` run via `retry_pipeline()`, `409` if none exists |
| `backend/alembic/` | DB migrations, wired to `app.database.session.Base` and `settings.database_url`; `245c694fed3d_*` creates `pipeline_run`/`stage_trace`; `68de6a50cacb_*` creates `review_queue_item`; `5f3cbe979b96_*` creates `notification`; `9217c457cc82_*` (Feature 08) adds `pipeline_run.source_channel`/`.confidence_score`; `b86e4d4ef367_*` (Feature 09) creates `benchmark_run`/`benchmark_case`; `a95fad549dbf_*` (Feature 10) adds `notification.external_delivery_status`/`.external_delivery_error`; `327d880cd1b9_*` (Feature 11) adds `review_queue_item.reviewer_name` |
| `frontend/src/components/` | Shared UI: `BuildIndicator.tsx`, `Layout.tsx` (persistent sidebar nav — Leads/Reviews/Benchmark, `lucide-react` icons added Step 12); `ui/` subdirectory (added Step 12, portfolio backlog P1-02/P1-03) — `PageHeader.tsx`, `Card.tsx` (`Card`/`SectionLabel`), `StatCard.tsx`, `States.tsx` (`EmptyState`/`LoadingState`/`ErrorState`), used by every page for a consistent type scale, card depth, and designed empty/loading/error states |
| `frontend/src/pages/` | Route-level pages — each has its own row below: `HomePage.tsx`, `LeadListPage.tsx`/`LeadDetailPage.tsx` (Feature 08), `BenchmarkPage.tsx` (Feature 09), `ReviewQueuePage.tsx`/`ReviewDetailPage.tsx` (Feature 15) |
| `frontend/src/pages/HomePage.tsx` | Index route (`/`) — landing page linking to Observability (`/leads`), Review Queue (`/reviews`), and Benchmark (`/benchmark`); replaced Step 4's bootstrap placeholder per `.claude/refinement-backlog.md`'s RB-004 (COMPLETED) |
| `frontend/src/pages/LeadListPage.tsx` | Feature 08: paginated lead list against `GET /leads`, filterable by status/channel |
| `frontend/src/pages/LeadDetailPage.tsx` | Feature 08: per-lead detail + full stage-trace timeline against `GET /leads/{lead_id}`; Feature 11 added a "View Full History →" link to `LeadHistoryPage.tsx` |
| `frontend/src/pages/LeadHistoryPage.tsx` | Feature 11: merged chronological timeline (stage transitions + human review actions) for a lead against `GET /leads/{lead_id}/history`; links back to `LeadDetailPage.tsx`; no persistent nav entry (reached only via that page's link, same pattern as `ReviewDetailPage.tsx`) |
| `frontend/src/lib/` | API client and typed helpers — `api.ts` (fetch wrappers for every backend endpoint: leads/reviews/notifications/benchmark) and `stageOrder.ts` (see below) |
| `frontend/src/lib/api.ts` | Typed `fetch` helpers for every backend endpoint this frontend calls (leads, reviews, notifications, benchmark); Feature 11 added `getLeadHistory()`/`TimelineEntry`/`LeadHistory` and `reviewer_name` on `ReviewActionRequest` |
| `frontend/src/lib/stageOrder.ts` | Feature 08: static TypeScript mirror of the backend's `graph.py` `STAGE_ORDER` (deliberately duplicated — TS can't import a Python constant) — used to render `LeadDetailPage.tsx`'s stage timeline in canonical order |
| `backend/app/benchmark/dataset.py` | Feature 09's `BENCHMARK_DATASET` — 22 labeled `DatasetItem`s (buyer/browser/spam/ambiguous), ships as a Python-literal fixture |
| `backend/app/benchmark/harness.py` | Feature 09's `run_benchmark()` — builds one `ToolRegistry`/`register_default_tools()` per run, invokes `IntentClassificationStage().run()` directly (out-of-graph single-stage invocation, see Key Decisions), computes attempt-level accuracy and item-level consistency |
| `backend/app/models/benchmark.py` | Feature 09's `BenchmarkRun`/`BenchmarkCase` — `BenchmarkCase.attempts_json` is the source of truth per repeat; `predicted_label`/`confidence`/`correct` reflect the first attempt only, the representative prediction the failure table shows |
| `backend/app/schemas/benchmark.py` | Feature 09's `BenchmarkRunSummaryOut` (list, no case detail)/`BenchmarkRunOut` (detail, full `cases`)/`BenchmarkCaseOut` |
| `backend/app/routers/benchmark.py` | Feature 09: `POST /benchmark/run` (synchronous), `GET /benchmark/runs`, `GET /benchmark/runs/{run_id}` |
| `frontend/src/pages/BenchmarkPage.tsx` | Feature 09: "Run Benchmark" trigger, accuracy/consistency/model stat tiles, ambiguous-or-misclassified case table |
| `frontend/src/pages/ReviewQueuePage.tsx` | Feature 15 (CD round, addendum): PENDING review-queue list, reading `GET /reviews` |
| `frontend/src/pages/ReviewDetailPage.tsx` | Feature 15: per-item detail + approve/reject/edit action form against `GET /reviews/{run_id}`/`POST /reviews/{run_id}/action`; surfaces the backend's 409 "already actioned" response as a distinct message, not a generic error; Feature 11 added an optional "Your name" input sent as `reviewer_name` |

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
- **A per-lead read view that aggregates pipeline execution history must query every `PipelineRun` row
  sharing a `lead_id` (ordered by `created_at`), never assume exactly one.** `PipelineRun.lead_id`
  carries no uniqueness constraint specifically so multi-attempt history stays representable once a
  future feature adds a retry/resubmit path. Set by Feature 11's implementation plan
  (`architecture-plan-feature-11.md`). **Amended by Feature 16 (2026-09-06):** Feature 11's own text
  claimed Feature 08's `GET /leads/{lead_id}` "correctly uses `.first()`" for a *current-state* view
  (as opposed to this rule's *history* view) — that reasoning held only because no code path had ever
  produced a second `PipelineRun` row for one `lead_id` yet. Feature 16 (Failed-Run Retry/Resubmission)
  is that future feature, and its arrival exposed the gap: an unordered `.first()` can return an
  arbitrary row once more than one exists, not necessarily the latest. `get_lead_detail` was corrected
  to `.order_by(PipelineRun.created_at.desc()).first()`. **Generalized rule:** any current-state
  (single-row) read of a table whose key is deliberately non-unique for future-multi-row reasons must
  order and take the latest explicitly — never rely on a query planner's undefined default row order,
  even before a second row is possible in practice. Set by Feature 16's implementation plan
  (`architecture-plan-feature-16.md`).
- **Reviewer identity is captured as an optional, free-text, self-reported `reviewer_name` field on
  `ReviewQueueItem`/`ReviewActionRequest`, populated at action time — this project has no User/auth
  model, and building one is out of scope for what is architecturally a single-operator review
  workflow.** Any future feature needing "who did X" should extend this same field/pattern rather than
  introducing authentication. This generalizes, rather than contradicts, Feature 07's existing note that
  `Notification` has "no addressee field (no User/auth model exists)" — same underlying constraint,
  different original reason. Set by Feature 11's implementation plan (`architecture-plan-feature-11.md`).
- **No-scroll constraint achieved (Step 8, 2026-09-05) — every page fits 1920×1080, 1440×900, 1366×768,
  and the mobile viewport (~390×844) with zero vertical or horizontal scroll for primary content, per
  `docs/ui-design-standards.md` §1.** Verified with a real Playwright script (Chromium is locally
  installed under `frontend/node_modules/.bin` though not a declared `package.json` dependency — see
  Feature 11's session notes) measuring `main`'s `scrollWidth`/`scrollHeight` against its
  `clientWidth`/`clientHeight` across all 7 pages × 4 viewports, against real seeded data (failed,
  awaiting-review, and multi-stage lead states). **One documented exception:**
  `LeadHistoryPage.tsx` (`/leads/{lead_id}/history`) can need minimal scroll for a lead with many
  timeline entries (e.g. a resumed run: 5 stages + a review action + a re-run stage, 7+ rows) — this
  page's whole purpose is a complete, unbounded-length per-lead audit trail (Feature 11's Key Decision
  above: history length is data-driven, not fixed), so a long history genuinely cannot compress into a
  fixed viewport the way a fixable layout choice could. Every other page, and `LeadHistoryPage.tsx`
  itself for a lead with a normal (non-multi-run) history, has zero scroll. **Root-cause fix, not a
  per-page patch:** `Layout.tsx`'s sidebar was fixed-width with no mobile breakpoint, leaving as little
  as 166px for `main` at 390px width and causing horizontal overflow on nearly every page — it now hides
  below `md` in favor of a compact top bar with the same nav links, which is what actually closed most
  of the mobile findings; `LeadDetailPage.tsx`'s per-stage decision JSON (previously always rendered
  inline) is now a collapsed-by-default `<details>` disclosure, which closed the largest desktop
  overflow (up to 596px on a failed/multi-stage lead); `LeadListPage.tsx`'s page size dropped from 20 to
  10 rows to fit a full page without scroll. Steps 9 and 12 must preserve this — see
  `docs/ui-design-standards.md` §1.
- **Review Detail's `message_body` is a read-only projection off `state_snapshot`, not a new column
  (Step 12, portfolio backlog P1-01).** The value already existed since Feature 02
  (`LeadPipelineState.intake.message_body`), persisted as part of `ReviewQueueItem.state_snapshot`'s
  JSON blob for the resume path Feature 06 already needed. Adding a denormalized DB column for a value
  Step 6 already stores would be duplicated state with a sync-drift risk for zero benefit; parsing it
  in `_to_review_out()` (`backend/app/routers/reviews.py`) at read time costs one JSON parse per
  reviewer-facing request, on an endpoint with no realistic volume concern (a human-review queue, not a
  hot path). If a future feature needs to query/filter leads by message content, that's the trigger to
  reconsider — not before.
- **No-scroll constraint held under Step 12's composition changes (portfolio backlog P1-04) by
  tightening spacing, not by removing content.** Lead List's new 3-stat summary row pushed it 11px over
  budget at 1366×768; the fix was `gap-5`→`gap-4` on that page's root flex container, not shrinking the
  stat cards or dropping a table row — re-verified via a Playwright script measuring `main.scrollHeight`
  vs `clientHeight` (not just eyeballing screenshots) across all three desktop widths post-fix, all at
  zero overflow. Future composition additions to Lead List specifically have ~4px less headroom at
  1366×768 than other pages before needing the same treatment again.
- **Two more documented no-scroll exceptions at the mobile viewport (Step 12, Round 4, 2026-09-05),
  same allowance as `LeadHistoryPage.tsx`'s long-history exception above.** A real Playwright
  measurement pass (`main.scrollWidth`/`scrollHeight` vs `clientWidth`/`clientHeight` at 390×844) found
  and closed most of a mobile regression across 6 pages — Home 243px→14px, Lead List 257px→13px, Review
  Queue held at 0px, Review Detail 222px→70px, via a genuine mobile card-list alternative to two tables
  (`LeadListPage.tsx`/`ReviewQueuePage.tsx`) plus a `StatCard.tsx` fix (icon hidden, label untracked at
  10px below `sm:`) that turned out to be the entire cause of a separate small horizontal overflow on
  every page using it — a long label like "AWAITING REVIEW" was overflowing past its own card border at
  a 3-column mobile width, confirmed via a cropped screenshot, not just the numeric measurement.
  **`LeadDetailPage.tsx` (465px→303px) and `BenchmarkPage.tsx` (109px→94px) remain over budget and are
  accepted as exceptions**, not further-compressed: Lead Detail genuinely renders 6 real pipeline-stage
  cards plus 2 summary cards in one mobile column, and Benchmark genuinely renders two real data tables
  plus a trend chart on one page — the same "genuinely data-heavy" reasoning `prompts/
  08_viewport-first-refactor.md`'s Common Failure Modes already allows, not a fixable layout choice.
  **Updated Step 12, Round 5 (2026-09-05):** both figures improved substantially as a side effect of
  that round's unrelated desktop whitespace fix, not a mobile-targeted change — `BenchmarkPage.tsx`'s
  94px closed to 0px (the `min-w-0` fix added to stop its Run History table forcing horizontal overflow
  on desktop also resolved a pre-existing mobile constraint), and `LeadDetailPage.tsx`'s 303px reduced to
  15px (padding/spacing redistribution, not a net height increase). Lead Detail's remaining 15px stays a
  documented exception under the same reasoning, now far smaller.
- **A chart's axis-label legibility defect can survive a fontSize/fill fix untouched if the real cause
  is non-uniform SVG scaling, not text styling (Step 12, Round 4, 2026-09-05).** `TrendChart.tsx`'s
  `<svg preserveAspectRatio="none">` inside a fixed-height, full-width container stretches X and Y by
  different factors to avoid letterboxing — fine for a `<path>` line, but it visibly distorts any
  `<text>` glyph drawn in the same viewBox into an illegible squashed shape, independent of font size or
  color contrast. The general fix: axis/label text that must stay legible inside a `preserveAspectRatio:
  none` SVG should be rendered as an HTML overlay positioned by percentage of the same box, not as SVG
  `<text>` — the grid lines and data paths can keep using the SVG's own coordinate system untouched.
  Caught only because this session re-inspected a cropped/enlarged screenshot after the first (wrong)
  fix instead of trusting the named cause — see `docs/ui-audit-refinement.md`'s general lesson about a
  fix's own before/after check looking clean while the underlying defect persists for an unrelated
  reason.
- **A page's "fill remaining vertical space" strategy (Step 12, Round 5, 2026-09-05) is: give
  `Layout.tsx`'s route wrapper and every page's own root element a real resolved height (`h-full` on a
  plain block wrapper, `flex h-full min-h-0 flex-col` on the page root), then mark that page's own LAST
  content section `flex-1 min-h-0` with `overflow-y-auto`/`overflow-auto` so it grows to fill the
  remainder without ever making `main` itself scroll.** Any future page or panel added to this project
  should follow this exact pattern rather than inventing a new one — three real CSS pitfalls were found
  and fixed while establishing it, all worth avoiding in future work here:
  1. **Don't make the route wrapper a `display: grid` (or `flex`) container just to stretch its single
     child.** A grid/flex item is subject to the "automatic minimum size" rule — its content's intrinsic
     min-width can force the item (and everything below it) wider than its parent, silently reintroducing
     horizontal overflow that a plain block wrapper with `h-full` never has (block boxes don't have
     content-based automatic minimum sizing). This actually happened mid-round: switching the wrapper to
     `grid h-full` pushed Benchmark 268px past the mobile viewport via its Run History table.
  2. **Any flex child that wraps a horizontally-scrollable table needs explicit `min-w-0`.** The
     "automatic minimum size" rule applies within nested flex contexts too (a column flex container's
     items can still be forced wider than intended by a table's `min-w-[...]`) — `LeadListPage.tsx`'s and
     `BenchmarkPage.tsx`'s table wrappers both needed `min-w-0` added at every flex level between the
     table and the page root once those wrappers became `flex-1` containers, even though the equivalent
     plain block markup never needed it.
  3. **`h-fit` on a grid item silently defeats CSS Grid's default stretch-to-row-height behavior.**
     `LeadHistoryPage.tsx`'s right-column "Lead summary" card had `h-fit`, an explicit sizing keyword that
     overrides the implicit `align-items: stretch` every other two-column page (`LeadDetailPage.tsx`,
     `ReviewDetailPage.tsx`) relies on for the same fill-to-bottom effect — removing it (and wrapping the
     left column's timeline list in its own `Card` so the fill reads as a designed panel rather than raw
     page background) was what actually closed that page's gap; the metric alone had briefly looked
     closed already due to a since-fixed measurement-script bug (see below), which is why this was caught
     by a direct screenshot comparison, not the script's number alone.
  Verification for any future page using this pattern: re-run
  `.claude/skills/measure-page-whitespace.py` against fresh desktop screenshots AND look at the
  screenshot directly — a `bg-white` card against this app's `bg-slate-50` page background differs by
  only ~7 RGB values, real but nearly invisible to the eye at normal zoom, so the pixel-scan script can
  correctly report "closed" on a page a quick visual skim might still misjudge either way.
- **`.claude/skills/measure-page-whitespace.py` (Step 11 Round 5, reused Step 12 Round 5) must scan only
  the main-content-area width (x ≥ 240px on a desktop 1920×1080 screenshot), never the full image width.**
  `Layout.tsx`'s left sidebar (`w-60`, 240px) is present at every row regardless of page content, with its
  own `bg-white` differing from the page's `bg-slate-50` — scanning the full width makes every row
  register as "content" via the sidebar alone, which produced a false "0% empty everywhere" reading on
  the very first run of this fix, including on `LeadHistoryPage.tsx`, which was still visibly broken.
  Caught by cross-checking the script's numbers against a direct look at the actual screenshots before
  trusting them — see `portfolio-evaluation.md`'s Round 5 Step 12 batch notes for the full account.
