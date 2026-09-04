# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 5.5: Implementation Planner — Feature 06 (Human Review & Approval Gate) completed this
session. Produced `architecture-plan-feature-06.md` (Deep tier). Key finding: the feature spec assumes
a pause/resume mechanism ("reuses Feature 01's orchestrator resume mechanism") that does not actually
exist in the codebase — this plan designs one (a second, smaller compiled graph — `crm_write_stage →
notify_stage` — reusing the same `Stage` instances/`_make_node`, entered via a new `resume_pipeline()`)
rather than treating the spec's assumption as already satisfied. Also found that the existing
`_route_after_enrich` edge already fully implements the confidence-based auto/queue routing this
feature's spec asks for — no graph-edge change needed, only the real `human_review` stage body and
what happens after a lead is queued. Three Architecture Rule Changes applied to `.claude/
portfolio-reference.md`'s Key Decisions (resumable-state snapshot ownership, resume re-entering the
orchestrator abstraction rather than a bespoke API code path, and a new `RunStatus.REJECTED` distinct
from `FAILED`). `implementation_plan.md`'s Group_F06 `owned_files` finalized (13 files) and
`FILE_OWNERSHIP_MAP` extended for the new stage/model/schema/router files. `.claude/plan-audit.md` has
the full entry.

**Completed steps:** 1 (Project Advisor), 2 (Roadmap Architect), 3 (Feature Specification Engine), 4
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01, Feature 02, Feature 03, Feature 04,
Feature 05, and Feature 06; re-entered per feature group, see `docs/implementation-planning.md` §16), 6
(Worker Pool Orchestrator — Group_F01, Group_F02, Group_F03, Group_F04, and Group_F05 all COMPLETED).

**Gates passed:** None yet — Gate 2 (Step 7, implementation verification) and Gate 1 (Step 13,
portfolio score ≥9.0/10) are both ahead. Step 7 has not yet run against any completed feature.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Step 6: Worker Pool Orchestrator — Group_F06 (Feature 06: Human Review & Approval Gate).**
`architecture-plan-feature-06.md` now exists with a finalized 7-step Implementation Order and
`owned_files`. Step 6 should claim Group_F06 and follow that order exactly: `state.py`
(`RunStatus.REJECTED`) → `app/models/review_queue.py` (`ReviewQueueItem` + Alembic revision) →
`stages/human_review.py` (`HumanReviewStage`) → `graph.py` (real stage wired in + dedicated
review-node wrapper persisting the queue item and setting `AWAITING_REVIEW`) → `graph.py`
(`build_resume_graph()` + `resume_pipeline()`) → `schemas/review.py` + `routers/reviews.py`
(concurrency-safe claim via conditional `UPDATE`) → `main.py` router registration.

**Dependency-satisfied but out of scope this round:** Group_F09 (Feature 09, Classification Accuracy
Benchmark Report) is dependency-satisfiable (`depends_on: [Group_F03]`, completed), but it's a Tier 2
item — Tier 1 (Features 01-08) takes priority per the roadmap's own tiering. Group_F13 (Feature 13) is
now also dependency-satisfiable (`depends_on: [Group_F05]`, completed) but is a Tier 3 item, same
lower-priority treatment. Group_F14 (Feature 14) remains CLAIMABLE-but-deferred as previously noted
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
