IMPLEMENTATION PLAN
====================

Feature / Round: Continued Development — Round (2026-09-06), deepens Feature 03 (Intent
Classification Stage). No new Feature ID: per `docs/continued-development.md` CD-1, this round
"materially deepens or corrects an existing [capability]" (how `confidence_score` is computed) —
it adds no new route, UI surface, or countable feature.
Classification: AI integration, Architecture change, Feature expansion (of an existing capability)
Planning Depth: Deep — this is an AI-integration change touching 5 existing systems (the
classification stage, the Ollama tool binding, the benchmark harness, the live confidence-threshold
routing gate, and `.claude/portfolio-reference.md`'s Key Decisions), and it changes the meaning of a
value multiple other features already depend on.

Objective
Replace `IntentClassificationStage`'s current confidence score — a single number taken verbatim
from one deterministic (temperature=0) LLM self-report — with a computed composite of three
independently-varying signals, so `confidence_score` stops clustering on the small set of round
numbers (0.80/0.85/0.90) a self-reporting LLM habitually produces, and instead reflects real,
continuously-varying evidence.

Existing Systems Analysis
- Reusable: `app/orchestrator/tools/ollama_tools.py`'s `classify_intent()` (Feature 03) — the same
  binding can serve a second, best-effort "confirmation" sample at a different temperature; no new
  tool needs registering. `app/benchmark/harness.py`'s existing repeats-and-agreement pattern
  (Feature 09) already established that self-consistency across repeated real model calls is a
  meaningful signal in this project — this round applies that same idea *inside* the live
  classification path itself (one extra confirmation call per lead) rather than only at benchmark
  time. `ToolRegistry`/`ScopedToolProxy.call(*args, **kwargs)` (Feature 01) already supports passing
  extra keyword arguments straight through to a registered tool, so a `temperature` override needs no
  scoping-layer change. The existing "a stage's own external-system failure is encoded as data, never
  raised" family of Key Decisions (Features 03/04/05/10) already establishes the precedent for a
  best-effort signal degrading gracefully instead of failing the run.
- Duplication Risk Flagged: none found. No existing module already computes a confidence signal from
  lead text or from call-to-call agreement inside the live path (Feature 09's benchmark harness
  computes consistency only in aggregate, across a whole dataset run, never as a per-lead value fed
  back into `confidence_score` itself).
- Modify: `backend/app/orchestrator/tools/ollama_tools.py` (accept a caller-supplied `temperature`,
  defaulting to 0.0 — the existing deterministic primary call is unchanged); `backend/app/orchestrator/
  stages/intent_classification.py` (compute the composite score instead of passing the self-report
  through verbatim).
- New: `backend/app/orchestrator/confidence_scoring.py` — the composite-scoring math lives in its own
  module, not inline in the stage, so it has independent unit tests that don't require mocking an LLM
  call (pure functions over plain floats/strings).
- Navigation Relationships Flagged: none. No new page, route, or countable feature — every existing
  consumer of `confidence_score` (`LeadDetailPage.tsx`, `LeadListPage.tsx`, `ReviewQueuePage.tsx`,
  `ReviewDetailPage.tsx`, `LeadHistoryPage.tsx`, `BenchmarkPage.tsx`'s Threshold Simulator,
  `FunnelDashboardPage.tsx`) already renders an arbitrary float via `ConfidenceMeter`/`.toFixed(2)` —
  checked directly (`frontend/src/components/ui/ConfidenceMeter.tsx:18` does
  `Math.round(value * 100)`; `ReviewQueuePage.tsx:134/155` uses `.toFixed(2)`), neither assumes a
  small fixed set of possible values, so no frontend file needs to change.

System Impact Map

CONFIDENCE SCORING (deepens Feature 03)
│
├── Frontend
│   ├── none — all existing consumers already render an arbitrary float (verified above)
│
├── Backend
│   ├── `app/orchestrator/stages/intent_classification.py` — composite scoring, one best-effort
│   │     confirmation tool call
│   ├── `app/orchestrator/tools/ollama_tools.py` — `classify_intent()` gains an optional
│   │     `temperature` parameter (default 0.0, existing callers unaffected)
│   ├── `app/orchestrator/confidence_scoring.py` — new, pure composite-scoring functions
│
├── Database
│   ├── none added — `ClassificationSlice.confidence_score` (Feature 01/03) stays a `float | None`;
│   │     only what populates it changes
│
├── Existing Systems (reused, not duplicated)
│   ├── `ollama_classify` tool binding (Feature 03) — reused for a second, differently-parameterized
│   │     call, not a new tool
│   ├── `_route_after_enrich`'s `confidence >= confidence_threshold` gate (Feature 06) — unchanged;
│   │     still reads whatever float `ClassificationSlice.confidence_score` holds
│   ├── `app/benchmark/harness.py` (Feature 09) — invokes the real stage unmodified, so it exercises
│   │     the new composite scoring automatically with zero code change
│   ├── `frontend/src/lib/thresholdSimulation.ts` (Feature 17) — unchanged; still a pure function of
│   │     whatever `confidence` values the benchmark cases now carry
│
├── Navigation
│   ├── none new — see Existing Systems Analysis above
│
└── AI
    ├── Context builder: unchanged (`_build_lead_text`)
    ├── Structured generation: unchanged shape (`{"intent_label", "confidence_score"}` JSON), now
    │     invoked a second time per successful classification at a nonzero temperature
    └── Output validation: unchanged (`_is_valid_response`), applied to both calls independently

Implementation Order (Dependency Graph)

`confidence_scoring.py` (new, no dependencies) → `ollama_tools.classify_intent()` temperature
parameter (independent of the above) → `IntentClassificationStage.run()` wiring (depends on both)
→ test updates (`test_confidence_scoring.py` new; `test_orchestrator_tools.py`/
`test_stage_intent_classification.py` updated) → live verification against the real local
`llama3.2:3b` model (depends on all of the above existing and passing).

1. **`app/orchestrator/confidence_scoring.py`** — purpose: pure, LLM-independent composite-scoring
   math. Existing files affected: none. New files: `confidence_scoring.py`. Dependencies: none.
   Requirements: `lexical_signal(lead_text, intent_label, *, has_contact_info) -> float` derives a
   deterministic [0,1] signal from message length, per-label keyword hits, and contact-info
   completeness — zero dependency on any LLM call, so it varies continuously per lead regardless of
   what the model self-reports; `combine(self_reported, lexical, consistency) -> float` blends the
   three signals (weights 0.55/0.20/0.25 when a consistency sample exists; 0.70/0.30 fallback split
   between self-reported and lexical when it doesn't), clamped to `[0.0, 1.0]`. Validation: unit
   tests cover the weighting arithmetic directly, the fallback path, and clamping at both extremes.

2. **`ollama_tools.classify_intent()` temperature parameter** — purpose: let the stage request a
   differently-parameterized confirmation sample through the exact same tool binding. Existing files
   affected: `ollama_tools.py`. New files: none. Dependencies: none. Requirements: `temperature:
   float = 0.0` default preserves the existing deterministic primary-call behavior and every existing
   caller/test unchanged; the value flows straight into `options={"temperature": temperature}`.
   Validation: existing `test_classify_intent_calls_with_deterministic_json_mode_options` must pass
   unmodified; one new test asserts a passed-through non-default temperature reaches the client call.

3. **`IntentClassificationStage.run()` composite wiring** — purpose: use the new pieces to produce
   `confidence_score`. Existing files affected: `intent_classification.py`. New files: none.
   Dependencies: steps 1-2. Requirements: the existing 2-attempt retry loop for the *primary* call
   and the `classification_failed`/`empty_message_short_circuit` sentinels are unchanged — the
   composite path only runs after a valid primary response is already in hand. On a valid primary
   response, issue exactly one additional best-effort confirmation call
   (`tools.call("ollama_classify", lead_text, temperature=confidence_scoring.CONFIRMATION_TEMPERATURE)`)
   wrapped in `try/except Exception`, never retried, never allowed to turn a successful classification
   into a failure; if it raises or returns an invalid response, `consistency` is `None` and `combine()`
   uses its fallback weighting. `intent_label` itself is decided by the primary call alone — the
   confirmation call feeds only the confidence number, never overrides the label. Validation: stage
   tests cover agreement (consistency=1.0), disagreement (consistency=0.0), and confirmation-call
   failure (fallback weighting) — each asserting `result.confidence_score` equals
   `confidence_scoring.combine(...)` called with the same inputs, so the stage test verifies wiring
   and `test_confidence_scoring.py` verifies the math, with no duplicated magic numbers between them.

Architecture Rule Changes
- [ ] **`IntentClassificationStage.confidence_score` (and any future stage that emits a confidence-style
  value) must be a composite of at least one LLM-independent signal, never a single LLM self-report
  passed through verbatim** — proposed addition to `.claude/portfolio-reference.md`'s Key Decisions.
  Conflict check: no existing Key Decision states how `confidence_score` must be computed (the
  existing Key Decisions about it — Feature 08's denormalized-column rule, Feature 17's `>=` boundary
  rule — govern how the value is *stored* and *compared*, never how it's *produced*); none found to
  reconcile against.
- [ ] **A stage's own best-effort secondary signal-gathering call (distinct from its primary,
  run-defining call) must be exception-safe inside `run()` and degrade to a reduced-weight fallback on
  failure, never raising or invalidating an already-successful primary result** — proposed addition to
  Key Decisions. Conflict check: this generalizes, rather than restates, the existing "external-system
  failure encoded as data, never raised" family (Features 03/04/05) and the "internally exception-safe,
  return a status, never raise" rule (Feature 10) to a new case those didn't cover: a *secondary* call a
  stage makes *to enrich its own already-decided output*, as opposed to either a primary call whose
  failure the pipeline must route around, or plumbing invoked strictly after a stage completes. No
  contradiction found; this is the same underlying discipline applied one level deeper.

Feature-Specific Requirements
- Weight constants (0.55 self-reported / 0.20 lexical / 0.25 consistency; 0.70/0.30 fallback) and the
  confirmation temperature (0.6) are this round's specific tuning choices, not a durable rule other
  features must follow — they live as named constants in `confidence_scoring.py`, not in Key
  Decisions.
- Keyword lists in `lexical_signal()` are a deliberately small, illustrative set per label (not an
  exhaustive taxonomy) — this is a portfolio project demonstrating the technique, not a production
  spam-classification system; expanding the lists is a low-risk future tuning pass, not an
  architecture change.

Risks
- Risk: an extra real Ollama call per successful classification roughly doubles per-lead classification
  latency and roughly doubles `run_benchmark()`'s total runtime (each of its `repeats` attempts now
  issues 2 real model calls instead of 1). Mitigation: the local model is small (`llama3.2:3b`, already
  the project's chosen default) and the confirmation call is best-effort with no retry, so the added
  cost is bounded to exactly one extra call per successful classification, never more; CD-4 measures
  the actual live benchmark runtime to confirm it stays acceptable for a synchronous, single-operator
  workflow (this project has no queueing/async requirement for benchmark runs).
- Risk: blending in a lexical heuristic could make `confidence_score` *less* correlated with actual
  correctness than the raw self-report was, silently degrading the quality of the
  `confidence >= threshold` routing gate it feeds. Mitigation: CD-4 re-runs the real benchmark
  (Feature 09) after implementation and compares accuracy/consistency against the pre-change baseline
  recorded in `.claude/pipeline-reference.md`/`portfolio-evaluation.md` — a material regression is
  treated as a defect per `docs/continued-development.md` CD-4's performance-regression discipline,
  not shipped silently.
- Risk: the confirmation call's own `intent_label` disagreeing with the primary call could confuse a
  future reader who expects `confidence_score` alone to explain routing. Mitigation: `intent_label` is
  always the primary call's decision, documented explicitly in `IntentClassificationStage`'s own
  docstring and in this plan's Implementation Order step 3 — the confirmation call never changes which
  label is assigned, only how confident the stage is willing to say it is.

Acceptance Criteria
- [ ] `confidence_score` for a batch of real classifications against the live local model shows more
  than 3 distinct values (the reported problem: prior sessions' live verification runs clustered on
  0.80/0.85/0.90 — see `.claude/pipeline-reference.md`'s twenty-fifth/prior-session notes referencing
  a `CONFIDENCE_THRESHOLD=0.95` override "since the real local model proved consistently overconfident
  on ambiguous test messages")
- [ ] Every existing backend test passes unmodified except the ones this plan explicitly names for
  update (`test_stage_intent_classification.py`'s exact-equality assertions, which now assert against
  `confidence_scoring.combine(...)` instead of the raw mocked self-report)
- [ ] `classify_intent()`'s existing deterministic-temperature test passes with zero changes
- [ ] The full real benchmark (Feature 09) runs successfully end-to-end against the live local model
  and its accuracy does not regress materially (>5 percentage points, matching CD-4's own
  performance-regression threshold convention) from the last recorded figure

Validation Requirements
- CD-4 must run the full backend test suite and confirm the new/updated tests pass
- CD-4 must live-verify against the real local `llama3.2:3b` model (not mocked) — same standard this
  project has applied to every prior AI-integration change (Features 03, 09, 15) — and record the
  actual distribution of `confidence_score` values produced, not just "it compiles"
- CD-4 must re-run `run_benchmark()` against the real model and compare accuracy/consistency to the
  previously recorded figures

Predicted Footprint
Files predicted to change: 5 (`confidence_scoring.py` new, `confidence_scoring_test.py`/
`test_confidence_scoring.py` new, `ollama_tools.py`, `intent_classification.py`,
`test_orchestrator_tools.py`, `test_stage_intent_classification.py`) — 7 total including this plan's
own Actual Footprint appendix.
Systems predicted to touch: intent classification stage, Ollama tool binding, benchmark harness
(exercised, not edited), `.claude/portfolio-reference.md` Key Decisions.

--- filled in later, by Step 7 / CD-4, once implementation is verified ---
Actual Footprint
Files actually changed: 9 — 1 more than predicted: `backend/app/orchestrator/confidence_scoring.py`
(new), `backend/app/tests/test_confidence_scoring.py` (new), `backend/app/orchestrator/tools/
ollama_tools.py`, `backend/app/orchestrator/stages/intent_classification.py`,
`backend/app/tests/test_orchestrator_tools.py`, `backend/app/tests/test_stage_intent_classification.py`,
plus two test files this plan's Existing Systems Analysis under-predicted —
`backend/app/tests/test_orchestrator_graph.py` and `backend/app/tests/test_benchmark_harness.py`
(graph-level and benchmark-harness tests that fake `ollama_classify` with a fixed-arity `lambda text:
...` needed their fakes updated to accept the new confirmation call, and their exact-equality
`confidence_score` assertions updated to compare against `confidence_scoring.combine(...)` instead of
the raw mocked self-report) — plus `backend/app/tests/test_router_benchmark.py`, same reason, plus this
plan's own Actual Footprint appendix.
Deviations from plan: the Predicted Footprint named only `intent_classification.py`'s and
`ollama_tools.py`'s own direct unit tests; it under-counted how many *other* existing test files fake
the `ollama_classify` tool with a single-argument lambda and assert an exact `confidence_score` value.
No architectural rework — every fix was mechanical (accept `temperature`, compare against the real
composite formula instead of a hardcoded number) — but a Deep-tier Existing Systems Analysis should
have grepped for all `"ollama_classify"` call sites project-wide up front rather than discovering the
remaining three during CD-4's full-suite run. Noted as a planning-accuracy lesson, not a defect in the
shipped code.
Rework required: none beyond the test-fake updates above. Full backend suite: 184/184 passing (10 new:
9 in `test_confidence_scoring.py`, 1 net new stage test — several existing stage tests were rewritten
in place rather than added). Full frontend suite: 66/66 passing, unchanged — confirmed no frontend file
needed edits (every existing `confidence_score` consumer already renders an arbitrary float; see
Existing Systems Analysis).
**Live-verified against the real local `llama3.2:3b` model (not mocked):** ran the real
`run_benchmark(repeats=3)` against the existing 22-case dataset end-to-end (66 real
`IntentClassificationStage.run()` calls, ~130 real Ollama calls including confirmation samples).
Result: **accuracy 87.0% / consistency 90.9% — identical to the last recorded baseline**
(`.claude/pipeline-reference.md`'s Feature 09 session note), confirming the composite scoring did not
regress classification quality. **Confidence diversity: 19 distinct values across 22 cases**
(`[0.0, 0.4704, 0.4776, 0.4848, 0.5422, 0.7324, 0.7706, 0.7776, 0.7824, 0.785, 0.785, 0.7874, 0.7874,
0.7898, 0.7922, 0.7946, 0.7946, 0.8326, 0.8398, 0.8446, 0.847, 0.897]`) — directly closing the
originating problem (self-reported confidence previously clustering on 0.80/0.85/0.90). Elapsed time
for the live run: ~326s (repeats=3, 22 items) — roughly double a pre-change run of the same shape, as
predicted in Risks; acceptable for this project's synchronous, single-operator benchmark endpoint.
