# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 6: Worker Pool Orchestrator — Group_F06 (Feature 06: Human Review & Approval Gate)
completed this session, per `architecture-plan-feature-06.md`'s 7-step Implementation Order.
`RunStatus.REJECTED` added; `ReviewQueueItem` model + Alembic migration
(`68de6a50cacb_add_review_queue_item_table`) created; real `HumanReviewStage` wired in (pure gate, no
tool access); `_make_human_review_node` persists a `ReviewQueueItem` with a full-state resume
snapshot and moves the run to `AWAITING_REVIEW` on queue; `build_resume_graph()` +
`build_production_resume_graph()` + `resume_pipeline()` added as the actual resume mechanism (a
second, smaller compiled graph — `crm_write_stage → notify_stage` — reusing the same `Stage`
instances/`_make_node`); `routers/reviews.py` added (`GET /reviews`, `GET /reviews/{run_id}`, `POST
/reviews/{run_id}/action` with a concurrency-safe atomic-`UPDATE` claim). One implementation-time gap
not anticipated by the architecture plan: `resume_pipeline` must reset the snapshot's
`AWAITING_REVIEW` status back to `RUNNING` before invoking the resume graph, or a successful resume
would stay stuck at `AWAITING_REVIEW` forever — fixed before any test run; see
`architecture-plan-feature-06.md`'s now-filled-in Actual Footprint and `.claude/validation-results.md`
for the full account. All 91 tests pass (79 pre-existing + 12 new).

**Completed steps:** 1 (Project Advisor), 2 (Roadmap Architect), 3 (Feature Specification Engine), 4
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01, Feature 02, Feature 03, Feature 04,
Feature 05, and Feature 06; re-entered per feature group, see `docs/implementation-planning.md` §16), 6
(Worker Pool Orchestrator — Group_F01, Group_F02, Group_F03, Group_F04, Group_F05, and Group_F06 all
COMPLETED).

**Gates passed:** None yet — Gate 2 (Step 7, implementation verification) and Gate 1 (Step 13,
portfolio score ≥9.0/10) are both ahead. Step 7 has not yet run against any completed feature.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Step 5.5: Implementation Planner — Feature 07 (Outcome Notification Stage), then Step 6:
Worker Pool Orchestrator — Group_F07.** Group_F07 (`dependency_groups: [Group_F01, Group_F06]`) is now
dependency-satisfiable — both are COMPLETED — but its `owned_files` is still `TBD — pending Step 5.5
architecture plan for Feature 07`, so Step 5.5 must run first to produce
`architecture-plan-feature-07.md` and finalize Group_F07's `owned_files`/`FILE_OWNERSHIP_MAP` entries
before Step 6 claims it. This is the last remaining Tier 1 pipeline-stage feature before Feature 08
(Observability View, `dependency_groups: [Group_F01, Group_F07]`) becomes claimable.

**Dependency-satisfied but out of scope this round:** Group_F09 (Feature 09, Classification Accuracy
Benchmark Report) is dependency-satisfiable (`depends_on: [Group_F03]`, completed), but it's a Tier 2
item — Tier 1 (Features 01-08) takes priority per the roadmap's own tiering. Group_F13 (Feature 13) is
also dependency-satisfiable (`depends_on: [Group_F05]`, completed) but is a Tier 3 item, same
lower-priority treatment. Group_F11 (Feature 11) remains BLOCKED (`depends_on: [Group_F08, Group_F06]`
— Group_F08 not yet done). Group_F14 (Feature 14) remains CLAIMABLE-but-deferred as previously noted
(Tier 3, visibility only).

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
