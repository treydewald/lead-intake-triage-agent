# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 6: Worker Pool Orchestrator — Group_F07 (Feature 07: Outcome Notification — In-App)
completed this session, per `architecture-plan-feature-07.md`'s 7-step Implementation Order.
`OutcomeNotificationStage` added (pure signaling, no tool access, maps `run.status` to one of
`auto_processed`/`awaiting_review`/`rejected`/`failed`); `Notification` model + Alembic migration
(`5f3cbe979b96_add_notification_table`) created; new `persist_outcome_notification()` helper in
`graph.py` fires the notification stage directly for the three terminal transitions
(failure/awaiting-review/reject) that never reach the graph's own `notify_stage` node — the
crm_write-success path still fires through that existing, unmodified node; `routers/notifications.py`
added (`GET /notifications`). One pre-existing gap surfaced (not introduced) by this feature's own
outcome-typing requirement: `RunStatus.COMPLETED` had zero assignment sites anywhere in the codebase
before this round — fixed via a new `_mark_completed_if_still_running()` applied in
`run_pipeline`/`resume_pipeline`; see `architecture-plan-feature-07.md`'s now-filled-in Actual
Footprint, `.claude/validation-results.md`, and `.claude/intervention-log.md` for the full account.
All 102 backend tests pass (91 pre-existing + 11 new); frontend's 1 test unaffected (Feature 07 is
backend-only).

**Completed steps:** 1 (Project Advisor), 2 (Roadmap Architect), 3 (Feature Specification Engine), 4
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01 through Feature 07; re-entered per
feature group, see `docs/implementation-planning.md` §16), 6 (Worker Pool Orchestrator — Group_F01
through Group_F07 all COMPLETED).

**Gates passed:** None yet — Gate 2 (Step 7, implementation verification) and Gate 1 (Step 13,
portfolio score ≥9.0/10) are both ahead. Step 7 has not yet run against any completed feature.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Step 5.5: Implementation Planner — Feature 08 (Observability / Monitoring View), then Step 6:
Worker Pool Orchestrator — Group_F08.** Group_F08 (`dependency_groups: [Group_F01, Group_F07]`) is now
dependency-satisfiable — both are COMPLETED — but its `owned_files` is still `TBD — pending Step 5.5
architecture plan for Feature 08`, so Step 5.5 must run first to produce
`architecture-plan-feature-08.md` and finalize Group_F08's `owned_files`/`FILE_OWNERSHIP_MAP` entries
before Step 6 claims it. This is the last Tier 1 feature — once it lands, all 8 Tier 1 features are
COMPLETED and the project's success criteria's "all Tier 1 features working end-to-end" condition is
met. Feature 08 has a frontend component (group: FRONTEND) — the first Step 5.5 round with real UI
surface, since Features 02-07 were all backend/pipeline-stage work.

**Dependency-satisfied but out of scope this round:** Group_F09 (Feature 09, Classification Accuracy
Benchmark Report) is dependency-satisfiable (`depends_on: [Group_F03]`, completed), but it's a Tier 2
item — Tier 1 (Features 01-08) takes priority per the roadmap's own tiering. Group_F10 (Feature 10,
External Notification Delivery) is now also dependency-satisfiable (`depends_on: [Group_F07]`,
completed) — its own spec explicitly names `persist_outcome_notification()`'s three direct call sites
as the extension point it will use, per the new Architecture Rule Change this round — but it's still a
Tier 2 item, same lower-priority treatment. Group_F13 (Feature 13) is also dependency-satisfiable
(`depends_on: [Group_F05]`, completed) but is a Tier 3 item. Group_F11 (Feature 11) remains BLOCKED
(`depends_on: [Group_F08, Group_F06]` — Group_F08 not yet done, about to become claimable once Group_F08
lands). Group_F14 (Feature 14) remains CLAIMABLE-but-deferred as previously noted (Tier 3, visibility
only).

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
