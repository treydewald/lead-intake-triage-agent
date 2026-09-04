# Lead Intake Triage Agent

A multi-stage AI agent that ingests inbound sales leads (web form, email, or missed-call callback),
classifies intent, enriches missing data, writes the result into a real CRM (HubSpot's free
developer sandbox), and routes low-confidence cases to a human reviewer instead of acting on them
blindly. Each pipeline stage is a genuinely separate unit — its own scoped tool access, its own
piece of state — not one large prompt relabeled as "agents."

**Status:** Environment bootstrapped (Step 4 of 16). No feature logic implemented yet — see
`implementation_plan.md` and `.claude/pipeline-reference.md` for current pipeline state.

## Stack

- **Backend:** FastAPI, SQLAlchemy, Alembic, LangGraph (pipeline orchestration), SQLite (dev) /
  PostgreSQL (production-capable)
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, React Router
- **AI:** Local open-weight LLM via Ollama (`llama3.2:3b` default), with an optional hosted-API
  fallback only if local reliability proves insufficient
- **CRM integration:** HubSpot free-tier developer sandbox, via direct `httpx` calls

## Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1   # PowerShell; use .venv/Scripts/activate.bat for cmd.exe, source .venv/Scripts/activate for Git Bash
pip install -r requirements.txt
copy .env.example .env       # fill in HUBSPOT_ACCESS_TOKEN once you have a sandbox account
uvicorn main:app --reload
```

Backend runs at http://localhost:8000 (health check: `GET /health`).

### Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend runs at http://localhost:5173.

### Local LLM

Requires [Ollama](https://ollama.com) running locally:

```bash
ollama serve
ollama pull llama3.2:3b
```

### HubSpot Sandbox (manual, one-time)

1. Create a free HubSpot developer account and sandbox at https://developers.hubspot.com/.
2. In the sandbox: Settings → Integrations → Private Apps → create one with `crm.objects.contacts`
   scope.
3. Paste the generated access token into `backend/.env`'s `HUBSPOT_ACCESS_TOKEN`.

## Testing

```bash
cd backend && pytest
cd frontend && npm test
cd frontend && npm run lint
```

## Project Documentation

- `project-definition.md` — what this project is and why (Step 1 output)
- `roadmap.md` — tiered feature roadmap (Step 2 output)
- `implementation_plan.md` — atomic, execution-ready feature specs (Step 3 output)
- `.claude/portfolio-reference.md` — architecture map, key decisions (read this before the code)
- `.claude/pipeline-reference.md` — current pipeline step and state

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
