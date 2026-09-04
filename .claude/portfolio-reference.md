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
| `backend/app/orchestrator/` | Pipeline stage-coordination layer (LangGraph) — the state-machine backbone for Feature 01; empty scaffold, implemented in Step 6 |
| `backend/alembic/` | DB migrations, wired to `app.database.session.Base` and `settings.database_url` |
| `frontend/src/components/` | Shared UI (`BuildIndicator.tsx`, `Layout.tsx`); feature components added in Step 6 |
| `frontend/src/pages/` | Route-level pages (observability view, review queue — added in Step 6) |
| `frontend/src/lib/` | API client and typed helpers (added in Step 6) |

*(Fill in further as the project's real structure emerges in Step 6 — don't pre-guess a structure
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
