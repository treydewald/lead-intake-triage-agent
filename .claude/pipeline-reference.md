# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-05 (Step 6 — Group_F10 claimed and COMPLETED: Feature 10, External
Notification Delivery)

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**This session (2026-09-05, third session same day):** No Suggestion was given; `.claude/
refinement-backlog.md`'s only OPEN entry (RB-004, a small self-contained HomePage.tsx fix) was
consumed first — resolved via option (b) from its own "Routes to" (rewrite the page's copy into a real
landing page with links, rather than a bare redirect). With the backlog empty, this session then
advanced the actual next foundational step: **Step 6 (Worker Pool Orchestrator) claimed Group_F10 and
built Feature 10 (External Notification Delivery)** against `architecture-plan-feature-10.md`'s 6-step
Implementation Order — see `.claude/execution-log.md`/`validation-results.md`'s Feature 10 entries for
full detail. 128/128 backend tests passing (10 new), `alembic upgrade head` applied cleanly (one
correction from the plan: chained onto the actual current head `b86e4d4ef367`, not the plan's stated
`5f3cbe979b96`, since Feature 09's migration landed after the plan was written). Live-verified against
the real local `llama3.2:3b` model across all three delivery paths (sent, failed, skipped) plus the
outcome-type gate, using a disposable local HTTP receiver — not mocked. No frontend change (Feature 10
has no UI surface). `implementation_plan.md` marks Feature 10 `COMPLETED`, Group_F10 `COMPLETED`.

Prior to this: Backlog consumption — RB-003 COMPLETED (documentation-only Architecture Map backfill
for Features 02-08). No pipeline step advanced that session.

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 6 (Worker Pool Orchestrator) COMPLETED this session for Group_F10 (Feature 10, External
Notification Delivery, Tier 2), built against `architecture-plan-feature-10.md`'s 6-step Implementation
Order. Extends `persist_outcome_notification()` (Feature 07's own Key Decision named this in advance as
the extension point) with a best-effort, never-raising external webhook delivery gated to the
`awaiting_review` outcome only; new `app/orchestrator/tools/webhook_tools.py`, two new nullable
`Notification` columns (`external_delivery_status`/`_error`), one new `notification_webhook_url`
setting (unset by default). `implementation_plan.md` marks Feature 10 `COMPLETED`, Group_F10
`COMPLETED`. 128/128 backend tests passing (10 new), live-verified against the real local
`llama3.2:3b` model across all three delivery paths (sent/failed/skipped) plus the outcome-type gate —
full detail in `.claude/execution-log.md`/`validation-results.md`'s Feature 10 entries.

Prior to this: Continued Development — Round 1, CD-1 through CD-4 COMPLETED (Feature 15,
Review Queue Frontend UI — see `docs/continued-development.md`). Resolves `.claude/refinement-
backlog.md`'s RB-002 (dead "Review Queue" nav link) by building the real frontend against Feature 06's
already-working backend, per the user's explicit choice between RB-002's two named options.
`roadmap-addendum-2026-09-04.md` (CD-1), `implementation_plan.md`'s new Feature 15 entry (CD-2),
`architecture-plan-feature-15.md` (CD-2.5/CD-4). Two new frontend pages
(`ReviewQueuePage.tsx`/`ReviewDetailPage.tsx`), three modified files (`lib/api.ts`, `App.tsx`,
`Layout.tsx`), zero backend changes. 11/11 frontend tests passing (4 new), 118/118 backend tests
unchanged, build/lint clean. Live-verified against the real backend (approve/reject/edit, the 409
already-actioned case, the 404 not-found case) via a temporary `CONFIDENCE_THRESHOLD=0.95` override
(not `.env`) since the real local model proved consistently overconfident on ambiguous test messages.
Confirmed as a side effect that Feature 07's existing `/reviews/{run_id}` notification `detail_link`s
now resolve to a real page for the first time. Full detail: `architecture-plan-feature-15.md`'s Actual
Footprint; `.claude/intervention-log.md`'s 2026-09-05 entry; `.claude/refinement-backlog.md`'s RB-002
(now COMPLETED).

Prior to this: Step 6 (Worker Pool Orchestrator) COMPLETED for Group_F09 (Feature 09,
Classification Accuracy Benchmark Report, Tier 2) — built against `architecture-plan-feature-09.md`'s
10-step Implementation Order. Added `backend/app/benchmark/` (dataset.py + harness.py),
`models/benchmark.py` (`BenchmarkRun`/`BenchmarkCase`, migration `b86e4d4ef367`),
`schemas/benchmark.py`, `routers/benchmark.py` (registered in `main.py`), and this project's third
real frontend page (`BenchmarkPage.tsx`, reachable via a new "Benchmark" nav link). 118/118 backend
tests passing (7 new), 5/5 frontend tests passing (2 new), `npm run build`/`oxlint` clean. **Live
manual verification against the real local `llama3.2:3b` model (not mocked):** dev servers started,
Playwright-driven click-through of `/benchmark` — clicked "Run Benchmark", the real synchronous run
completed 22 dataset items x 3 repeats = 66 real Ollama calls, producing accuracy 87.0%/consistency
90.9%, with all 4 ambiguous items and all 3 misclassified `browser`→`buyer` cases shown correctly and
zero console errors. Mid-implementation discovery worth noting: `IntentClassificationStage.run()`
never raises for expected failure modes — it retries its own tool call once internally and returns a
`classification_failed` sentinel — so the harness's outer exception catch is a defensive fallback, not
the primary failure-detection path (see `.claude/execution-log.md`'s Feature 09 entry). All 6
acceptance criteria verified. Full detail: `.claude/execution-log.md`/`.claude/validation-results.md`'s
Feature 09 entries; `architecture-plan-feature-09.md`'s Actual Footprint section.

Prior to this: Step 5.5 (Implementation Planner) COMPLETED for Feature 09 — produced
`architecture-plan-feature-09.md`. Planning Depth: Standard. Designed the harness to reuse Feature 03's
real `IntentClassificationStage`/`ToolRegistry`/`register_default_tools()` machinery directly (invoked
outside the compiled graph, the same pattern `test_stage_intent_classification.py` already uses with
fake tools, now with the real registered tool) — no classification logic reimplemented. One new
Architecture Rule Change applied to `.claude/portfolio-reference.md`'s Key Decisions (out-of-graph
single-stage invocation convention). Designed as a genuine cross-system feature (2 new DB tables, 3 new
endpoints, a new frontend page) reusing Feature 08's router/schema/page conventions throughout.

Prior to this: Step 7 (Implementation Verification, Gate 2) COMPLETED — **verdict PASS**. All
8 Tier 1 features spot-checked live end-to-end (both servers started, all 3 intake channels exercised,
high/low-confidence routing, approve-resume flow, notifications, observability list/detail/404), full
test suite re-confirmed (111 backend + 3 frontend, unchanged), build/lint clean, no test coverage tool
configured (recorded, not gating), cross-feature interaction review clean, no architectural deviations
found beyond what was already recorded in each `architecture-plan-feature-0{1..8}.md`'s Actual
Footprint section. **One pre-existing, non-gating gap found and logged:** the sidebar's "Review Queue"
nav item (`/review`) has no matching frontend route and renders a blank page — not a Tier 1 acceptance
criterion, backend `/reviews` endpoints all verified working; logged as `.claude/refinement-
backlog.md`'s RB-002 (OPEN). Full detail: `.claude/validation-results.md`'s Step 7 entry. Prior to
this: Step 6 Worker Pool Orchestrator — Group_F08 (Feature 08, Observability / Monitoring View)
COMPLETED this session, built against `architecture-plan-feature-08.md`'s 8-step Implementation
Order. Added `PipelineRun.source_channel`/`.confidence_score` (denormalized, migration
`9217c457cc82`), exported `graph.py`'s `STAGE_ORDER`, new `GET /leads`/`GET /leads/{lead_id}`
endpoints with the post-persistence status mapping, and this project's first real frontend pages
(`LeadListPage.tsx`/`LeadDetailPage.tsx`, reachable via the "Observability" nav link at `/leads`).
111/111 backend tests passing (9 new), 3/3 frontend tests passing (2 new), `npm run build` clean,
manual dev-server + Playwright smoke test against real seeded leads (including a genuine HubSpot-write
failure) confirmed the list view, detail/timeline view, and 404 case all render correctly. **This
completes all 8 Tier 1 features end-to-end** — the project's stated success criteria condition is now
met. Full detail: `.claude/execution-log.md`/`.claude/validation-results.md`'s Feature 08 entries.
**One pre-existing, unrelated flaky test found and logged, not fixed:**
`test_router_notifications.py::test_list_notifications_returns_newest_first` (Feature 07's own test, a
timestamp-ordering race) — outside Group_F08's file ownership; tracked as `.claude/refinement-
backlog.md`'s RB-001. **Gap noted previously, still open:** no feature anywhere in the 14-feature
roadmap builds a frontend for the existing `GET /reviews`/`POST /reviews/{run_id}/action` routes;
Feature 08's lead detail view still does not link to `/reviews/{run_id}` since that destination
renders nothing (see `architecture-plan-feature-08.md`'s Risks). Step 7 (Implementation Verification)
has not yet run against any completed feature, including this one.

**Completed steps:** 1 (Project Advisor), 2 (Roadmap Architect), 3 (Feature Specification Engine), 4
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01 through Feature 10, plus Feature 15's
CD-2.5; re-entered per feature group, see `docs/implementation-planning.md` §16), 6 (Worker Pool
Orchestrator — Group_F01 through Group_F10 all COMPLETED — all 8 Tier 1 features plus Feature 09 and
Feature 10 [Tier 2] implemented end-to-end), 7 (Implementation Verification — Gate 2 — PASSED, against
Tier 1 only; Feature 09/10 not yet covered by a Gate 2 pass), Continued Development Round 1 (CD-1
through CD-4 — Feature 15, Review Queue Frontend UI, COMPLETED and verified).

**Gates passed:** Gate 2 (Step 7, implementation verification) — PASSED, 2026-09-04. Gate 1 (Step 13,
portfolio score ≥9.0/10, per `docs/premium-ui-standard.md`) is still ahead.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Feature 10 (Group_F10) is now COMPLETED** — this session's Step 6 run. `.claude/refinement-
backlog.md` has zero OPEN/IN_PROGRESS entries (RB-001 through RB-004 all COMPLETED).

Paths available next session:
- **Step 5.5 for Group_F11** (Feature 11, Per-Lead Audit/History Trail UI,
  `depends_on: [Group_F08, Group_F06]`, both COMPLETED) — dependency-satisfiable, no
  `architecture-plan-*.md` yet. Group_F13 (Feature 13, Tier 3) is also dependency-satisfiable but lower
  priority; Group_F14 (Feature 14) remains CLAIMABLE-but-deferred (Tier 3, visibility only).
- **A Gate 2 (Step 7) re-pass covering Feature 09 and Feature 10** — the last full Gate 2 run only
  verified Tier 1; both Tier 2 features have their own full validation loops already recorded in
  `.claude/execution-log.md`/`validation-results.md` but have not been through a dedicated
  Implementation Verification gate the way the 8 Tier 1 features were as a batch. Feature 15 has its
  own CD-4 verification recorded in `architecture-plan-feature-15.md` and does not need a separate
  Gate 2 pass.
- With no Suggestion and an empty backlog, the next idle session should run
  `docs/next-action-selection.md`'s Dynamic Next-Action Selection rather than defaulting to Scope
  Expansion — this project has landed several backend/frontend features across recent Step 6 and CD
  rounds with no full In-App Cohesion Audit or UI Audit & Refinement pass since Step 7's Tier-1-only
  Gate 2 run.

Step 5 (Workspace Recovery) does not apply — this is a fresh bootstrap, not a recovery.

---

## Deviations from Standard Pipeline

- **HubSpot sandbox account/Private App token creation is a manual, out-of-band step** — this
  session cannot create a HubSpot developer account or generate a Private App token
  autonomously. `backend/.env.example`'s `HUBSPOT_ACCESS_TOKEN` is a placeholder; a human must
  create the free sandbox account and paste a real token into `backend/.env` before Feature 05
  (HubSpot CRM Write Stage) can be exercised against the live sandbox. Feature 05's own
  implementation and tests should not block on this being present at Step 6 build time.
- **Ollama model pulled during Step 4** — `ollama list` showed no local models at bootstrap start;
  `llama3.2:3b` (the configured default, ~2GB) was pulled in the background during this step and
  confirmed present (`ollama list` shows `llama3.2:3b`, pulled 2026-09-04). Ready for Step 6's
  Feature 03 (Intent Classification Stage) with no further setup needed.
