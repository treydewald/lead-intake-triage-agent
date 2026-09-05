# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04 (Step 6 — Worker Pool Orchestrator, Group_F09, complete)

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 6 (Worker Pool Orchestrator) COMPLETED this session for Group_F09 (Feature 09,
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
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01 through Feature 09; re-entered per
feature group, see `docs/implementation-planning.md` §16), 6 (Worker Pool Orchestrator — Group_F01
through Group_F09 all COMPLETED — all 8 Tier 1 features plus Feature 09 [Tier 2] implemented
end-to-end), 7 (Implementation Verification — Gate 2 — PASSED, against Tier 1 only; Feature 09 not yet
covered by a Gate 2 pass).

**Gates passed:** Gate 2 (Step 7, implementation verification) — PASSED, 2026-09-04. Gate 1 (Step 13,
portfolio score ≥9.0/10, per `docs/premium-ui-standard.md`) is still ahead.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Group_F09 is COMPLETED.** Two paths forward, neither yet decided:
- **Step 5.5 for Group_F10** (Feature 10, External Notification Delivery, `depends_on: [Group_F07]`,
  now COMPLETED) or **Group_F11** (Feature 11, Per-Lead Audit/History Trail UI,
  `depends_on: [Group_F08, Group_F06]`, both now COMPLETED) — both dependency-satisfiable, neither has
  an `architecture-plan-*.md` yet. Group_F13 (Feature 13, Tier 3) is also dependency-satisfiable but
  lower priority; Group_F14 (Feature 14) remains CLAIMABLE-but-deferred (Tier 3, visibility only).
- **A Gate 2 (Step 7) re-pass covering Feature 09** specifically — the last Gate 2 run (this session's
  "Prior to this" entry above) only verified Tier 1; Feature 09 (Tier 2) has its own full validation
  loop already recorded in `.claude/execution-log.md`/`validation-results.md` but has not been through
  a dedicated Implementation Verification gate the way the 8 Tier 1 features were as a batch.

**Also available:** `.claude/refinement-backlog.md`'s RB-002 (dead "Review Queue" nav item, OPEN,
P3) — this session's Step 7 finding. Per its own "Routes to" note, it's a product decision (remove the
dead link vs. build the Review Queue frontend via Scope Expansion/Suggestion) rather than a mechanical
fix, so it wasn't auto-routed anywhere this session. Surface it the next time a Suggestion is being
picked, or at the next Dynamic Next-Action Selection / In-App Cohesion Audit.

RB-001 remains COMPLETED (resolved last session) — no longer outstanding.

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
