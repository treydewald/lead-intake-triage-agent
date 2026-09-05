# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04 (RB-001 backlog fix session)

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 6: Worker Pool Orchestrator — Group_F08 (Feature 08, Observability / Monitoring View)
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
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01 through Feature 08; re-entered per
feature group, see `docs/implementation-planning.md` §16), 6 (Worker Pool Orchestrator — Group_F01
through Group_F08 all COMPLETED — all 8 Tier 1 features implemented end-to-end).

**Gates passed:** None yet — Gate 2 (Step 7, implementation verification) and Gate 1 (Step 13,
portfolio score ≥9.0/10) are both ahead. Step 7 has not yet run against any completed feature.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Step 7: Implementation Verification (Gate 2)** — all 8 Tier 1 features are now COMPLETED, and Step 7
has not run against any of them yet. Per the pipeline's standard sequence, this is the natural point to
run it before continuing into Tier 2, checking the full Tier 1 implementation (not just each feature's
own inline test-based validation from its Step 6 round) against its architecture plans and specs.

**Also available, not yet started:** Group_F09 (Feature 09, Classification Accuracy Benchmark Report,
`depends_on: [Group_F03]`, completed) and Group_F10 (Feature 10, External Notification Delivery,
`depends_on: [Group_F07]`, completed) are both dependency-satisfiable Tier 2 items. Group_F11 (Feature
11, Per-Lead Audit/History Trail UI) is now also dependency-satisfiable (`depends_on: [Group_F08,
Group_F06]` — both completed as of this session). Group_F13 (Feature 13, Tier 3) is dependency-
satisfiable but lower priority. Group_F14 (Feature 14) remains CLAIMABLE-but-deferred as previously
noted (Tier 3, visibility only). None of these should be started ahead of Step 7 per the pipeline's
own sequence, absent an explicit Suggestion to the contrary.

**RB-001 resolved this session** (see `.claude/refinement-backlog.md`) — no longer outstanding. Step 7
is the sole next action.

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
