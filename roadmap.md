TIERED FEATURE ROADMAP
======================

## Tier 1: Core (Required for MVP)

1. Pipeline Orchestration Layer
   Description: The state-machine backbone (LangGraph or an equivalent lightweight orchestrator) that
   coordinates the six pipeline stages as genuinely separate units — each with its own scoped tool
   access and its own piece of state — rather than one large prompt. This is the architectural
   foundation every other Tier 1 feature plugs into, and the single feature the source specification's
   Critical risk (per-stage boundary must be real under code inspection, not cosmetic) attaches to
   directly.
   Key Components: Stage interface/contract definition, state-machine graph wiring the 6 stages,
   per-stage tool-access scoping (enforced, not just documented), shared lead-record state schema,
   stage transition/error handling.
   Dependencies: None — must be built first; every other Tier 1 pipeline stage depends on it.

2. Intake Parsing & Normalization Stage
   Description: Normalizes a raw inbound lead (web form submission, email text, or missed-call callback
   transcript) into a structured lead record the rest of the pipeline can consume.
   Key Components: Web-form input handler, email text parser, callback-transcript input handler,
   structured lead-record schema, field-normalization logic.
   Dependencies: Pipeline Orchestration Layer.

3. Intent Classification Stage
   Description: Classifies lead intent/urgency (e.g. buyer vs. browser vs. spam) from the normalized
   lead record using a read-only-lookup-scoped stage, and produces a confidence score that later stages
   (enrichment, approval gate) key off of.
   Key Components: LLM classification call (local open-weight model via Ollama, with an optional
   hosted-API fallback path), confidence-score calculation, read-only tool scoping (no write access),
   classification-result schema.
   Dependencies: Pipeline Orchestration Layer, Intake Parsing & Normalization Stage.

4. Data Enrichment Stage
   Description: Fills missing lead fields (contact/context details) using external-lookup-scoped tools
   only — this stage explicitly has no CRM-write access, preserving the per-stage boundary.
   Key Components: External-lookup tool integration(s), missing-field detection, enrichment-result
   merge into the lead record, enforced read/lookup-only tool scoping.
   Dependencies: Pipeline Orchestration Layer, Intent Classification Stage.

5. HubSpot CRM Write Stage
   Description: An exclusively CRM-write-scoped stage that performs an idempotent, retry-safe
   create/update against HubSpot's real free-tier developer sandbox (real auth, real rate limits — not
   a mock), never creating duplicate records on retry.
   Key Components: HubSpot sandbox auth setup, idempotency key / dedupe-lookup strategy, create/update
   logic, retry-with-backoff handling, write-only tool scoping (no read/lookup access from other
   stages).
   Dependencies: Pipeline Orchestration Layer, Data Enrichment Stage.

6. Human Review & Approval Gate
   Description: Routes low-confidence classifications to a human reviewer with the agent's draft
   classification attached, instead of letting the pipeline auto-act on uncertain cases. High-confidence
   cases bypass this gate and proceed automatically to the CRM write stage.
   Key Components: Confidence-threshold routing logic, review-queue data model, reviewer
   approve/reject/edit action, resume-pipeline-on-approval hook.
   Dependencies: Pipeline Orchestration Layer, Intent Classification Stage (confidence score),
   HubSpot CRM Write Stage (the action being gated/resumed).

7. Outcome Notification (In-App)
   Description: Surfaces the pipeline's outcome — auto-processed vs. awaiting review — to the relevant
   user within the app, per the core workflow's Notification step.
   Key Components: In-app notification/toast or inbox item, outcome-event trigger from the orchestrator,
   notification data model.
   Dependencies: Pipeline Orchestration Layer, Human Review & Approval Gate.

8. Observability / Monitoring View
   Description: A React UI showing, per processed lead, what each pipeline stage decided, its
   confidence, and its outcome — the persisted, per-stage processing trace made visible. Doubles as a
   live walkthrough usable in a client conversation or proposal.
   Key Components: Per-lead stage-trace persistence (backend), React monitoring dashboard, per-lead
   detail view (stage-by-stage decisions/confidence/outcome), lead-list/filter view.
   Dependencies: Pipeline Orchestration Layer (all stages must log their trace), Outcome Notification.

## Tier 2: Enhancements (Improves Product Value)

1. Classification Accuracy Benchmark Report
   Description: A reported, honestly-measured classification accuracy/consistency benchmark, including
   failure cases (not cherry-picked successes) — directly measures the unproven local-LLM reliability
   assumption named in the project definition rather than leaving it assumed.
   Key Components: Labeled test-lead dataset, benchmark run harness, accuracy/consistency metric
   calculation, failure-case reporting view.
   Dependencies: Intent Classification Stage (Tier 1).

2. External Notification Delivery
   Description: Extends the in-app-only notification (Tier 1) with an external channel (email or
   Slack-style alert) on a routed-for-review case, so a human reviewer doesn't need to be watching the
   app.
   Key Components: Email or Slack webhook integration, outcome-to-external-channel trigger,
   delivery-failure handling.
   Dependencies: Outcome Notification (Tier 1).

3. Per-Lead Audit/History Trail UI
   Description: A full stage-by-stage timeline view per lead in the UI, beyond the current-state summary
   the Tier 1 monitoring view provides — shows the complete history of what happened to a given lead
   over time, including any human review action taken.
   Key Components: Timeline UI component, stage-transition history query, human-review-action history
   display.
   Dependencies: Observability / Monitoring View (Tier 1), Human Review & Approval Gate (Tier 1).

## Tier 3: Advanced (Future / Complex)

1. Multi-Agent Orchestration (Stretch Goal — explicitly deferred)
   Description: A more sophisticated multi-agent orchestration pattern beyond the current state-machine
   coordination. Explicitly deferred this round per the source specification's own adversarial
   resolution — recorded here for future-round visibility only; do not re-add mid-build.
   Key Components: (Deferred — not specified this round.)
   Dependencies: Pipeline Orchestration Layer (Tier 1) would need to be stable first.

2. Swappable CRM Interface
   Description: An abstraction allowing a second, paid CRM platform to be substituted for HubSpot
   without an architecture rewrite.
   Key Components: CRM adapter interface, HubSpot adapter refactored to implement it, second
   adapter (illustrative/future), config-driven CRM selection.
   Dependencies: HubSpot CRM Write Stage (Tier 1).

3. Multi-Channel Intake Expansion
   Description: Extends intake beyond web form / email / missed-call callback to additional channels
   such as SMS or a chat widget.
   Key Components: New channel input handler(s), normalization mapping into the existing lead-record
   schema.
   Dependencies: Intake Parsing & Normalization Stage (Tier 1).

## Dependency Notes
- The Pipeline Orchestration Layer is the single foundational dependency for every other Tier 1
  feature — it must be built first and establishes the enforced per-stage tool/state boundary that the
  project definition's Critical risk depends on holding throughout the rest of implementation.
- The pipeline stages have a strict linear data dependency matching the core workflow: Intake Parsing →
  Intent Classification → Data Enrichment → HubSpot CRM Write. The Human Review & Approval Gate sits
  between classification/enrichment and the CRM write action for low-confidence cases, and resumes the
  pipeline toward the CRM Write Stage on reviewer approval.
- Data Enrichment and HubSpot CRM Write must remain separately tool-scoped (lookup-only vs. write-only)
  even though they are adjacent in the pipeline — this is a boundary to enforce in code, not just an
  ordering note.
- Observability / Monitoring View depends on every upstream stage persisting its trace correctly, so it
  is built last in Tier 1, once the full pipeline is producing real trace data to display.
- Tier 2's Classification Accuracy Benchmark Report depends only on the Intent Classification Stage and
  can be started as soon as that stage is stable, in parallel with later Tier 1 items if desired.
- Tier 3's Multi-Agent Orchestration item is recorded for visibility only; it is out of scope this round
  and should not be started even if Tier 1/2 finish early.

## Execution Order Recommendation
1. Pipeline Orchestration Layer — Nothing else can be built or tested in isolation until the
   stage-coordination backbone and tool/state scoping model exist.
2. Intake Parsing & Normalization Stage — First real data enters the pipeline here; needed before
   classification has anything to classify.
3. Intent Classification Stage — Produces the confidence score that both Data Enrichment ordering and
   the Human Review gate depend on downstream.
4. Data Enrichment Stage — Completes the lead record before it's written to the CRM; exercises the
   lookup-only tool boundary against the write-only boundary that comes next.
5. HubSpot CRM Write Stage — The highest-risk external integration (real sandbox auth/rate limits);
   building it early leaves room to address surprises before the rest of the pipeline is finalized
   around it, per the project definition's own assumption that sandbox behavior should be verified
   early.
6. Human Review & Approval Gate — Wires into both the classification confidence score and the CRM
   write action, so both must exist first; completes the core decision logic of the pipeline.
7. Outcome Notification (In-App) — A thin layer on top of the now-complete decision pipeline.
8. Observability / Monitoring View — Built last in Tier 1 since it visualizes trace data that only
   exists once every upstream stage is logging it correctly.
</content>
