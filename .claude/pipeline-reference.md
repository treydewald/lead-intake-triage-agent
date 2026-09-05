# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04 (Step 5.5 — Implementation Planner, Feature 09, complete)

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 5.5 (Implementation Planner) COMPLETED this session for Feature 09 (Classification
Accuracy Benchmark Report, Tier 2) — produced `architecture-plan-feature-09.md`. Planning Depth:
Standard. The harness reuses Feature 03's real `IntentClassificationStage`/`ToolRegistry`/
`register_default_tools()` machinery directly (invoked outside the compiled graph, the same pattern
`test_stage_intent_classification.py` already uses with fake tools, now with the real registered
tool) — no classification logic is reimplemented. One new Architecture Rule Change applied to
`.claude/portfolio-reference.md`'s Key Decisions (out-of-graph single-stage invocation convention).
Designed as a genuine cross-system feature (2 new DB tables, 3 new endpoints, this project's second
real frontend page) reusing Feature 08's router/schema/page conventions throughout — see
`.claude/plan-audit.md`'s new entry for the full Existing Systems Analysis, Implementation Order (10
steps), and the accuracy/consistency metric definitions Step 7 will later validate against.
`implementation_plan.md`'s Group_F09 `owned_files` finalized. **Next: Step 6 claims Group_F09.**

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
through Group_F08 all COMPLETED — all 8 Tier 1 features implemented end-to-end; Group_F09 planned,
not yet claimed), 7 (Implementation Verification — Gate 2 — PASSED, against Tier 1 only).

**Gates passed:** Gate 2 (Step 7, implementation verification) — PASSED, 2026-09-04. Gate 1 (Step 13,
portfolio score ≥9.0/10, per `docs/premium-ui-standard.md`) is still ahead.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Step 6 (Worker Pool Orchestrator) claims Group_F09** (Feature 09, Classification Accuracy Benchmark
Report) — its Step 5.5 plan (`architecture-plan-feature-09.md`) is complete with a 10-step
Implementation Order and finalized `owned_files`. Also dependency-satisfiable, still needing their own
Step 5.5 pass first: Group_F10 (Feature 10, External Notification Delivery, `depends_on: [Group_F07]`),
Group_F11 (Feature 11, Per-Lead Audit/History Trail UI, `depends_on: [Group_F08, Group_F06]`).
Group_F13 (Feature 13, Tier 3) is dependency-satisfiable but lower priority. Group_F14 (Feature 14)
remains CLAIMABLE-but-deferred (Tier 3, visibility only).

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
