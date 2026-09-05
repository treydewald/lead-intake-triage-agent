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

**Updated 2026-09-05 (Step 14, README Generator).** All 16 pipeline steps effectively complete or
in progress: Tier 1 (8 features) and Tier 2 (3 features: Classification Accuracy Benchmark, External
Notification Delivery, Per-Lead Audit Trail UI) all implemented and independently verified — 138/138
backend tests, 18/18 frontend tests, `tsc -b`/`vite build` clean, 0 axe-core accessibility violations.
Step 9.5's dependency scan found 19 known transitive-package vulnerabilities, investigated and logged
Moderate (no exploitable condition present) rather than blind-upgraded — see `qa-report.md`. Step 13
(Portfolio Score Gate) **PASSED** at 9/10 overall (Visual & UI/UX 9, Feature Signaling 9, Professional
Readiness 9, Client Impact 9) after 6 evaluation rounds — the first Gate 1 pass in this pipeline's own
recorded history. Remaining backlog (`portfolio-evaluation.md`) is P3-only: 5 optional 9→9.5 polish
items, none gate-blocking. Steps 14-16 (README, description refinement, publish) are the only work
left before this project reaches its full "Steps 1→16" completion. HubSpot sandbox integration runs
against real API calls in dev; `HUBSPOT_ACCESS_TOKEN` is intentionally left unconfigured in the shared
dev environment by design (documented deviation, `.claude/pipeline-reference.md`), so dev-seeded runs
show an expected `failed`-status skew at the CRM-write stage rather than a defect.

---

## Current Development Priorities

The project has moved from feature-implementation mode into portfolio-completion and maintenance
mode. Ordered by what's actually left:

1. Steps 14-16 — README generation (this step), description refinement, and publish/portfolio
   finalization. No further feature work is gating this.
2. P3 backlog items in `portfolio-evaluation.md` (all optional 9→9.5 polish: a second signature-visual
   typography pass, Lead Detail's remaining 15px mobile exception, plus 3 more) — none block
   publication; candidates for a future low-frequency polish pass, not urgent.
3. The 19 known transitive dependency vulnerabilities logged Moderate in `qa-report.md` — worth a
   periodic re-scan as upstream packages release fixed versions, not an immediate action.
4. Any new client-driven feature requests would enter via `docs/continued-development.md`'s CD-1
   addendum loop, not this list — this section only covers already-known remaining work.

---

## Recommended Schedule

The project is now stable, fully tested, and past its portfolio quality gate — a materially different
risk profile than the "large unfinished scope + subtle correctness constraint" state this section
described at bootstrap. Unattended autonomous execution is now reasonable for a narrow set of
low-risk, easily-verified tasks, but there is no active backlog large or urgent enough to justify a
tight recurring cadence. Recommend:

- **Dependency vulnerability re-scan** (`npm audit`, `pip-audit`) — conditional/event-driven
  (triggered by a new advisory affecting a project dependency, not a fixed timer), since the current
  19 findings were already triaged as non-exploitable in this project's specific configuration and a
  fixed-interval re-scan would mostly just re-confirm the same result.
- **P3 backlog polish batch** — conditional, triggered manually when the developer wants incremental
  9→9.5 polish; not scheduled automatically, since these are optional and low-urgency by the Step 11
  evaluator's own classification.
- **No recurring implementation/bug-fixing job** — there is no known open defect; scheduling one
  would have nothing productive to do and risks manufacturing busywork.

This recommendation should be revisited if: a new feature request arrives (moves the project back
into active development), a dependency advisory becomes actually exploitable, or the P3 backlog grows
enough to justify a batch-processing session.

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
