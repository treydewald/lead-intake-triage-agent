PROJECT ADVISOR REPORT
======================

Project: Lead Intake Triage Agent

## Project Strategy
Mode: STANDARD — see docs/project-strategy.md
Intent: PORTFOLIO
Lifetime: MEDIUM
Scale: MEDIUM
Optimization Objective: PORTFOLIO_SIGNAL
Steps 10-16 (screenshots/evaluation/gate/docs/publish) this cycle: MANDATORY
[Optimization Objective is PORTFOLIO_SIGNAL, not SPEED, so Steps 10-16 remain mandatory per
docs/project-strategy.md's "Mode Effects on Steps 10-16." Consistent with the source specification's
own stated Intended Mode: STANDARD.]

## Summary
A multi-step AI agent that ingests inbound sales leads (web form, email, or missed-call callback),
classifies intent, enriches missing data, writes the result into a real CRM (HubSpot's free developer
sandbox), and routes low-confidence cases to a human for approval instead of acting on them blindly.
The pipeline is built from genuinely separate stages — each with its own scoped tool access and its own
piece of state — rather than one large prompt relabeled as "agents." It exists to demonstrate that AI
can take real, multi-step, reliable action across business systems, not just answer questions, which
is the exact differentiation named as the highest-priority, highest-growth capability gap in this
developer's current portfolio.

## Value Proposition
Inbound leads routinely arrive unstructured and require a human to read, classify intent, judge
urgency, update the CRM, and route to the right person — a manual, error-prone, slow step directly
named in client language ("connect our systems," "reduce manual work"). This project proves the
developer can automate that step reliably: genuine per-stage tool/state separation (not a prompt
wrapper), idempotent retry-safe CRM writes, a measured (not assumed) classification-accuracy benchmark,
and integration against one real, named CRM platform with real auth and rate limits. It closes the
Agentic Workflow Automation gap — ranked #1, HIGH strategic priority, in this developer's own
portfolio gap analysis — by extending an already-proven pattern (tested FastAPI backends making live
third-party API calls, plus direct CRM-domain modeling experience) into the single highest-value
capability area the 2026 market currently rewards, rather than starting a new capability from zero.

## Users & Use Cases
Primary users: small-to-mid B2B service businesses running a CRM-based sales pipeline (illustrated
concretely via a real-estate or home-services framing; the underlying workflow generalizes across B2B
service verticals).

Key use cases:
1. A web-form lead arrives with a vague message ("interested, call me") — the agent classifies intent
   (buyer vs. browser vs. spam), enriches missing contact/context fields, and creates/updates the
   HubSpot record automatically.
2. An email lead contains enough signal for high-confidence classification and routing — the agent
   writes the CRM update and routes it to the correct rep with no human step required.
3. A missed-call callback transcript is ambiguous — the agent's confidence score falls below threshold,
   so it stops short of acting and routes the case to a human reviewer with its draft classification
   attached, rather than silently guessing.
4. A sales manager opens the observability view to see, per lead, what each pipeline stage decided, its
   confidence, and its outcome — usable as a live walkthrough in a client conversation or proposal.

## Core System Definition
Inputs: Inbound lead records (web form submission, email text, missed-call callback transcript) —
unstructured or semi-structured text plus whatever structured fields (name, phone, source) already
exist.

Outputs: A classified, enriched HubSpot CRM record (created or updated, never duplicated on retry); a
routing decision (auto-processed vs. routed to human review); a notification on action taken or review
needed; a per-lead processing trace (stage-by-stage decision, confidence, outcome) for the observability
view; a measured classification-accuracy benchmark report.

Workflow:
1. Intake parsing — normalize the raw lead (web form / email / callback transcript) into a structured
   record.
2. Intent classification — classify lead intent/urgency using a read-only-lookup-scoped stage; produce
   a confidence score.
3. Data enrichment — fill missing fields using external-lookup-scoped tools only (no CRM-write access
   at this stage).
4. CRM update action — an exclusively CRM-write-scoped stage performs an idempotent, retry-safe
   create/update against the HubSpot sandbox.
5. Conditional human-approval gate — low-confidence cases are routed to a human reviewer instead of
   auto-actioned; high-confidence cases proceed automatically.
6. Notification — the outcome (auto-processed, or awaiting review) is surfaced to the relevant user.
7. Observability logging — every stage's decision, confidence, and outcome is persisted per lead for
   the monitoring view and the benchmark report.

## Feature Tiers
Must-Have:
- Multi-step pipeline (parse → classify → enrich → CRM write → approval gate → notify) with each stage
  holding genuinely separate, non-overlapping tool access and independent state.
- Idempotent, retry-safe CRM write operations against HubSpot's real free-tier developer sandbox
  (real auth, real rate limits — not a mock).
- Human-review/approval path for low-confidence classifications — no silent auto-action on uncertain
  cases.
- Observability/monitoring view showing each stage's decision, confidence, and outcome per processed
  lead.

Nice-to-Have:
- A reported, honestly-measured classification accuracy/consistency benchmark view (including failure
  cases, not cherry-picked successes).
- Notification delivery beyond in-app (e.g. email/Slack-style alert on a routed-for-review case).
- Per-lead audit/history trail in the UI (full stage-by-stage timeline, not just the current state).

Advanced/Future:
- Multi-Agent Orchestration stretch goal (explicitly deferred this round per the source specification's
  adversarial resolution — do not re-add mid-build).
- Swappable CRM interface allowing a second, paid CRM platform to be substituted without an
  architecture rewrite.
- Multi-channel intake beyond web/email/callback (e.g. SMS, chat widget).

## Technical Direction
Frontend: React — the observability/monitoring view and human-review queue require a real UI, not just
API responses; matches this developer's existing stack pattern.
Backend: FastAPI (this developer's proven pattern) with an explicit orchestration layer (e.g. LangGraph
or an equivalent lightweight state-machine orchestrator) coordinating the distinct pipeline stages —
not one large prompt.
Database: PostgreSQL (or SQLite for local dev) — persists lead records, per-stage processing traces,
and benchmark results.
Integrations: HubSpot free-tier developer sandbox (real CRM integration target); a locally-run
open-weight LLM (e.g. via Ollama) for classification/enrichment decisions, with a free-tier hosted LLM
API as an explicit, optional fallback only if local tool-calling proves insufficiently reliable for
consistent classification (conditional exception, not a default dependency).
Document Processing: NONE — lead records are short structured/semi-structured text, not documents the
product is built around; this is not a document-Q&A, contract-analysis, or RAG-shaped workflow.

## Constraints & Assumptions
Constraints:
- Full stack runs free by default (no paid CRM tier, no paid vector database); any paid LLM API use is
  an optional, explicitly-justified fallback only.
- The Multi-Agent Orchestration stretch goal is out of scope for this round — resist re-adding it
  mid-build to keep scope disciplined.
- The per-stage tool/state boundary must be architecturally real under code inspection, not cosmetic —
  the single most important constraint to hold throughout implementation (an adversarial audit flagged
  this as the Critical risk in the source specification).

Assumptions:
- HubSpot's free developer sandbox provides sufficient real auth/rate-limit behavior to demonstrate
  genuine external-system integration; its actual behavior should be verified against the real sandbox
  early rather than deferred to the end.
- Local open-weight LLM tool-calling reliability is unproven going in for this developer — the required
  accuracy benchmark exists specifically to measure this rather than assume it.
- Demand for this exact sub-pattern (lead intake triage specifically, vs. agentic workflow automation
  generally) is inferred from a broader, well-evidenced market category rather than independently
  confirmed — an accepted, explicitly-carried risk, not a hidden one.

## Ready for Roadmap?
YES
The specification (sourced from Portfolio Intelligence Round 1, Verdict: READY) is complete, specific,
and adversarially pressure-tested — every required section above has concrete content, no placeholder
language, and the differentiation/technical-depth requirements are load-bearing rather than optional
polish.

## Concept Quality (metrics — new in v20.0)
problem_usefulness: 7/10, confidence: MEDIUM — the manual lead-triage problem is concretely named with
supporting market figures (109% YoY AI-hiring growth, ~60% of new enterprise AI projects including an
agentic component), but demand for this specific sub-pattern (vs. agentic automation generally) is
inferred, not independently confirmed, per the source specification's own honestly-stated risk.
technical_depth_potential: 9/10, confidence: MEDIUM — genuine multi-stage tool/state separation,
idempotent external writes, and a measured accuracy benchmark are real technical depth; MEDIUM because
local-LLM tool-calling reliability is unproven for this developer going in.
portfolio_value_potential: 8/10, confidence: MEDIUM — closes the #1-ranked, HIGH-priority Agentic
Workflow Automation gap and extends an already-demonstrated backend/CRM pattern rather than starting
from zero; sits above the High-ROI menu's commodity CRUD tier (e.g. #4 CRM & Lead Pipeline) toward the
AI-differentiated tier, though not as maximal as a from-scratch novel category would score.
differentiation_potential: 7/10, confidence: MEDIUM — lead-triage/CRM-update agents are a commonly-cited
2026 example use case, risking a tutorial-shape read (flagged explicitly by the source specification's
adversarial audit); the differentiator is execution rigor (real sandbox, idempotency, measured
benchmark, genuinely real agent boundaries), not novel problem framing.
