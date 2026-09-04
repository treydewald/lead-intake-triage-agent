# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 4: Environment Bootstrap — complete.

**Completed steps:** 1 (Project Advisor), 2 (Roadmap Architect), 3 (Feature Specification Engine), 4
(Environment Bootstrap).

**Gates passed:** None yet — Gate 2 (Step 7, implementation verification) and Gate 1 (Step 13,
portfolio score ≥9.0/10) are both ahead.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Step 5.5: Implementation Planner** (`prompts/05.5_implementation-planner.md`) — new in v22.0,
runs between Step 5 and Step 6. Analyzes `implementation_plan.md`'s Tier 1 feature specs against
this project's actual bootstrapped architecture (this file + `portfolio-reference.md`'s Architecture
Map) before Step 6 writes any code, producing `architecture-plan-*.md` per feature/group.

Step 5 (Workspace Recovery) does not apply — this is a fresh bootstrap, not a recovery.

After Step 5.5: **Step 6 (Worker Pool Orchestrator)** implements Tier 1 features in the
`roadmap.md` Execution Order Recommendation, starting with Feature 01 (Pipeline Orchestration
Layer).

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
