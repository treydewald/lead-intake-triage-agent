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

**Step 6 (re-entry): Worker Pool Orchestrator claims Group_F03** (Feature 03: Intent Classification
Stage) — `architecture-plan-feature-03.md` and `implementation_plan.md`'s `owned_files` are both ready;
Group_F03 is `CLAIMABLE`. Implementation Order from the plan: (1) `contracts.py`'s `input_slice`/
`effective_input_slice` → (2) new `app/orchestrator/tools/` package (`ollama_tools.py` +
`register_default_tools`) → (3) `stages/intent_classification.py` (empty-message short-circuit;
retry-once-then-fail-closed call/validation policy; `{buyer, browser, spam}` label set) → (4)
`graph.py` (`_make_node` reads `effective_input_slice`; real `default_stages()["classification"]`;
`build_production_graph()` populates `ToolRegistry` for the first time). Step 6 must also update
`test_orchestrator_graph.py`'s `default_stages()`-based test to register a fake `"ollama_classify"`
tool so it exercises the real stage's success path, not the old stub-failure path — see the
architecture plan's Implementation Order step 4 and Validation Requirements.

**Dependency-satisfied but out of scope this round:** Group_F14 (Feature 14, Multi-Channel Intake
Expansion) also became CLAIMABLE once Group_F02 completed (`depends_on: [Group_F02]`), but it's a
Tier 3 "FUTURE" item recorded for visibility only per `plan-audit.md`'s Step 3 entry — not part of
this round's approved build order. Do not claim it ahead of Tier 1/Tier 2 features.

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
