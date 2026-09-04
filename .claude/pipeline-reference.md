# Pipeline Reference — Lead Intake Triage Agent

**Last Updated:** 2026-09-04

How *this project* is using the Upwork Portfolio Project Pipeline. Distinct from
`portfolio-reference.md`, which is about the product — this file is about pipeline state.

---

## Current Step

**Project Mode:** STANDARD (Intent: PORTFOLIO, Lifetime: MEDIUM, Scale: MEDIUM, Optimization
Objective: PORTFOLIO_SIGNAL — see `docs/project-strategy.md`). Steps 10-16 are MANDATORY this cycle.

**Step:** Step 6: Worker Pool Orchestrator — Group_F05 (Feature 05: HubSpot CRM Write Stage) completed
this session, following `architecture-plan-feature-05.md`'s 7-step Implementation Order exactly:
`contracts.py` (`input_slices`) → `state.py` (`CrmWriteSlice` extended + `MergedIntakeEnrichment`) →
`graph.py`'s `_make_node` (generic multi-slice branch) → `hubspot_tools.py` (`write_contact`,
`HubSpotWriteError`) → `tools/__init__.py` (registers `"hubspot_write"`) → `stages/
hubspot_crm_write.py` (new `HubSpotCrmWriteStage`, deliberately no try/except around the tool call) →
`graph.py`'s `default_stages()["crm_write"]` swap. One genuine implementation-time discovery not
anticipated by the architecture plan: `search_contact` (Feature 04) returns only a matched contact's
`properties`, never its internal HubSpot id, which a PATCH-based update needs — resolved via
HubSpot's own `idProperty` upsert query parameter (addressing the record by its dedupe key's own
value) rather than modifying `search_contact` or a second lookup; recorded as a new Key Decision in
`.claude/portfolio-reference.md`. All 79 tests (59 pre-existing + 20 new) passed on the first
`pytest` run — no fix cycle needed. `implementation_plan.md` marks Feature 05 and Group_F05
`COMPLETED`; `.claude/execution-log.md` and `.claude/validation-results.md` have the full entries;
`architecture-plan-feature-05.md`'s Actual Footprint is filled in.

**Completed steps:** 1 (Project Advisor), 2 (Roadmap Architect), 3 (Feature Specification Engine), 4
(Environment Bootstrap), 5.5 (Implementation Planner — Feature 01, Feature 02, Feature 03, Feature 04,
and Feature 05; re-entered per feature group, see `docs/implementation-planning.md` §16), 6 (Worker Pool
Orchestrator — Group_F01, Group_F02, Group_F03, Group_F04, and Group_F05 all COMPLETED).

**Gates passed:** None yet — Gate 2 (Step 7, implementation verification) and Gate 1 (Step 13,
portfolio score ≥9.0/10) are both ahead. Step 7 has not yet run against any completed feature.

**`.claude/` scaffold status:** Current — full-tier scaffold copied from pipeline templates on
2026-09-04. See `PIPELINE-SYNC.md`.

**Scaffold tier decision:** FULL tier. Mode is STANDARD, and `roadmap.md` defines Tier 2 (3
features) and Tier 3 (3 features) beyond Tier 1 — per `docs/claude-directory-spec.md`'s Scaffold
Tier section, STANDARD mode with Tier 2/3 features present falls back to full tier.

---

## Next Step

**Step 5.5: Implementation Planner — Feature 06 (Human Review Gate).** Group_F06's `dependency_groups`
(`Group_F01`, `Group_F03`, `Group_F05`) are all now `COMPLETED`, making it the next Tier 1 feature in
`roadmap.md`'s Execution Order (`... → HubSpot CRM Write → Human Review Gate → Outcome Notification →
Observability View`). `Group_F06.owned_files` in `implementation_plan.md` is still `TBD` — per this
project's established pattern (Features 02-05 each did), Step 5.5 must run first to produce
`architecture-plan-feature-06.md` and finalize `owned_files`/Implementation Order before Step 6 claims
Group_F06. Likely design question for that plan to resolve: how the paused/queued lead re-enters the
graph after a reviewer's decision (approve / reject / edit) — `ReviewSlice` already has
`reviewer_action`/`corrected_intent_label`/`paused_at_stage` fields from Feature 01's bootstrap, but no
stage or edge yet reads or acts on them.

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
