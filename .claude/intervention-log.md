# Intervention Log — [PROJECT_NAME]

Append-only record of every deliberate pipeline-level decision (Scope Expansion, Continual Refinement, UI
Audit & Refinement, In-App Cohesion Audit, Implementation Planning depth, Continued Development,
QA/Repair, Portfolio Evaluation, documentation regeneration) run on this project, and what happened
afterward. Full schema, rationale, and the Intervention Registry vocabulary: `docs/intervention-
tracking.md` — don't restate the rules here, just follow them.

**Read by:** nothing in this pipeline yet, mechanically — this is Phase A evidence recording. A future
iteration's Pipeline Learning System (`meta/PIPELINE_LEARNING_SYSTEM.md`) reads across many projects'
copies of this file once enough of them exist to learn from.
**Written by:** any of the operations named above, immediately after it runs — one row, minimal fields,
copying facts already being decided or already recorded elsewhere (see `docs/intervention-tracking.md`
§5 for exactly what to copy from where).

---

## Log

[Append-only, chronological. Never delete or edit a past entry — outcomes get filled in as a follow-up
edit to that same entry once the round they belong to is scored, not a new entry. Example entry shape
below — replace with real entries as operations run; delete the example once the first real one is
added.]

### 2026-01-01 — scope_expansion
- Trigger: [one line — why this ran]
- Expected effect: [copied from the operation's own registry entry / canonical spec]
- Outcome: [filled in once this round's result is recorded elsewhere — copy it here too]
- Surprise: [optional — only if the outcome clearly diverged from the expected effect]
- Agent: [optional — the execution agent/environment that ran this, e.g. "claude/claude_code"]
