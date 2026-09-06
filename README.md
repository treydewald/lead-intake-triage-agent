# Lead Intake Triage Agent

A multi-stage AI agent that ingests inbound sales leads, classifies and enriches them, writes the
result into a real CRM, and pulls a human into the loop only when the model isn't confident enough
to act alone.

## Overview

Sales teams lose leads two ways: acting on bad data automatically, or drowning a human in every
single inbound message. This project is a working demonstration of the middle path — a pipeline
that handles the confident cases end-to-end and routes only the genuinely ambiguous ones to a
reviewer, with a full audit trail either way.

**End-to-end flow:** a lead arrives via web form, email, or a missed-call callback → **Intake**
normalizes it → **Intent Classification** (a local LLM via Ollama) scores intent and confidence →
**Data Enrichment** looks up the contact in HubSpot and fills in anything Intake left blank →
**HubSpot CRM Write** upserts the contact record → if confidence cleared the configured threshold,
the run completes automatically; if it didn't, the run pauses and lands in a **Human Review** queue,
where an operator approves, edits, or rejects it — from the app itself, or directly from a Slack
message's Approve/Reject buttons — an **Outcome Notification** stage records what happened (in-app,
plus an optional external webhook) and every step is preserved on a per-lead history timeline. A run
that fails partway (e.g. a CRM write error) isn't a dead end — it can be retried from the stage that
failed, without re-running the whole pipeline from scratch.

**Architecture:** each stage above is a real, isolated unit — its own Pydantic input/output schema,
its own slice of a shared `LeadPipelineState`, and its own explicit tool allowlist enforced by a
scoped tool proxy, wired together as a [LangGraph](https://github.com/langchain-ai/langgraph) state
graph. A stage can never reach another stage's tools directly; that boundary is verified by tests,
not just convention (`backend/app/tests/test_orchestrator_tool_scope.py`).

## Key Features

### Core Pipeline
- **Six-stage orchestrated pipeline** (Intake → Intent Classification → Data Enrichment → HubSpot
  CRM Write → Human Review gate → Outcome Notification), each stage a `Stage` contract
  implementation under `backend/app/orchestrator/stages/`, wired by
  `backend/app/orchestrator/graph.py`.
- **Enforced per-stage tool scoping** — a stage only ever reaches an external system through a
  `ScopedToolProxy` built from its own declared `allowed_tools`; there is no code path for one
  stage to call another stage's tool.
- **Resumable runs** — a paused (awaiting-review) run persists its full pipeline state as one JSON
  snapshot and resumes through a second, smaller compiled graph starting at the paused stage, reusing
  the exact same `Stage`/`ToolRegistry` machinery as the primary run.
- **Idempotent CRM writes** — HubSpot upserts address the contact by its own dedupe-key value
  (phone or email) via HubSpot's `idProperty` query parameter, so re-processing a lead never creates
  a duplicate contact.
- **Retryable failed runs** — a run that fails partway (e.g. a CRM write error) resumes from the
  failed stage via a second compiled graph, reusing the same `Stage`/`ToolRegistry` machinery as the
  primary run and Feature 06's own resume pattern, rather than restarting the lead from scratch.

### Backend (FastAPI + SQLAlchemy + LangGraph)
- **Three intake channels** — `POST /leads/webform`, `POST /leads/email`, `POST /leads/callback` —
  each triggers a full pipeline run.
- **Observability API** — `GET /leads` (paginated, filterable by status/channel), `GET
  /leads/{lead_id}` (full per-lead stage-trace timeline), `GET /leads/{lead_id}/history` (merged
  history across every pipeline run and human review action for that lead — never assumes exactly
  one run per lead), `POST /leads/{lead_id}/retry` (retry the most recent failed run).
- **Human review workflow** — `GET /reviews` (pending queue), `GET /reviews/{run_id}` (item detail,
  including the original message content), `POST /reviews/{run_id}/action` (approve/edit/reject),
  with a concurrency-safe atomic claim so two reviewers can't double-action the same item. The same
  action logic is also reachable from `POST /slack/interactions` — a signature-verified Slack
  interactive-component callback letting a reviewer approve/reject directly from Slack.
- **Classification accuracy benchmark** — `POST /benchmark/run` executes the Intent Classification
  stage standalone against a 22-item labeled dataset (`backend/app/benchmark/dataset.py`) and
  computes attempt-level accuracy and item-level consistency across repeats; `GET /benchmark/runs` /
  `GET /benchmark/runs/{run_id}` retrieve past runs; `GET /benchmark/confidence-threshold` exposes the
  live confidence-gate setting so a candidate threshold can be simulated against real benchmark data
  before ever changing the real setting.
- **Aggregate funnel & reviewer throughput** — `GET /analytics/funnel` computes lead counts by
  outcome status and source channel, average time-to-resolution, and per-reviewer throughput,
  entirely from already-persisted `PipelineRun`/`ReviewQueueItem` rows — no new tables, no caching.
- **In-app + external notifications** — every terminal outcome (auto-processed, awaiting review,
  rejected, failed) is recorded via `GET /notifications`; an optional Slack-compatible incoming
  webhook additionally delivers `awaiting_review` outcomes externally (with interactive Approve/Reject
  buttons wired to `POST /slack/interactions`), gated by `NOTIFICATION_WEBHOOK_URL` and never able to
  affect pipeline state (delivery failure is recorded as data on the notification row, never raised).
- **Free-by-default stack** — SQLite for local dev (a Postgres DSN swap-in is a config change, no
  code change), a local open-weight model via Ollama by default, HubSpot's free developer sandbox;
  any paid LLM API is an explicitly opt-in fallback only.

### Frontend (React 19 + TypeScript + Vite + Tailwind v4)
- **Lead observability** — a searchable/filterable/paginated lead list, a per-lead detail view with
  a collapsible full stage-trace timeline and a "Retry" action on any failed run's banner, and a
  dedicated lead history page merging multi-run and review-action events chronologically.
- **Human review console** — a pending-queue view and a per-item detail page showing the original
  message, the model's classification/confidence, and an approve/edit/reject action form (with an
  optional self-reported reviewer name, since this is a single-operator workflow with no auth model).
- **Benchmark dashboard** — trigger a fresh accuracy run, see accuracy/consistency/model stat tiles,
  a trend chart across prior runs, a table of ambiguous or misclassified cases, and a collapsible
  "Threshold Simulator" panel showing how many cases would land on each side of a candidate
  confidence threshold before ever touching the real setting.
- **Funnel & reviewer throughput dashboard** — aggregate stat tiles, a by-source-channel breakdown,
  and a reviewer-throughput table, all computed from data the app already persists.
- **Designed for every state** — a shared UI kit (`frontend/src/components/ui/`) gives every page a
  consistent type scale, card depth, and dedicated empty/loading/error states instead of bare text.
- **Fully responsive, no unintended scroll** — every page fits common desktop viewports
  (1920×1080, 1440×900, 1366×768) and a mobile viewport (~390×844) without scroll, verified with a
  real Playwright measurement script; the one documented exception is a lead's full audit-trail
  history page, which can scroll for a lead with an unusually long history by design.

### Quality & Accessibility
- **171 backend tests / 66 frontend tests**, all passing; `tsc -b` and `vite build` clean.
- **Measured test coverage** — 98% backend statement coverage (`pytest-cov`); 92% frontend statement
  coverage (`@vitest/coverage-v8`), up from 71% before Continual Refinement Round 1: it first found
  `LeadDetailPage.tsx` — the page `portfolio-description.md` names as this project's core
  differentiator — had no dedicated test, then its own deferred backlog item (RB-008) closed the
  remaining named gaps (`lib/api.ts`, `LeadListPage.tsx`, `NotFoundPage.tsx`), RB-009's fetch-pattern
  refactor added 3 more covering the reset-on-navigation branch it introduced, and Continual Refinement
  Round 2's RB-010 closed a further gap on two newer pages' interactive success/failure paths. Held
  steady through four later Continued Development rounds (Features 16-19), including a real inbound
  Slack-signature trust boundary whose cryptographic core is fully unit-tested independent of any
  live external service.
- **0 accessibility violations** (axe-core, all severities) across every primary page.
- **Dependency vulnerability scanning** (`npm audit`, `pip-audit`) run and findings triaged during
  QA — see `qa-report.md`; re-run in each Continual Refinement round (frontend: 0 vulnerabilities;
  backend: 0 vulnerabilities as of the 2026-09-06 dependency-upgrade round, after a dedicated
  compatibility-verification pass carried `langgraph`, `langgraph-checkpoint`, `langchain-core`,
  `starlette`/`fastapi`, `pytest`, and `python-dotenv` across major-version boundaries — full test
  suite and a live end-to-end pipeline run re-confirmed no regressions).

## Setup Instructions

### Prerequisites
- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com) (for local LLM classification)
- A free [HubSpot developer account](https://developers.hubspot.com/) with a sandbox (optional for
  read-only exploration; required for the CRM-write stage to succeed)

### Installation

```bash
git clone <repo-url>
cd lead-intake-triage-agent
```

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1   # PowerShell; .venv/Scripts/activate.bat for cmd.exe, source .venv/Scripts/activate for Git Bash
pip install -r requirements.txt
copy .env.example .env       # fill in HUBSPOT_ACCESS_TOKEN once you have a sandbox account
alembic upgrade head
```

**Frontend:**
```bash
cd frontend
npm install
copy .env.example .env
```

### Configuration

Backend (`backend/.env`, see `backend/.env.example` for the full list):
- `DATABASE_URL` — defaults to `sqlite:///./leads.db`; swap for a PostgreSQL DSN in production
- `OLLAMA_BASE_URL` / `OLLAMA_MODEL` — local LLM endpoint and model (default `llama3.2:3b`)
- `FALLBACK_LLM_API_KEY` — optional hosted-LLM fallback, unset by default
- `HUBSPOT_ACCESS_TOKEN` / `HUBSPOT_BASE_URL` — HubSpot Private App token (Settings → Integrations →
  Private Apps → create one with `crm.objects.contacts` scope)
- `CONFIDENCE_THRESHOLD` — classification confidence below which a run routes to human review
  (default `0.7`)
- `NOTIFICATION_WEBHOOK_URL` — optional Slack-compatible webhook for external `awaiting_review`
  delivery, unset by default
- `SLACK_SIGNING_SECRET` — Slack app signing secret, required for `POST /slack/interactions` to
  accept any request (unset by default — with no secret configured, that endpoint rejects every
  request rather than trusting an unverified payload)
- `CORS_ORIGINS` — allowed frontend origins

Frontend (`frontend/.env`, see `frontend/.env.example`):
- `VITE_API_URL` — backend base URL (default `http://localhost:8000`)

### Running Locally

```bash
# Local LLM (separate terminal)
ollama serve
ollama pull llama3.2:3b

# Backend (from backend/)
uvicorn main:app --reload   # http://localhost:8000, health check: GET /health

# Frontend (from frontend/)
npm run dev                 # http://localhost:5173
```

### Running Tests

```bash
cd backend && pytest
cd frontend && npm test
cd frontend && npm run lint

# Coverage
cd backend && pytest --cov=app --cov-report=term-missing
cd frontend && npm run test:coverage
```

### Building for Production

```bash
cd frontend && npm run build
```

## Project Structure

```
backend/
  main.py                       # FastAPI app entrypoint — CORS, router registration
  app/core/config.py            # Pydantic settings (env-driven)
  app/database/session.py       # SQLAlchemy engine/session
  app/models/                   # ORM models (pipeline_run, review_queue, notification, benchmark)
  app/schemas/                  # Pydantic request/response schemas (incl. analytics)
  app/routers/                  # FastAPI routers (leads, reviews, notifications, benchmark, analytics, slack, health)
  app/orchestrator/
    contracts.py                # Stage ABC every pipeline stage implements
    state.py                    # LeadPipelineState — one slice per stage
    tool_scope.py                # ToolRegistry / ScopedToolProxy — the enforced tool boundary
    graph.py                    # LangGraph StateGraph wiring, run/resume/retry entry points
    review_actions.py           # apply_review_action() — shared by the HTTP and Slack transports
    stages/                     # One module per pipeline stage
    tools/                      # Real external-system bindings (Ollama, HubSpot, webhook)
  app/benchmark/                # Labeled dataset + benchmark harness
  alembic/                      # DB migrations
frontend/
  src/pages/                    # Route-level pages (one per screen)
  src/components/               # Layout, shared UI kit (components/ui/)
  src/lib/                      # Typed API client (api.ts), stage-order mirror (stageOrder.ts)
.claude/
  portfolio-reference.md        # Architecture map and key decisions — read before the code
  pipeline-reference.md         # Development pipeline history and current state
```

## API / Usage

**Intake:**
- `POST /leads/webform`, `POST /leads/email`, `POST /leads/callback` — submit a new lead, triggers a
  full pipeline run

**Observability:**
- `GET /leads` — paginated lead list, filterable by status/source channel
- `GET /leads/{lead_id}` — lead detail with full stage-trace timeline
- `GET /leads/{lead_id}/history` — merged history across all runs and review actions for a lead
- `POST /leads/{lead_id}/retry` — retry the lead's most recent failed run from the stage that failed

**Human Review:**
- `GET /reviews` — pending review queue
- `GET /reviews/{run_id}` — review item detail (includes original message content)
- `POST /reviews/{run_id}/action` — approve, edit, or reject a paused run

**Slack:**
- `POST /slack/interactions` — signature-verified Slack interactive-component callback; routes an
  Approve/Reject button click through the same logic as `POST /reviews/{run_id}/action`

**Benchmark:**
- `POST /benchmark/run` — run the classification-accuracy benchmark against the labeled dataset
- `GET /benchmark/runs` — list past benchmark runs
- `GET /benchmark/runs/{run_id}` — benchmark run detail, including per-case results
- `GET /benchmark/confidence-threshold` — the live confidence-gate setting

**Analytics:**
- `GET /analytics/funnel` — aggregate lead counts by status/channel, average time-to-resolution, and
  per-reviewer throughput

**Notifications:**
- `GET /notifications` — list outcome notifications, newest first

**Health:**
- `GET /health` — service health check

**Frontend routes:** `/` (home), `/leads`, `/leads/:leadId`, `/leads/:leadId/history`, `/reviews`,
`/reviews/:runId`, `/benchmark`, `/analytics`.

## Contributing

- Every new pipeline stage implements the `Stage` contract (`backend/app/orchestrator/contracts.py`)
  and reaches external systems only through its scoped tool proxy — never by importing another
  stage's tool binding directly.
- Every new external-system tool binding lives in its own module under
  `backend/app/orchestrator/tools/`, registered via `register_default_tools()`.
- See `.claude/portfolio-reference.md`'s Key Decisions before changing pipeline state, tool scoping,
  or notification behavior — several non-obvious constraints (read-slice boundaries, terminal-status
  ownership, the mobile no-scroll pattern) are recorded there with the reasoning behind them.
- Run the full backend and frontend test suites, plus `tsc -b && vite build`, before committing.

---

## Autonomous Development Schedule

This project can optionally run on a recurring autonomous-development schedule via Claude's scheduling
capability. This is **opt-in** — the project works identically with or without it. Two prompts below:
one recommends a schedule, the other activates it. Full framework:
`docs/scheduling.md` in the [Upwork Portfolio Project Pipeline](https://github.com/treydewald/Upwork-Portfolio-Project-Pipeline)
repo. Current recommendation and any actually-configured jobs live in this project's own
`meta/SCHEDULE.md` — check it before running either prompt below; don't assume this section's copy is
current if `meta/SCHEDULE.md` has moved on since.

### 🚀 Configure Maximum-ROI Autonomous Project Development

```
You are responsible for determining the optimal recurring development schedule for THIS project.

Maximize useful project progress over time while minimizing redundant executions, wasted tokens,
conflicting agents, unnecessary reviews, and autonomous changes that require immediate human correction.
More executions is not the goal — validated useful progress per execution is.

First inspect this project completely: README.md, the current roadmap/backlog, `.claude/` reference
files if present, architecture docs, test configuration, CI config, recent commits, recent
development/iteration logs, and this project's own `meta/SCHEDULE.md` if it already exists (compare
against it — don't regenerate a fresh recommendation from zero if one already exists and nothing
material has changed).

Determine: this project's current development stage; the highest-value unfinished work; which tasks are
safe to run fully autonomously vs. require human judgment; which must be sequential vs. can run
independently; how frequently each of the following actually deserves a recurring slot, if any —
autonomous implementation, bug fixing, testing, QA/review, backlog grooming, requirements verification,
documentation maintenance, dependency review, security review, performance review, UX review,
architecture review, portfolio-quality review, technical-debt reduction, research. Do not enable every
category — only schedule what its expected ROI justifies.

Prefer conditional/event-driven execution over fixed-frequency timers where the trigger is checkable.
Prioritize, in order: broken/blocking functionality, explicit project requirements, high-value unfinished
roadmap items, tests and validation, user-facing functionality, reliability, security, architecture,
performance, documentation, technical debt, optional polish. Never let a scheduled job spend repeated
executions polishing low-priority items while higher-priority categories still have open work.

Stop and record a decision request — do not fabricate one to keep the job running — when scheduled
execution would encounter: major architectural changes, ambiguous product requirements, destructive
operations, major dependency changes, irreversible migrations, deployment decisions, substantial scope
changes, conflicting requirements, or insufficient information to safely proceed.

Write or update `meta/SCHEDULE.md` at this project's root with your recommendation, following the
section structure already in that file (Current Project State, Current Development Priorities,
Recommended Schedule, Scheduled Tasks, Conditional Tasks, Human-Gated Tasks, Execution Dependencies, ROI
Assessment, Scheduling History, Evidence for Interval Changes, Next Scheduling Review). This prompt only
writes the *recommendation* — it must never create, modify, or claim to configure an actual scheduled
job. Use the separate "Set Up Maximum-ROI Scheduled Development" prompt below for that.

If a Scheduling History section with real prior executions already exists in `meta/SCHEDULE.md`, use it:
increase frequency only where consecutive executions produced clear value without conflicts; decrease,
convert to conditional, or disable a task where consecutive executions produced little value or required
repeated human correction. Never preserve an interval "for the sake of automation" once the evidence
says otherwise.
```

### ⚙️ Set Up Maximum-ROI Scheduled Development

```
You are activating (or reconciling) the scheduled-development configuration for THIS project, using
whatever scheduling/cron capability this Claude session's environment actually provides.

Read this project's `meta/SCHEDULE.md` for the current recommendation. List this account's EXISTING
scheduled jobs first — never assume none exist, never create a duplicate of a job that already matches
the recommendation.

For each recommended task in `meta/SCHEDULE.md`'s "Scheduled Tasks" table:
- If the environment provides a way to create/update/disable scheduled jobs from this session, use it —
  create missing jobs, update jobs whose interval/condition has changed, disable jobs the current
  recommendation no longer justifies. Confirm each operation actually succeeded before recording it.
- If the environment does NOT provide that capability in this session, do not claim a job was created,
  modified, or removed. Instead, output the exact configuration (task, interval, execution time,
  conditions, prerequisites) and state plainly the minimal manual action needed to activate it.

Update `meta/SCHEDULE.md` after this run: mark each task's Status as "Configured" (with its real job
identifier), "Not configured," or "Disabled" — never leave a recommended job looking like an active one.
Record the date and outcome of this activation attempt in the Scheduling History section.

This prompt is safe to re-run at any time — later runs must reconcile against whatever is actually
configured, not blindly recreate everything.
```

---

Generated from codebase analysis.
