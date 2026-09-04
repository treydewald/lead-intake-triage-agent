# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 6: Worker Pool Orchestrator — Group_F04 (Feature 04: Data Enrichment Stage) completed
this session. Implemented `DataEnrichmentStage` per `architecture-plan-feature-04.md`'s Implementation
Order: `EnrichmentSlice` extended with `attempted_fields`/`match_confidence`/`conflicts`/
`lookup_error`; new `hubspot_tools.search_contact` (read-only, exact phone/email match or fuzzy-name
`CONTAINS_TOKEN` fallback) registered as `"hubspot_search_contact"`; `default_stages()["enrichment"]`
swapped from `_StubStage` to the real stage. Full backend suite: 59/59 passing (15 new tests across
5 files), first run clean. Grep-verified no direct `httpx` import in the stage module. Live HubSpot
sandbox smoke call skipped — `HUBSPOT_ACCESS_TOKEN` still empty in `.env` (standing deviation, see
below). `implementation_plan.md`'s Feature 04 and Group_F04 both marked `COMPLETED`;
`architecture-plan-feature-04.md`'s Actual Footprint filled in (no deviations, no rework).

**Completed steps:** 1 (Project Advisor), 2 (Roadmap Architect), 3 (Feature Specification Engine), 4
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01, Feature 02, Feature 03, and Feature
04; re-entered per feature group, see `docs/implementation-planning.md` §16), 6 (Worker Pool
Orchestrator — Group_F01, Group_F02, Group_F03, and Group_F04 all COMPLETED).

**Gates passed:** None yet — Gate 2 (Step 7, implementation verification) and Gate 1 (Step 13,
portfolio score ≥9.0/10) are both ahead. Step 7 has not yet run against any completed feature.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Step 5.5: Implementation Planner — Feature 05 (HubSpot CRM Write Stage).** Group_F04 is now
`COMPLETED`, so Group_F05 (`depends_on: [Group_F01, Group_F04]`) is dependency-satisfied. Per
`docs/implementation-planning.md` §16, Step 5.5 re-enters for Feature 05 (producing
`architecture-plan-feature-05.md` and finalizing Group_F05's `owned_files`) before its own Step 6
round claims it. Note: Feature 05 is this project's highest-risk external integration (idempotent,
retry-safe HubSpot writes against a real sandbox) and depends on a human provisioning
`HUBSPOT_ACCESS_TOKEN` (see Deviations below) before it can be exercised against the live sandbox —
Step 5.5/Step 6 should not block on that being present at plan/build time, per the existing deviation
note.

**Dependency-satisfied but out of scope this round:** Group_F09 (Feature 09, Classification Accuracy
Benchmark Report) is dependency-satisfiable (`depends_on: [Group_F03]`, completed), but it's a Tier 2
item — Tier 1 (Features 01-08) takes priority per the roadmap's own tiering. Group_F14 (Feature 14)
remains CLAIMABLE-but-deferred as previously noted (Tier 3, visibility only).

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
