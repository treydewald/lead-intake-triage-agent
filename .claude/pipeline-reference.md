# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 5.5: Implementation Planner — complete for Feature 02 (Intake Parsing & Normalization
Stage). Produced `architecture-plan-feature-02.md`; two Architecture Rule Changes applied to
`.claude/portfolio-reference.md`'s Key Decisions (per-stage module location under
`app/orchestrator/stages/`, and the input==output-schema raw-data-seeding convention).

**Completed steps:** 1 (Project Advisor), 2 (Roadmap Architect), 3 (Feature Specification Engine), 4
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01 and Feature 02; re-entered per
feature group, see `docs/implementation-planning.md` §16), 6 (Worker Pool Orchestrator — Feature
01/Group_F01 only so far).

**Gates passed:** None yet — Gate 2 (Step 7, implementation verification) and Gate 1 (Step 13,
portfolio score ≥9.0/10) are both ahead.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Step 6 (re-entry): Worker Pool Orchestrator claims Group_F02** (Feature 02 — Intake Parsing &
Normalization Stage). `architecture-plan-feature-02.md` is complete with a 5-step Implementation
Order (`stages/intake.py` → `schemas/pipeline.py` additions → `routers/leads.py` → `graph.py`
stub-swap → `main.py` registration). Step 6 should finalize `implementation_plan.md`'s `owned_files`
for Group_F02 from that Implementation Order (currently `TBD`) before claiming, per
`prompts/06_worker-pool-orchestrator.md`'s grouping rule #4.

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
