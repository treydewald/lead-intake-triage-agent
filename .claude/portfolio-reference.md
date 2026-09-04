# Portfolio Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04 (populated by Step 4; keep current — see `docs/claude-directory-spec.md`)

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
| `backend/app/core/config.py` | Pydantic settings (env-driven): DB URL, Ollama config, HubSpot token, confidence threshold |
| `backend/app/database/session.py` | SQLAlchemy engine/session/Base (SQLite dev DB: `backend/leads.db`) |
| `backend/app/models/` | SQLAlchemy ORM models (lead records, stage traces, review queue — populated in Step 6) |
| `backend/app/schemas/` | Pydantic request/response schemas (populated in Step 6) |
| `backend/app/routers/` | FastAPI route modules — `health.py` scaffolded; per-feature routers added in Step 6 |
| `backend/app/orchestrator/contracts.py` | `Stage` ABC contract every pipeline stage implements (input/output schema, `allowed_tools`, `state_slice`) |
| `backend/app/orchestrator/state.py` | `LeadPipelineState` — one Pydantic slice per stage (intake, classification, enrichment, crm_write, review, notification) + run metadata |
| `backend/app/orchestrator/tool_scope.py` | `ToolRegistry`/`ScopedToolProxy` — the enforced per-stage tool-access boundary; a stage only ever reaches a tool through its scoped proxy |
| `backend/app/orchestrator/errors.py` | `OutOfScopeToolError`, `StageExecutionError`, `StateValidationError` |
| `backend/app/orchestrator/graph.py` | LangGraph `StateGraph` wiring the 6 stages (stub bodies for Features 04-07 until each lands), `run_pipeline()` entry point |
| `backend/app/orchestrator/stages/intent_classification.py` | Feature 03's `IntentClassificationStage` — calls `ollama_classify` via the scoped tool proxy, retry-once-then-fail-closed |
| `backend/app/orchestrator/tools/` | Real tool bindings for external systems, one module per system (`ollama_tools.py`), wired by `register_default_tools()` |
| `backend/app/models/pipeline_run.py` | `PipelineRun`/`StageTrace` SQLAlchemy models — every stage transition's persisted trace |
| `backend/app/schemas/pipeline.py` | Pydantic request/response schemas for triggering/querying a pipeline run |
| `backend/alembic/` | DB migrations, wired to `app.database.session.Base` and `settings.database_url`; `245c694fed3d_*` creates `pipeline_run`/`stage_trace` |
| `frontend/src/components/` | Shared UI (`BuildIndicator.tsx`, `Layout.tsx`); feature components added as their own Step 6 groups land |
| `frontend/src/pages/` | Route-level pages (observability view, review queue — added as their own Step 6 groups land) |
| `frontend/src/lib/` | API client and typed helpers (added as their own Step 6 groups land) |

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
- **A stage's own recoverable, per-spec-expected external-system failure (e.g., an LLM call failing
  after one retry, an external lookup timing out, or a returned invalid/out-of-set response) must be
  encoded as data in the stage's own output slice — never raised as a `Stage.run()` exception** — so it
  flows through the graph's existing conditional-confidence routing (`_route_after_enrich`) into Human
  Review instead of short-circuiting the entire run to `RunStatus.FAILED`/END via `_make_node`'s
  exception handler. Raising from `Stage.run()` stays reserved for genuinely unexpected/bug-level
  errors, never a failure mode a feature's own spec already anticipates. Set by Feature 03's
  implementation plan (`architecture-plan-feature-03.md`); the examples were broadened by Feature 04's
  (`architecture-plan-feature-04.md`) to reflect a second real instance (a lookup timeout) of the same
  already-general principle — no semantic change.
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
