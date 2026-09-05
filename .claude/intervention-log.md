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

### 2026-09-05 — implementation_planning_standard
- Trigger: user chose Feature 10 (External Notification Delivery) as this session's next step, from a
  short list of undecided Tier 2 options (`.claude/pipeline-reference.md`'s prior Next Step: Group_F10,
  Group_F11, or a Gate 2 re-pass for Feature 09). Feature 10 reached Step 5.5 before its Step 6 build;
  classified Standard-tier — one new external system (a Slack-compatible webhook) and a small schema
  change, but the extension point (`persist_outcome_notification()`) already exists and was named in
  advance by Feature 07's own Key Decision.
- Expected effect (Predicted Footprint, `architecture-plan-feature-10.md`): 7 files —
  `models/notification.py`, one new Alembic migration, `core/config.py`, `backend/.env.example`, new
  `tools/webhook_tools.py`, `orchestrator/graph.py`, `schemas/notification.py`. Two new Architecture
  Rule Changes applied to `.claude/portfolio-reference.md`'s Key Decisions (non-Stage plumbing may call
  `tools/` bindings directly, bypassing `ScopedToolProxy`; a side-channel delivery invoked from that
  plumbing must be internally exception-safe, never raising).
- Outcome: pending Step 6/7 — not yet built this session; `Group_F10.status` remains `UNCLAIMED`.
- Surprise: none — this is the first Implementation Planning round to explicitly separate
  "Stage-scoped" tool access (`ScopedToolProxy`) from "plumbing-scoped" direct calls, a distinction the
  codebase had already practiced implicitly (via `persist_outcome_notification`'s own direct DB write)
  since Feature 07, but had never stated as its own rule until this feature's spec required a second
  instance of the same pattern.
- Agent: claude/claude_code

### 2026-09-05 — portfolio_evaluation
- Trigger: Step 10 (Screenshot Capture) completed unconditionally per this cycle's mandatory
  Steps 10-16; Step 11 (Portfolio Evaluator) ran next against the 9 captured screenshots plus a direct
  read of the frontend source for empty/loading/error-state and cohesion-link verification (per
  `docs/premium-ui-standard.md`'s hard-gate rule, a claim about a missing state or link is checked
  against the actual component, not inferred from the screenshot alone).
- Expected effect: an anchored 0-10 score per `QUALITY_RUBRIC.md`'s four dimensions plus a prioritized
  P1/P2/P3 backlog, gating routing to either Step 13 (≥9.0, Visual & UI/UX ≥9.0) or Step 12 (below
  gate).
- Outcome: OVERALL SCORE 5/10 (Visual & UI/UX 5, Feature Signaling 5, Professional Readiness 5, Client
  Impact 5) — below the 9.0 gate on every dimension, so this routes to Step 12 (Batch Backlog
  Processor), then loops back to Step 11 to re-evaluate. `portfolio-evaluation.md` (project root)
  records 4 P1, 4 P2, and 3 P3 items. `.claude/project-metrics.md`'s `PROJECT_COMPLETED` entry appended
  with matching numbers.
- Surprise: a real functional gap, not just a polish item — Review Detail (the one screen where a
  human makes a judgment call) shows neither the lead's message content nor a link to that lead's full
  Detail/History view, even though the API response it already receives (`ReviewQueueItemOut`) carries
  `lead_id` needed for that link at zero backend cost. Logged as P1-01, the top-priority item.
- Agent: claude/claude_code

### 2026-09-05 — portfolio_evaluation (Round 2)
- Trigger: Step 12 (Batch Backlog Processor) completed all 4 Round 1 P1 items and re-captured
  screenshots; Step 11 re-ran unconditionally per `prompts/12_batch-backlog-processor.md`'s own Next
  Steps section to re-score against the current state rather than assume the batch's effect.
- Expected effect: an anchored 0-10 re-score per `QUALITY_RUBRIC.md`'s four dimensions, gating routing
  to either Step 13 (≥9.0, Visual & UI/UX ≥9.0) or another Step 12 batch.
- Outcome: OVERALL SCORE 6/10 (Visual & UI/UX 6, Feature Signaling 7, Professional Readiness 8, Client
  Impact 6) — up from 5/10, still below the 9.0 gate, routes to another Step 12 batch. New backlog: 3
  P1 (native-control restyling, composition fill, depth/interaction feedback), 2 P2 (Benchmark trend
  viz, motion), 3 P3 (carried forward unchanged). `.claude/project-metrics.md`'s `PROJECT_COMPLETED`
  entry appended with matching numbers.
- Surprise: the composition fix (Round 1's P1-04) only partially resolved the dead-space weakness it
  targeted — filling the top of each page with stat rows/two-column layouts left most pages' lower
  50-75% still empty, so the same underlying weakness persists in reduced form rather than being fully
  closed by what looked like a direct fix.
- Agent: claude/claude_code

### 2026-09-05 — portfolio_evaluation (Round 3)
- Trigger: Step 12 (Batch Backlog Processor) completed all 3 Round 2 P1 items and re-captured
  screenshots; Step 11 re-ran unconditionally per `prompts/12_batch-backlog-processor.md`'s own Next
  Steps section to re-score against the current state rather than assume the batch's effect.
- Expected effect: an anchored 0-10 re-score per `QUALITY_RUBRIC.md`'s four dimensions, gating routing
  to either Step 13 (≥9.0, Visual & UI/UX ≥9.0) or another Step 12 batch.
- Outcome: OVERALL SCORE 7/10 (Visual & UI/UX 8, Feature Signaling 7, Professional Readiness 8, Client
  Impact 7) — up from 6/10, still below the 9.0 gate, routes to another Step 12 batch. New backlog: 4
  P1 (Benchmark trend visualization, Review Detail composition fix, motion/microinteraction layer,
  signature visual characteristic), 1 P2 (Lead Detail remaining dead space), 3 P3 (carried forward
  unchanged). `.claude/project-metrics.md`'s `PROJECT_COMPLETED` entry appended with matching numbers.
- Surprise: closing the native-control weakness (Round 2's P1-01) made the *other* still-open
  weakness — Review Detail's composition gap — visually more conspicuous rather than less, the same
  pattern Round 2 itself observed about native controls becoming more jarring as everything around
  them improved. Fixing one weakness in isolation appears to reliably raise the salience of whichever
  weakness is fixed last, not just leave it unchanged — worth anticipating in future rounds' batch
  ordering rather than treating each P1 item as independent.
- Agent: claude/claude_code

### 2026-09-05 — portfolio_evaluation (Round 4)
- Trigger: Step 12 (Batch Backlog Processor) completed all 4 Round 3 P1 items (Benchmark trend
  visualization, Review Detail composition fix, motion layer, signature visual) and re-captured
  screenshots; Step 11 re-ran unconditionally per `prompts/12_batch-backlog-processor.md`'s own Next
  Steps section to re-score against the current state.
- Expected effect: an anchored 0-10 re-score per `QUALITY_RUBRIC.md`'s four dimensions, gating routing
  to either Step 13 (≥9.0, Visual & UI/UX ≥9.0) or another Step 12 batch.
- Outcome: OVERALL SCORE 7/10 (Visual & UI/UX 8, Feature Signaling 8, Professional Readiness 8, Client
  Impact 7) — unchanged from Round 3. New backlog: 2 P1 (chart axis-label legibility, composition/
  empty-space gap on Home/Review Queue/Lead History), 1 P2 (mobile scroll regression, carried forward
  with a new confirmed instance), 3 P3 (carried forward unchanged). `.claude/project-metrics.md`'s
  `PROJECT_COMPLETED` entry appended with matching numbers. (Entry backfilled 2026-09-05 during Round 5 —
  this round's own session did not append it at the time, a gap this file's own "written immediately
  after it runs" convention should have caught; see `.claude/pipeline-reference.md`'s Round 4 write-up
  for the source data used to reconstruct it.)
- Surprise: direct pixel-level inspection (cropping/enlarging the new trend chart's axis-label region)
  found a genuine legibility defect that a full-page visual re-inspection had missed in Round 3's own
  verification — and confirmed the "large empty void" issue Round 2/3 scoped to Lead Detail alone is
  also visible on Home, Review Queue, and Lead History at 1920x1080, wider than previously credited.
- Agent: claude/claude_code

### 2026-09-05 — portfolio_evaluation (Round 5)
- Trigger: Step 12 (Batch Backlog Processor) completed Round 4's P1-01 (chart labels), P1-02
  (composition panels), and P2-02 (mobile reflow, 4 of 6 pages) and re-captured screenshots; Step 11
  re-ran unconditionally per `prompts/12_batch-backlog-processor.md`'s own Next Steps section.
- Expected effect: an anchored 0-10 re-score per `QUALITY_RUBRIC.md`'s four dimensions, gating routing
  to either Step 13 (≥9.0, Visual & UI/UX ≥9.0) or another Step 12 batch.
- Outcome: OVERALL SCORE 7/10 (Visual & UI/UX 8, Feature Signaling 9, Professional Readiness 8, Client
  Impact 7) — unchanged from Round 3/4 despite Feature Signaling's gain. New backlog: 1 P1 (page-height/
  whitespace gap, now measured across all 7 pages rather than 3), 1 P2 (2 mobile density exceptions),
  3 P3 (carried forward unchanged). `.claude/project-metrics.md`'s `PROJECT_COMPLETED` entry appended
  with matching numbers.
- Surprise: this round used a reproducible pixel-scan measurement (Python/Pillow, background-color
  boundary detection) instead of a visual estimate to quantify each screenshot's empty space, and the
  result contradicted the prior rounds' framing — the composition gap turned out to be present on every
  one of the 7 primary desktop pages (30-57% empty below content at 1920x1080), including Review Detail
  and Lead Detail, both explicitly credited as "genuinely closed" in Round 3/4. The prior batch's fix
  (adding one compact secondary panel per page) measurably reduced the empty fraction on the 3 pages it
  touched but did not close the underlying gap. Logged as a pipeline-level insight (composition/
  whitespace claims should be pixel-measured, not eyeballed) to `meta/PIPELINE_INSIGHTS_LOG.md`.
- Agent: claude/claude_code

### 2026-09-05 — portfolio_evaluation (Round 6)
- Trigger: Step 12 (Batch Backlog Processor) completed Round 5's P1-01 (project-wide whitespace fix)
  and P2-01 (mobile density exceptions, closed as a side effect) and re-captured screenshots; Step 11
  re-ran unconditionally per `prompts/12_batch-backlog-processor.md`'s own Next Steps section.
- Expected effect: an anchored 0-10 re-score per `QUALITY_RUBRIC.md`'s four dimensions, gating routing
  to either Step 13 (≥9.0, Visual & UI/UX ≥9.0) or another Step 12 batch.
- Outcome: OVERALL SCORE 9/10 (Visual & UI/UX 9, Feature Signaling 9, Professional Readiness 9, Client
  Impact 9) — up from 7/10, **first round to clear the 9.0 gate on all four dimensions.** Backlog is
  empty at P1/P2; only 5 P3 nice-to-haves remain (3 carried forward, 2 new optional 9→9.5 polish items).
  `.claude/project-metrics.md`'s `PROJECT_COMPLETED` entry appended with matching numbers. Routes to
  Step 13 (Portfolio Score Gate) for the first time this project.
- Surprise: given this exact defect class (a fix that looks complete without being independently
  re-verified) had already bitten this project twice — Round 4's chart-label fix, and Round 5's own
  measurement-script sidebar-exclusion bug — this round deliberately re-ran the pixel-scan script fresh
  against the current screenshots rather than trusting Round 5's self-reported numbers before scoring
  Visual & UI/UX at 9. The independent re-run reproduced Round 5's exact figures (2.0-2.9% desktop,
  2.4-2.7% mobile), confirming the fix generalizes rather than being an artifact of who measured it —
  not a surprise in outcome, but the specific verification step that made scoring 9 with confidence
  possible rather than repeating the same "looks fixed" mistake a third time.
- Agent: claude/claude_code
