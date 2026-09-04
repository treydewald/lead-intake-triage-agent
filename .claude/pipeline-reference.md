# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 5.5: Implementation Planner — Feature 04 (Data Enrichment Stage) completed this session.
Produced `architecture-plan-feature-04.md`: a read-only HubSpot contact search
(`hubspot_search_contact`) fills missing lead fields (exact-key match on phone/email at confidence
1.0, else a `difflib`-scored fuzzy name match against a `0.85` threshold), reusing Feature 03's
`input_slice`/`ToolRegistry` machinery unchanged. Three Architecture Rule Changes applied to
`.claude/portfolio-reference.md`'s Key Decisions (one wording generalization; two new — the
read/write tool-naming split for a shared external system, and the read-time-only multi-slice merge
convention). `implementation_plan.md`'s Group_F04 `owned_files` finalized from the plan's Implementation
Order. Group_F04 not yet claimed by Step 6.

**Completed steps:** 1 (Project Advisor), 2 (Roadmap Architect), 3 (Feature Specification Engine), 4
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01, Feature 02, Feature 03, and Feature
04; re-entered per feature group, see `docs/implementation-planning.md` §16), 6 (Worker Pool
Orchestrator — Group_F01, Group_F02, and Group_F03 all COMPLETED).

**Gates passed:** None yet — Gate 2 (Step 7, implementation verification) and Gate 1 (Step 13,
portfolio score ≥9.0/10) are both ahead. Step 7 has not yet run against any completed feature.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Step 6: Worker Pool Orchestrator — claim Group_F04 (Feature 04: Data Enrichment Stage).**
`architecture-plan-feature-04.md` and `implementation_plan.md`'s `owned_files` are both ready; per
`docs/decision-trees.md`'s top-level routing ("Tier 1 features incomplete → Step 5.5 → Step 6"), this
round's Step 5.5 is done, so Step 6 executes it directly next.

**Dependency-satisfied but out of scope this round:** Group_F09 (Feature 09, Classification Accuracy
Benchmark Report) is dependency-satisfiable (`depends_on: [Group_F03]`, completed), but it's a Tier 2
item — Tier 1 (Features 01-08) takes priority per the roadmap's own tiering. Group_F14 (Feature 14)
remains CLAIMABLE-but-deferred as previously noted (Tier 3, visibility only). Once Group_F04 completes,
Group_F05 (`depends_on: [Group_F01, Group_F04]`) becomes dependency-satisfied and needs its own Step
5.5 re-entry before its own Step 6 round, per `docs/implementation-planning.md` §16.

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
