# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 5.5: Implementation Planner — Feature 05 (HubSpot CRM Write Stage) completed this
session. Produced `architecture-plan-feature-05.md` (Deep tier). Two genuine architecture gaps
surfaced and resolved before any code was written: (1) this stage needs read access to both `intake`
and `enrichment` slices at once, which the existing singular `input_slice` mechanism couldn't express
— resolved by adding an additive `input_slices` (plural) companion to `Stage`, with `_make_node`
building the merged input generically from a new `MergedIntakeEnrichment` schema; (2) the existing
"recoverable failure, never raise" Key Decision, read literally, contradicted Feature 05's own spec
(a write failure after retries exhausted must halt the run, not continue) — resolved by rewording the
Key Decision to the actual distinguishing test ("does the spec want the run to continue past it or
halt for this lead," not "does the spec anticipate it"). A third rule was added: the new write tool's
dedupe lookup reuses Feature 04's `search_contact` as a direct in-module function call, never a second
registered tool exposed to the write-only stage. All three applied to `.claude/portfolio-reference.md`'s
Key Decisions. `implementation_plan.md`'s `Group_F05.owned_files` finalized (12 files: 2 new, 10
modify) and a `FILE_OWNERSHIP_MAP` entry added for the new stage file, following Group_F04's precedent
of only mapping genuinely new files (shared files stay under their originating group's wildcard).
`.claude/plan-audit.md` has the new checkpoint entry.

**Completed steps:** 1 (Project Advisor), 2 (Roadmap Architect), 3 (Feature Specification Engine), 4
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01, Feature 02, Feature 03, Feature 04,
and Feature 05; re-entered per feature group, see `docs/implementation-planning.md` §16), 6 (Worker Pool
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

**Step 6: Worker Pool Orchestrator — Group_F05 (Feature 05: HubSpot CRM Write Stage).**
`architecture-plan-feature-05.md` now exists with a full Implementation Order (7 steps) and finalized
`owned_files`; Step 6 claims Group_F05 and builds exactly that order: `contracts.py` (`input_slices`) →
`state.py` (`CrmWriteSlice` extended + `MergedIntakeEnrichment`) → `graph.py`'s `_make_node` (generic
multi-slice branch) → `hubspot_tools.py` (`write_contact`, retry-with-backoff, reuses `search_contact`
internally) → `tools/__init__.py` (registers `"hubspot_write"`) → `stages/hubspot_crm_write.py` (new
`HubSpotCrmWriteStage` — deliberately no try/except around the tool call, per the reworded Key
Decision) → `graph.py`'s `default_stages()["crm_write"]` swap. Note: Feature 05 is this project's
highest-risk external integration and depends on a human provisioning `HUBSPOT_ACCESS_TOKEN` (see
Deviations below) before it can be exercised against the live sandbox — Step 6 should not block on
that being present at build time, per the existing deviation note; unit tests use fake tool/client
doubles throughout, same as Features 03/04.

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
