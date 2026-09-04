# Maximum-ROI Autonomous Development Schedule — Lead Intake Triage Agent

**Full framework:** see the pipeline repo's `docs/scheduling.md` (this project's `.claude/pipeline-reference.md`
or `.claude/portfolio-reference.md` should note the pipeline repo location if a local clone is available;
otherwise this file is self-contained enough to act on without it). **State: Not configured** — no
account-level scheduled job exists for this project yet. Everything below is a recommendation until the
README's "⚙️ Set Up Maximum-ROI Scheduled Development" prompt is run and this file is updated to reflect
what was actually configured.

**Do not copy another project's schedule into this file.** This project's optimal cadence depends on
*its own* development stage, roadmap, backlog, test coverage, and architecture — determined fresh at
Step 4 bootstrap and re-evaluated whenever this section is regenerated (Step 14) or the project's stage
materially changes (initial development → feature implementation → stabilization → testing → polish →
portfolio preparation → maintenance).

---

## Current Project State

Steps 1-4 complete (2026-09-04). Mode: STANDARD. Environment bootstrapped: FastAPI/SQLAlchemy/
Alembic backend and Vite/React/TypeScript/Tailwind frontend both scaffolded, verified running
(health check, build, tests, lint all green), git initialized, GitHub repo created and pushed. No
Tier 1 feature logic exists yet — `implementation_plan.md` has all 14 features specced but none
implemented. Local LLM (`llama3.2:3b` via Ollama) is pulled and ready; HubSpot sandbox account/
Private App token is a manual prerequisite not yet created (see `.claude/pipeline-reference.md`'s
Deviations section).

---

## Current Development Priorities

Ordered per `roadmap.md`'s Execution Order Recommendation (itself already priority-ordered by
dependency and risk):

1. Feature 01 — Pipeline Orchestration Layer (blocking: every other Tier 1 feature depends on it).
2. Feature 02 — Intake Parsing & Normalization Stage.
3. Feature 03 — Intent Classification Stage (needs `llama3.2:3b`, already pulled).
4. Feature 04 — Data Enrichment Stage.
5. Feature 05 — HubSpot CRM Write Stage (highest external-integration risk; needs a manually-created
   sandbox token before it can be exercised against the real API — see Human-Gated Tasks).
6. Feature 06 — Human Review & Approval Gate.
7. Feature 07 — Outcome Notification (In-App).
8. Feature 08 — Observability / Monitoring View.
9. Tier 2 (Features 09-11) — Classification Accuracy Benchmark, External Notification Delivery,
   Per-Lead Audit Trail UI — startable once their Tier 1 dependency is stable.
10. Tests/validation, security/dependency scan (Step 9.5), documentation, polish — after Tier 1 is
    functionally complete, per Steps 7-9 of the pipeline.

---

## Recommended Schedule

No recommended schedule yet. This is a brand-new STANDARD-mode project with all 8 Tier 1 features
unimplemented and a hard architectural constraint (per-stage tool/state boundaries must be
*actually* enforced in code, not cosmetic) that the project definition itself flags as the single
biggest risk to get wrong. That combination — large unfinished scope plus a subtle correctness
constraint threading through every feature — calls for close human-in-the-loop implementation via
Step 6, not autonomous unattended sessions, at least through Tier 1 completion and Step 7's
implementation verification gate. Revisit once Tier 1 is stable and passing Step 7/9: a benchmark
re-run (Feature 09) or a dependency/security re-scan (Step 9.5) are the kind of narrow, low-risk
tasks that could reasonably become a recurring conditional job at that point.

---

## Scheduled Tasks

_(Fill in only tasks whose expected ROI justifies their execution cost — do not enable every category
by default. See `docs/scheduling.md` §3, §6.)_

| Task | Purpose | Interval | Conditions | May modify code | May modify tests | May modify docs | May commit | May PR | Human approval | Est. ROI | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | Not configured |

---

## Conditional Tasks

| Task | Trigger Condition | What Runs | Human approval |
|---|---|---|---|

---

## Human-Gated Tasks

Always includes, at minimum: major architectural changes, ambiguous product requirements, destructive
operations, major dependency changes, irreversible migrations, deployment decisions, substantial scope
changes, conflicting requirements, and any point where the autonomous session has insufficient
information to safely proceed. Do not fabricate a decision to keep a scheduled job running — record the
open question here instead and stop.

---

## Execution Dependencies

[INSERT — which scheduled tasks must serialize against each other or against manual development
sessions on this project, if more than one task is ever scheduled.]

---

## ROI Assessment

Not yet applicable until at least one scheduled task has actually executed.

---

## Scheduling History

_(Append-only — never edit a past entry. One row per execution: date, task, state before, work
completed, files changed, tests run, commits/PRs, blockers, human intervention needed, estimated value,
and whether the interval should change.)_

---

## Evidence for Interval Changes

_(None yet.)_

---

## Next Scheduling Review

**Trigger, not date:** re-evaluate when this project moves to its next development stage (see "Current
Project State" above), when several consecutive scheduled executions produce little value, or when the
account-level prompt is run for the first time and there's real history to react to.
