IMPLEMENTATION PLAN
====================

Feature / Round: Feature 17 (Confidence-Threshold "What-If" Simulator)
Classification: Feature expansion, Cross-system integration, UI/UX change
Planning Depth: Standard — touches exactly two existing systems (Feature 06's confidence gate,
Feature 09's benchmark dataset) plus one existing page; no new data model, no new external
integration, no architecture change.

Objective
Connect Feature 09's already-persisted per-case confidence/correctness data to Feature 06's live
`CONFIDENCE_THRESHOLD` setting, so a candidate threshold's effect (how many cases would auto-process
vs. route to review, and how many of those auto-processed cases would actually be wrong) is visible
before the real setting is ever touched.

Existing Systems Analysis
- Reusable: `BenchmarkCase.confidence`/`.correct`/`.is_ambiguous` — already computed and persisted by
  Feature 09's harness, already returned in full by the existing `GET /benchmark/runs/{run_id}`
  response (`BenchmarkCaseOut`, `backend/app/schemas/benchmark.py`). `BenchmarkPage.tsx`'s existing
  `latestRun`/`runs` state and run-switching logic (`handleSelectRun`) — the simulator rides on
  whichever run is already selected, no new fetch/state machine needed. `Settings.confidence_threshold`
  (`backend/app/core/config.py`) — the single source of truth Feature 06's live gate already reads;
  the simulator must read the exact same value, never a duplicated/hardcoded default. The
  `<details>`/`<summary>` collapsible pattern `LeadDetailPage.tsx` already established for optional
  deeper content ("View stage output"), reused here for the same reason (zero footprint when
  collapsed, avoids extra state for an open/closed toggle).
- Duplication Risk Flagged: **the Scope Expansion candidate (`scope-expansion.md`'s S-02) proposed "a
  new derived endpoint computing the auto/review split from a benchmark run's already-stored per-case
  confidence values."** Checking the actual data shape (`BenchmarkCaseOut` already includes
  `confidence`, `correct`, `is_ambiguous` per case, and the frontend already has the full case array
  in memory once a run is selected) shows this would duplicate a computation the frontend can do
  directly over data it already holds — a network round-trip per slider drag for arithmetic that's a
  single array `.filter()`/`.reduce()` client-side. **Resolution: no simulation-computation endpoint.**
  The only genuinely-missing piece is the live threshold value itself (nothing today exposes any
  config to the frontend), which is the one new endpoint this plan adds.
- Modify: `backend/app/routers/benchmark.py` (add one route); `frontend/src/pages/BenchmarkPage.tsx`
  (add the panel); `frontend/src/lib/api.ts` (add the new endpoint's client function and type).
- New: `frontend/src/lib/thresholdSimulation.ts` — a pure function, not a component, so its edge-case
  behavior (extremes, boundary equality, zero-ambiguous/zero-misclassified) is unit-testable without
  rendering anything. `GET /benchmark/confidence-threshold` — nothing else exposes backend config
  today; scoped to this one non-sensitive numeric value, not a general settings-dump endpoint (which
  would risk exposing something sensitive later without a deliberate per-field decision each time).
- Navigation Relationships Flagged: none new. The panel lives inside `BenchmarkPage.tsx`, the page
  that already owns both the accuracy data and the "what does this data mean for the live gate"
  question — no new page, no new route, nothing else needs a link to or from it.

System Impact Map

FEATURE 17 — Confidence-Threshold "What-If" Simulator
│
├── Frontend
│   ├── `BenchmarkPage.tsx` — new collapsible "Threshold Simulator" panel
│   ├── `lib/thresholdSimulation.ts` — new pure computation
│   ├── `lib/api.ts` — new `getConfidenceThreshold()`
│
├── Backend
│   ├── `app/routers/benchmark.py` — new `GET /confidence-threshold`
│
├── Database
│   ├── none added
│
├── Existing Systems (reused, not duplicated)
│   ├── `BenchmarkCase`'s existing per-case `confidence`/`correct`/`is_ambiguous` fields (Feature 09)
│   ├── `Settings.confidence_threshold` (Feature 06)
│   ├── `BenchmarkPage.tsx`'s existing run-selection state (`latestRun`, `handleSelectRun`)
│   ├── `LeadDetailPage.tsx`'s `<details>` collapsible pattern
│
├── Navigation
│   ├── none new — see Existing Systems Analysis above
│
└── AI
    └── N/A — no new AI integration; reads already-computed classification results, runs no new
          inference

Implementation Order (Dependency Graph)

`Settings.confidence_threshold` (existing) → `GET /benchmark/confidence-threshold` (new)
  → `getConfidenceThreshold()` in `api.ts` (new; depends on the route existing)
  → `simulateThreshold()` pure function (new; independent of the above, depends only on the
    existing `BenchmarkCase` shape)
  → Threshold Simulator panel on `BenchmarkPage.tsx` (new; depends on both of the above)

1. **`GET /benchmark/confidence-threshold`** (`benchmark.py`) — purpose: expose the live threshold
   read-only. Existing files affected: `benchmark.py`. New files: none (a `ConfidenceThresholdOut`
   schema is small enough to inline in the route's `response_model` via an existing-style Pydantic
   model, added to `schemas/benchmark.py`). Dependencies: `Settings` (already imported project-wide).
   Requirements: no auth/param — this is a non-sensitive numeric value, same "safe to read openly"
   class as everything else this router already returns. Validation: endpoint test asserts the
   response matches `settings.confidence_threshold` exactly, including after a `monkeypatch` override
   (proving it reads live, not a cached/hardcoded copy).

2. **`simulateThreshold(cases, threshold)`** (`thresholdSimulation.ts`) — purpose: pure computation,
   independent of any component. Existing files affected: none. New files:
   `thresholdSimulation.ts`. Dependencies: the existing `BenchmarkCase` TypeScript interface
   (`api.ts`). Requirements: `confidence >= threshold` is "auto-processed" (matches Feature 06's own
   `>=` convention in `_route_after_enrich`, `backend/app/orchestrator/graph.py` — this plan's
   Acceptance Criteria requires this boundary to match production exactly, so the two must never
   drift independently); among auto-processed cases, split into correct/incorrect/ambiguous
   (`is_ambiguous` cases have `correct === null` and must never be miscounted as either correct or
   incorrect). Validation: unit tests for extremes (0.0/1.0), boundary equality, an all-ambiguous run,
   and a run with zero misclassifications.

3. **`getConfidenceThreshold()`** (`api.ts`) — purpose: thin GET wrapper, same shape as every other
   `api.ts` function. Existing files affected: `api.ts`. New files: none. Dependencies: step 1.
   Requirements: returns `{ confidence_threshold: number }`. Validation: covered by step 4's component
   test (mocked) plus a live check during CD-4.

4. **Threshold Simulator panel** (`BenchmarkPage.tsx`) — purpose: user-facing entry point. Existing
   files affected: `BenchmarkPage.tsx`, `BenchmarkPage.test.tsx`. New files: none. Dependencies: steps
   1-3. Requirements: collapsed by default (`<details>`); fetches the live threshold once per page
   load (not per slider drag); recomputes via `simulateThreshold()` on every slider change, entirely
   client-side; re-derives from `latestRun.cases` whenever `latestRun` changes (run switch); renders
   nothing if no run is loaded (mirrors the page's existing empty-state gate). Validation: component
   test simulates a slider change and asserts the displayed counts update; a second test switches the
   selected run and asserts the panel's counts re-base to the new run's cases.

Architecture Rule Changes
- [ ] None proposed. This feature connects two already-established systems (Feature 06's threshold,
  Feature 09's dataset) exactly as each already works; it does not introduce a new pattern other
  features would need to follow. Conflict check: none found — no existing Key Decision addresses
  config exposure to the frontend or client-side derived computation, so there is nothing to
  reconcile against.

Feature-Specific Requirements
- The panel is collapsed by default specifically because this session cannot live-verify the
  page's no-scroll constraint (`docs/ui-design-standards.md` §1, established by Step 8 with real
  Playwright measurements) across all four target viewports — no browser-automation tool is
  available this session (same capability gap noted in this project's own Feature 11/Step 7
  verification history). A collapsed-by-default panel means an incorrect height estimate has zero
  effect on the page's default, already-verified layout; only a user who deliberately expands it
  sees the new content, and CD-5's polish/UI-audit trigger conditions can re-visit the expanded
  state's layout in a future session that does have browser automation available.

Risks
- Risk: the simulator's `>=` boundary convention silently drifts from `_route_after_enrich`'s real
  production convention if either is changed independently in the future. Mitigation: both are
  documented as required-to-match in this plan and in `simulateThreshold`'s own code comment; a
  future change to one should grep for the other before shipping.
- Risk: adding the panel regresses the page's no-scroll constraint when expanded. Mitigation:
  collapsed by default (see Feature-Specific Requirements); explicitly flagged as `UNVERIFIED` for
  the expanded state per `docs/agent-portability.md`'s Visual Certification state, not silently
  assumed fine.
- Risk: `GET /benchmark/confidence-threshold` becomes a precedent for casually exposing more config
  later, including something sensitive. Mitigation: scoped to this one named, non-sensitive value in
  this plan; any future config-exposure need should make its own explicit safety judgment, not treat
  this endpoint as a general precedent to extend carelessly.

Acceptance Criteria
- [ ] All acceptance criteria already stated in `implementation_plan.md`'s Feature 17 spec
- [ ] `simulateThreshold`'s auto/review boundary at a given confidence value matches
  `_route_after_enrich`'s real routing decision for the same confidence and threshold (cross-checked
  by a backend + frontend test pair using the same numeric example)

Validation Requirements
- CD-4 must confirm the live-fetched threshold in the frontend matches `Settings.confidence_threshold`
  via an actual HTTP call against a real running backend, not only a mocked test
- CD-4 must confirm the panel adds no visible layout regression to `BenchmarkPage.tsx`'s existing
  (already-verified) collapsed-state rendering, and must record the expanded-state visual check as
  `UNVERIFIED` (no browser automation available) rather than silently claiming full visual
  verification

Predicted Footprint
Files predicted to change: 8 (`benchmark.py`, `schemas/benchmark.py`, `api.ts`, `BenchmarkPage.tsx`,
`BenchmarkPage.test.tsx`, `thresholdSimulation.ts`, `thresholdSimulation.test.ts`, plus 1 new backend
test file, plus this plan's own Actual Footprint appendix)
Systems predicted to touch: benchmark router, benchmark schemas, BenchmarkPage frontend

--- filled in later, by Step 7 / CD-4, once implementation is verified ---
Actual Footprint
Files actually changed: 8 — exactly as predicted: `backend/app/routers/benchmark.py`,
`backend/app/schemas/benchmark.py`, `backend/app/tests/test_router_benchmark_threshold.py`,
`frontend/src/lib/api.ts`, `frontend/src/lib/thresholdSimulation.ts`,
`frontend/src/lib/thresholdSimulation.test.ts`, `frontend/src/pages/BenchmarkPage.tsx`,
`frontend/src/pages/BenchmarkPage.test.tsx`, plus this plan's own Actual Footprint appendix.
Deviations from plan: none. The `ConfidenceThresholdOut` schema was added to
`backend/app/schemas/benchmark.py` (predicted) rather than inlined elsewhere, as planned.
Rework required: none. Full backend suite (149/149) and frontend suite (56/56) passed on the
first full run. Live-verified against a real running backend with a real, pre-existing 22-case
benchmark run: at the live 0.7 threshold, 21/22 cases would auto-process, of which 3 are actually
incorrect and 3 are ambiguous — confirming both the endpoint and the client-side computation
against real data, and surfacing a genuinely useful finding (3 silently-wrong auto-approvals at
the current threshold) as a side effect of building the feature. Expanded-panel visual layout
recorded `UNVERIFIED` per `docs/agent-portability.md` (no browser automation available this
session) rather than assumed fine — see this plan's Feature-Specific Requirements.
