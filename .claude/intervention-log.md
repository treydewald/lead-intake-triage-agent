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
edit to that same entry once the round they belong to is scored, not a new entry.]

### 2026-09-04 — implementation_planning_deep
- Trigger: Feature 07 (Outcome Notification — In-App) reached Step 5.5 before its Step 6 build; spec
  classified as a Deep-tier plan since it touches shared orchestrator plumbing at multiple call sites,
  not one isolated module.
- Expected effect (Predicted Footprint, `architecture-plan-feature-07.md`): ~10 files across new
  stage/model/schema/router/migration modules plus `graph.py`/`reviews.py`/`state.py`/
  `routers/__init__.py`/`models/__init__.py` modifications.
- Outcome (Actual Footprint, same file): 14 files changed — architecturally identical to the plan; the
  only differences were the test footprint splitting into 2 files instead of 1 predicted line item, and
  5 pre-existing test assertions needing updates because they encoded the pre-fix
  `RunStatus.RUNNING`/no-notification-on-failure behavior (already anticipated by the plan's own Risk
  section). 102/102 backend tests passed on the first full run; no rework cycle needed.
- Surprise: the plan's own Existing Systems Analysis surfaced a genuine pre-existing gap unrelated to
  Feature 07's literal scope — `RunStatus.COMPLETED` had zero assignment sites anywhere in the
  codebase before this round — and fixed it as part of this feature rather than deferring it, since
  Feature 07's own auto-processed/in-progress distinction is what exposed it.
- Agent: claude/claude_code

### 2026-09-04 — implementation_planning_standard
- Trigger: Feature 08 (Observability / Monitoring View) reached Step 5.5 before its Step 6 build; spec
  classified as a Standard-tier plan — cross-system (backend + this project's first real frontend
  surface) but reuses the entire existing persistence layer end-to-end, no new architectural primitive.
- Expected effect (Predicted Footprint, `architecture-plan-feature-08.md`): ~11 files across 1 new
  Alembic migration, 2 new frontend pages, 1 new frontend lib file, and modifications to
  `models/pipeline_run.py`, `orchestrator/graph.py`, `schemas/pipeline.py`, `routers/leads.py`,
  `lib/api.ts`, `App.tsx`, `components/Layout.tsx`.
- Outcome: pending Step 6/7 — not yet built this session.
- Surprise: the plan's own Existing Systems Analysis surfaced a genuine gap unrelated to Feature 08's
  literal scope — no feature anywhere in the 14-feature `implementation_plan.md` roadmap builds a
  frontend for the existing `GET /reviews`/`POST /reviews/{run_id}/action` routes, so a human reviewer
  has no UI to actually action a queued lead. Not fixed this round (out of Feature 08's own spec scope)
  — flagged as a future Scope Expansion/CD candidate instead, and the plan deliberately withholds a
  `/reviews/{run_id}` link from the lead detail view until that destination actually exists.
- Agent: claude/claude_code

### 2026-09-05 — continued_development / implementation_planning_standard
- Trigger: RB-002 (`.claude/refinement-backlog.md`) — Step 7 found the sidebar's "Review Queue" nav
  item pointed at a non-existent route, a defect this same gap was already flagged for back in Feature
  08's own Implementation Planning round (2026-09-04, entry above). No Suggestion queued this session;
  asked the user directly which of RB-002's two named resolution options to take (remove the dead link,
  or build the real page) — user chose to build it. Ran the full Continued Development loop (CD-1
  through CD-4): `roadmap-addendum-2026-09-04.md` (CD-1), Feature 15 spec in `implementation_plan.md`
  (CD-2), `architecture-plan-feature-15.md` (CD-2.5, Standard-tier — new frontend surface, zero backend
  changes, every pattern already established by Features 08/09), Step 6-equivalent implementation
  (CD-3), Step 7-equivalent verification (CD-4).
- Expected effect (Predicted Footprint, `architecture-plan-feature-15.md`): 7 files — 2 new pages + 2
  new test files + 3 modified files (`api.ts`, `App.tsx`, `Layout.tsx`); zero backend files.
- Outcome (Actual Footprint, same file): exactly 7 files changed, architecturally identical to the
  plan. One test-infrastructure fix not anticipated by the plan: cross-test `vi.spyOn` mock leakage in
  `ReviewDetailPage.test.tsx` required an `afterEach(() => vi.restoreAllMocks())` the project's other
  test files hadn't needed yet. 118/118 backend tests (unchanged) + 11/11 frontend tests passed;
  build/lint clean. Live-verified against the real backend (not just mocked tests): approve/reject/edit
  actions, the 409 already-actioned case, and the 404 not-found case, using a temporary
  `CONFIDENCE_THRESHOLD=0.95` env-var override (not `.env`) to reliably route real leads into the queue
  for testing, since the real local model proved consistently overconfident on ambiguous messages.
- Surprise: none architecturally — this round is itself the resolution of a surprise an earlier round
  (Feature 08's Implementation Planning) had already correctly predicted and flagged, closing that loop
  rather than opening a new one.
- Agent: claude/claude_code
