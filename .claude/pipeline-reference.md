# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 6: Worker Pool Orchestrator — Group_F03 (Feature 03: Intent Classification Stage)
claimed and completed this session. Implemented per `architecture-plan-feature-03.md`'s Implementation
Order: `contracts.py`'s `input_slice`/`effective_input_slice` → new `app/orchestrator/tools/` package
(`ollama_tools.py` + `register_default_tools`) → `stages/intent_classification.py` → `graph.py`
(`_make_node` reads `effective_input_slice`; real `default_stages()["classification"]`;
`build_production_graph()` populates `ToolRegistry` for the first time). 44/44 tests passing (15 new);
grep-verified no direct `ollama` import in the stage module; real end-to-end smoke call against the
local `llama3.2:3b` daemon returned a valid, in-set label. `implementation_plan.md` marked Feature 03
`COMPLETED`, Group_F03 `COMPLETED`.

**Completed steps:** 1 (Project Advisor), 2 (Roadmap Architect), 3 (Feature Specification Engine), 4
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01, Feature 02, and Feature 03;
re-entered per feature group, see `docs/implementation-planning.md` §16), 6 (Worker Pool Orchestrator —
Group_F01, Group_F02, and Group_F03 all COMPLETED).

**Gates passed:** None yet — Gate 2 (Step 7, implementation verification) and Gate 1 (Step 13,
portfolio score ≥9.0/10) are both ahead. Step 7 has not yet run against any completed feature.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Step 5.5 (re-entry): Implementation Planner for Feature 04 (Data Enrichment Stage).** Per
`docs/decision-trees.md`'s top-level routing ("Tier 1 features incomplete → Step 5.5 → Step 6"), Tier 1
still has 5 of 8 features remaining (04-08), so the next step is another Step 5.5/Step 6 round, not
Step 7 — Step 7 (Implementation Verification) only enters once all Tier 1 features are complete.
Group_F04 (`depends_on: [Group_F01, Group_F03]`) is now dependency-satisfied now that Group_F03 is
`COMPLETED`; its `owned_files` are still `TBD` pending this Step 5.5 run, per
`docs/implementation-planning.md` §16.

**Dependency-satisfied but out of scope this round:** Group_F09 (Feature 09, Classification Accuracy
Benchmark Report) also became dependency-satisfiable once Group_F03 completed (`depends_on:
[Group_F03]`), but it's a Tier 2 item — Tier 1 (Features 01-08) takes priority per the roadmap's own
tiering. Group_F14 (Feature 14) remains CLAIMABLE-but-deferred as previously noted (Tier 3, visibility
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
