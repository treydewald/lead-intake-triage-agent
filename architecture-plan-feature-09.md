IMPLEMENTATION PLAN
====================

Feature / Round: Feature 09 — Classification Accuracy Benchmark Report
Classification: New feature, Cross-system integration (harness invokes the real orchestrator stage +
real Ollama), AI integration
Planning Depth: Standard — genuinely new backend subsystem (dataset, harness, persistence, API) plus a
new frontend page, but every piece reuses an existing pattern from Features 03/08 rather than inventing
new architecture; not Deep because there is no new cross-stage coordination or state-machine change.

Objective
Add an honestly-measured, repeatable classification accuracy/consistency benchmark that exercises
Feature 03's real `IntentClassificationStage` (same code path production leads use) against a labeled
test-lead dataset, persists each run's results, and exposes them via API and a small React page —
directly measuring the project's stated "is the local LLM reliable" assumption instead of leaving it
assumed, per `project-definition.md`'s Nice-to-Have and `roadmap.md`'s Tier 2 Feature 09.

Existing Systems Analysis
- Reusable:
  - `app/orchestrator/tool_scope.py`'s `ToolRegistry`/`ScopedToolProxy` — the harness builds a registry
    exactly the way `app/tests/test_stage_intent_classification.py` does for tests, but with the real
    tool binding, not a fake one.
  - `app/orchestrator/tools/register_default_tools(registry, settings)` — already wires the real
    `ollama_classify` tool (bound to a live `ollama.Client`) into a `ToolRegistry`. The harness calls
    this directly instead of re-registering a fake or duplicate binding, which is what makes results
    "real production behavior" per the feature spec's own System Behaviors bullet.
  - `IntentClassificationStage` (`app/orchestrator/stages/intent_classification.py`) itself, invoked via
    `stage.run(intake_slice, proxy)` exactly as the orchestrator's `_make_node` does — no
    reimplementation of classification logic.
  - `IntakeSlice` (`app/orchestrator/state.py`) as the harness's per-test-case input shape — a labeled
    dataset item is just an `IntakeSlice` plus an expected label, so no new "lead" representation is
    needed.
  - Router/schema/frontend conventions established by Feature 08 (`routers/leads.py`,
    `schemas/pipeline.py`, `pages/LeadListPage.tsx`, `lib/api.ts`): list/detail endpoint pair, a
    Pydantic response schema per endpoint, a React page fetching from `lib/api.ts` and rendering a
    table — the benchmark report reuses this shape rather than a new API/page convention.
  - `Layout.tsx`'s existing `navItems` array — one new entry, no new nav mechanism.
- Duplication Risk Flagged: None found. No existing dataset, harness, or reporting mechanism exists
  anywhere in the codebase; `.claude/seed-data.md` is a *different* fixture (realistic-but-unlabeled
  data for screenshot/demo purposes per `docs/token-discipline.md`'s screenshot-capture tooling) and
  must not be reused or merged with the benchmark's labeled ground-truth dataset — they serve different
  purposes and have different correctness requirements (seed data has no ground-truth label field at
  all).
- Modify:
  - `backend/main.py` — register the new `benchmark` router.
  - `frontend/src/App.tsx` — add the `benchmark` route.
  - `frontend/src/components/Layout.tsx` — add a `Benchmark` nav item.
  - `frontend/src/lib/api.ts` — add typed fetch helpers for the two new endpoints.
  - `.claude/portfolio-reference.md` — one new Key Decision (below).
- New:
  - `backend/app/benchmark/dataset.py` — the labeled test-lead fixture (buyer/browser/spam/ambiguous
    categories), reason: no existing fixture carries ground-truth intent labels.
  - `backend/app/benchmark/harness.py` — `run_benchmark()`, reason: no existing code invokes a single
    stage outside the full graph for a non-test purpose.
  - `backend/app/models/benchmark.py` — `BenchmarkRun`/`BenchmarkCase` ORM models, reason: no existing
    table stores benchmark results (`project-definition.md`'s Database line explicitly calls for this).
  - `backend/app/schemas/benchmark.py` — response schemas, reason: new response shapes.
  - `backend/app/routers/benchmark.py` — `POST /benchmark/run`, `GET /benchmark/runs`,
    `GET /benchmark/runs/{run_id}`, reason: new resource.
  - `backend/alembic/versions/<new>_add_benchmark_tables.py` — migration for the two new tables.
  - `frontend/src/pages/BenchmarkPage.tsx` — the report/failure-case view, reason: new resource, no
    existing page shows benchmark data.

System Impact Map
```
backend/
  app/benchmark/
    dataset.py          [new]  labeled test-lead fixture (buyer/browser/spam/ambiguous)
    harness.py           [new]  run_benchmark(repeats, session_factory) -> BenchmarkRun
  app/models/
    benchmark.py         [new]  BenchmarkRun, BenchmarkCase (SQLAlchemy)
  app/schemas/
    benchmark.py         [new]  BenchmarkRunOut, BenchmarkRunSummaryOut, BenchmarkCaseOut
  app/routers/
    benchmark.py         [new]  POST /benchmark/run, GET /benchmark/runs, GET /benchmark/runs/{id}
  main.py                [modify] register benchmark.router
  alembic/versions/
    <new>_add_benchmark_tables.py  [new] benchmark_run, benchmark_case tables
frontend/
  src/pages/BenchmarkPage.tsx  [new]  trigger-run button, latest summary, failure-case table
  src/lib/api.ts               [modify] runBenchmark(), listBenchmarkRuns(), getBenchmarkRun()
  src/App.tsx                  [modify] route: /benchmark -> BenchmarkPage
  src/components/Layout.tsx    [modify] nav item: Benchmark -> /benchmark
existing systems touched (read-only, no changes):
  app/orchestrator/tool_scope.py           (ToolRegistry/ScopedToolProxy — reused as-is)
  app/orchestrator/tools/__init__.py       (register_default_tools — reused as-is)
  app/orchestrator/stages/intent_classification.py  (IntentClassificationStage — reused as-is)
  app/orchestrator/state.py                (IntakeSlice — reused as-is)
```

Implementation Order (Dependency Graph)
1. `app/benchmark/dataset.py` | Define the labeled fixture | existing: none | new: dataset.py |
   deps: none | requirements: at least buyer/browser/spam/ambiguous categories, each item an
   `IntakeSlice`-shaped dict plus `expected_label: str | None` (`None` for ambiguous items) and a
   short `case_id` | validation: dataset has >=4 categories represented, every non-ambiguous item has a
   non-null `expected_label` in `{"buyer","browser","spam"}`.
2. `app/models/benchmark.py` | Persist run + per-case results | existing:
   `app/database/session.py` (Base) | new: benchmark.py | deps: step 1's shape informs case fields |
   requirements: `BenchmarkRun(id, created_at, model_used, repeats, total_cases, accuracy, consistency)`;
   `BenchmarkCase(id, run_id FK, case_id, category, expected_label, is_ambiguous, attempts_json
   [list of {label, confidence} per repeat], correct: bool | None, consistent: bool)` | validation:
   migration applies cleanly against SQLite dev DB.
3. `alembic/versions/<new>_add_benchmark_tables.py` | Migration for step 2's tables | existing: prior
   migrations as pattern | new: one migration file | deps: step 2 | requirements: follows the existing
   `alembic revision --autogenerate` + manual review pattern already used for the other 4 migrations |
   validation: `alembic upgrade head` succeeds from a fresh DB.
4. `app/benchmark/harness.py` | `run_benchmark(repeats=3, session_factory=SessionLocal, settings=settings)
   -> BenchmarkRun` | existing: `ToolRegistry`, `register_default_tools`, `IntentClassificationStage`,
   `IntakeSlice` | new: harness.py | deps: steps 1-2 | requirements: build one `ToolRegistry` +
   `register_default_tools(registry, settings)` once per run (not once per case — matches production's
   one-registry-per-process pattern); for each dataset item, call
   `IntentClassificationStage().run(intake, proxy)` exactly `repeats` times; a raised exception or an
   `intent_label is None` result (the stage's own `classification_failed`/`empty_message_short_circuit`
   sentinels) counts as an incorrect/failed attempt, never excluded from the denominator, per the
   feature spec's timeout/failure edge case; persist one `BenchmarkRun` + one `BenchmarkCase` per
   dataset item | validation: harness run against a temporary/test Ollama-shaped fake tool in a unit
   test produces the exact accuracy/consistency numbers hand-computed from the fake's scripted
   responses.
5. `app/schemas/benchmark.py` | Response shapes | existing: `schemas/pipeline.py` as the sibling
   pattern | new: benchmark.py | deps: step 2 | requirements: `BenchmarkRunSummaryOut` (list view: id,
   created_at, accuracy, consistency, total_cases), `BenchmarkRunOut` (detail: summary fields + full
   `cases: list[BenchmarkCaseOut]` with predicted-vs-actual + confidence per case) | validation:
   `model_validate` round-trips ORM rows without extra DB queries beyond the two already issued by the
   router.
6. `app/routers/benchmark.py` | `POST /benchmark/run` (invokes harness synchronously, returns
   `BenchmarkRunOut`), `GET /benchmark/runs` (list, newest first), `GET /benchmark/runs/{run_id}`
   (detail incl. failure-case list) | existing: `routers/leads.py` as the sibling pattern
   (`get_session_factory` DI override for tests) | new: benchmark.py | deps: steps 4-5 | requirements:
   `GET /benchmark/runs/{run_id}` 404s on unknown id, same as `routers/leads.py`'s lead-detail 404 |
   validation: one test per endpoint, plus one asserting the failure-case list contains every
   misclassified case with predicted/actual label and confidence (acceptance criterion #3).
7. `main.py` | Register router | existing: main.py's existing 4-router pattern | new: none | deps:
   step 6 | requirements: one import + one `app.include_router(benchmark.router)` line | validation:
   `GET /benchmark/runs` reachable on the running app.
8. `frontend/src/lib/api.ts` | Typed fetch helpers | existing: existing helpers in the same file as
   pattern | new: none (same file, additive) | deps: step 6 | requirements:
   `runBenchmark()`, `listBenchmarkRuns()`, `getBenchmarkRun(runId)` matching the existing helpers'
   fetch/error-handling shape | validation: type-checks against the backend response shape.
9. `frontend/src/pages/BenchmarkPage.tsx` | Report view | existing: `LeadListPage.tsx` as the sibling
   pattern (table + status styling) | new: BenchmarkPage.tsx | deps: step 8 | requirements: a "Run
   Benchmark" button, latest run's accuracy/consistency shown prominently, a table of every
   misclassified case (predicted vs. actual label, confidence) — never filtered down to an aggregate
   score alone, per the feature spec | validation: one frontend test rendering a mocked run with at
   least one failure case and asserting it appears in the table.
10. `frontend/src/App.tsx` + `Layout.tsx` | Wire the route + nav | existing: existing route/nav
    patterns | new: none | deps: step 9 | requirements: `/benchmark` route, `Benchmark` nav item |
    validation: manual click-through, no console errors (same bar Step 7 already applies).

Architecture Rule Changes
- [ ] **A harness that needs to invoke a single orchestrator stage in isolation (outside the compiled
  graph) for a non-test purpose builds its own `ToolRegistry`, calls the existing
  `register_default_tools(registry, settings)` factory, and invokes `stage.run(input, registry.
  scoped_proxy(stage.allowed_tools, stage.name))` directly — never reimplementing the stage's decision
  logic, never bypassing `ScopedToolProxy`, and never registering a second, parallel tool binding for
  the same external system.** This is the production-benchmark analogue of the pattern
  `app/tests/test_stage_intent_classification.py` already uses with fake tool functions; Feature 09 is
  the first time this pattern is used with the *real* registered tools outside a test. Any future
  feature needing to invoke a stage standalone (a different benchmark, a manual replay/debug tool)
  should follow this same construction rather than inventing a new one. — Conflict check: none found.
  No existing Key Decision addresses out-of-graph single-stage invocation; this is new ground, not a
  contradiction of anything in `.claude/portfolio-reference.md`.

Feature-Specific Requirements
- Dataset (`app/benchmark/dataset.py`) ships with the repo as a Python-literal fixture (not a DB seed),
  so the benchmark is runnable with zero setup beyond a working Ollama install — consistent with the
  project's free-by-default constraint.
- Accuracy definition: correct predictions / total attempts, where "total attempts" = non-ambiguous
  dataset items × `repeats`, and a raised exception or a `None`/failure-sentinel result from the stage
  counts as an incorrect attempt (never excluded). Ambiguous items are excluded from the accuracy
  denominator entirely (no ground-truth label exists to score against) but are still persisted and
  shown in the report, explicitly marked ambiguous — never silently dropped.
- Consistency definition: per non-ambiguous-or-ambiguous item, the item is "consistent" if all
  `repeats` attempts produced the identical `intent_label` (a failed/None attempt breaks consistency for
  that item, it is not treated as a match with anything). Overall consistency % = consistent items /
  total items (ambiguous items included here, since label-stability is meaningful even without a known
  correct answer).
- Default `repeats = 3` for `POST /benchmark/run` (no request body needed for v1; a future round could
  make this configurable, but the feature spec doesn't require it).
- `POST /benchmark/run` runs synchronously and returns the completed `BenchmarkRunOut` — the dataset is
  small (roughly 20-30 items × 3 repeats = 60-90 local Ollama calls) so this stays within a reasonable
  request timeout for local development; no background job infrastructure is introduced for this.

Risks
- Risk: A synchronous `POST /benchmark/run` against a real local Ollama instance could take long enough
  to feel like a hung request in the UI. Mitigation: `BenchmarkPage.tsx` shows an explicit
  in-progress/loading state on the trigger button; dataset size is kept small (~20-30 items) precisely
  to keep total wall-clock time reasonable for local dev/demo use.
- Risk: Reusing `register_default_tools` pulls in the HubSpot tool registration too (that function wires
  every tool, not just `ollama_classify`), which could make the harness depend on HubSpot config being
  present even though the benchmark never calls a HubSpot tool. Mitigation: the harness only ever calls
  `scoped_proxy(IntentClassificationStage.allowed_tools, ...)` — `frozenset({"ollama_classify"})` — so
  an out-of-scope/missing HubSpot tool is never reachable; `register_default_tools` registering it
  anyway is harmless (registration doesn't require a live token, only calling `hubspot_write` would).
- Risk: A flaky/slow local Ollama call during a benchmark run could look identical to a genuine
  classification failure. Mitigation: not distinguished in v1 (out of scope per the feature spec, which
  explicitly wants failures/timeouts counted against the metric, not diagnosed) — this is intentional,
  not an oversight.

Acceptance Criteria
- [ ] The benchmark dataset includes at least buyer, browser, spam, and ambiguous example categories
- [ ] `POST /benchmark/run` computes and persists an accuracy percentage against ground-truth labels
  (never a self-reported model confidence used as the accuracy metric)
- [ ] `GET /benchmark/runs/{run_id}` returns every misclassified case with its predicted and actual
  label and confidence score
- [ ] Running the benchmark produces a consistency metric derived from repeated same-input runs, shown
  distinctly from the accuracy metric
- [ ] An ambiguous dataset item is shown in the report explicitly marked as such, never forced into a
  correct/incorrect bucket
- [ ] `BenchmarkPage.tsx` is reachable from the nav, shows the latest run's accuracy/consistency, and
  lists every failure case from that run

Validation Requirements
Step 7 must specifically check: the harness calls the real `IntentClassificationStage`/
`register_default_tools` path (not a reimplementation — grep for any duplicate classification logic);
an intentionally-ambiguous dataset item never appears counted in the accuracy denominator; a
deliberately-failing case (e.g. temporarily point `OLLAMA_MODEL` at a nonexistent model, or use a unit
test with a raising fake tool) is counted as incorrect, not excluded; the frontend page renders with no
console errors and the failure-case table matches the API response exactly (same bar as Feature 08's
Step 7 pass).

Predicted Footprint
Files predicted to change: 10 new (dataset.py, harness.py, models/benchmark.py, schemas/benchmark.py,
routers/benchmark.py, 1 migration, BenchmarkPage.tsx, plus 2-3 test files) + 4 modified (main.py,
App.tsx, Layout.tsx, lib/api.ts) + 1 modified (`.claude/portfolio-reference.md`)
Systems predicted to touch: orchestrator tool-scope/tools (read-only reuse), database/alembic (new
tables), FastAPI routers, React pages/routing/nav.
