SCOPE EXPANSION
================

Round: 1
Date: 2026-09-05

Trigger: Explicit user request ("run scope expansion") — overrides the same-day Dynamic Next-Action
Selection session that concluded NO_ACTION (per `.claude/pipeline-reference.md`, twenty-eighth session),
per the Master Prompt's "an explicit Suggestion still wins" rule. That NO_ACTION conclusion was correct
on its own terms (no *discovered* gap forced an operation) — it does not mean no valuable net-new
capability exists; ideation has no honest-zero exit condition (§9), so an explicit ask is always a valid
trigger independent of that conclusion.

Inputs read: `project-definition.md`, `roadmap.md` (all 3 tiers), `.claude/portfolio-reference.md`
(Architecture Map + Key Decisions), `refinement-audit.md`, `portfolio-evaluation.md`. No
`product-expansion-map.md` (PRODUCT-mode only; this project is STANDARD) or prior `scope-expansion.md`
existed before this round.

CANDIDATES (this round)

- S-01 Failed-Run Retry / Resubmission: Value: High | Cost: Low-Medium | Priority: P1 | Status: Shipped (Feature 16, 2026-09-06)
  Today a `FAILED` `PipelineRun` (e.g. a HubSpot write exhausting its retries) is a permanent dead end —
  the UI can show that it failed, but nothing lets anyone act on it short of manually recreating the lead
  from scratch. This is genuinely new: no roadmap tier mentions retry, and it's distinct from Feature 06's
  human-review resume path (that resumes a *paused*, not a *failed*, run). It's also architecturally
  anticipated rather than speculative — `.claude/portfolio-reference.md`'s Key Decisions already states
  `PipelineRun.lead_id` was deliberately left non-unique "so multi-attempt history stays representable if
  a future feature ever adds a retry/resubmit path." Mechanically it reuses Feature 06's existing
  resume-graph abstraction (a second compiled graph re-entering at the failed stage, using the same
  `Stage`/`ToolRegistry` instances) rather than inventing a new execution path. New surface: one endpoint
  (`POST /leads/{lead_id}/retry`) and a "Retry" action on `LeadDetailPage.tsx`'s existing failed-state
  banner. Strengthens the project's core "reliable multi-step action, not just answer questions" value
  proposition — "what happens when it fails" is exactly the production-readiness question a real client
  would ask next.

- S-02 Confidence-Threshold "What-If" Simulator: Value: High | Cost: Medium | Priority: P1 | Status: Shipped (Feature 17, 2026-09-06)
  Ties two systems that already exist but have never been connected: the benchmark harness's 22-item
  labeled dataset (`BenchmarkCase`, with a per-item confidence score already persisted) and the live
  `CONFIDENCE_THRESHOLD` setting that gates auto-processing vs. human review. Nothing today lets anyone
  see how many labeled leads would land on each side of a *candidate* threshold before changing the real
  setting. This is a genuinely new capability, not a restatement of Tier 2's existing Benchmark Report
  (which measures accuracy/consistency at the *current* threshold, not threshold sensitivity) — and it
  directly demonstrates a "human-AI collaboration tuning" story the market rewards, per
  `project-definition.md`'s own differentiation framing. Cost is contained: no new external integration,
  a new derived endpoint computing the auto/review split from a benchmark run's already-stored per-case
  confidence values, and one new panel (a threshold slider plus resulting counts) on `BenchmarkPage.tsx`.

- S-03 Aggregate Lead Funnel & Reviewer Throughput Dashboard: Value: High | Cost: Medium | Priority: P2 | Status: Not Started
  `project-definition.md`'s Use Case 4 already names a "sales manager" persona wanting to see pipeline
  performance, but the existing Observability view (`LeadListPage.tsx`/`LeadDetailPage.tsx`) only answers
  "what happened to this one lead" — nothing answers "how is the whole pipeline performing": conversion
  rate by source channel, average time-to-resolution, review-queue throughput per reviewer. This is a
  distinct question from every existing page, not a restyle of one. Cost is a pure read-path aggregation
  over data the project already persists (`PipelineRun`, `ReviewQueueItem`) — no new write paths, no new
  external integration, one new backend endpoint plus one new frontend page.

- S-04 Interactive Slack Review Actions: Value: Medium-High | Cost: Medium-High | Priority: P2 | Status: Not Started
  Feature 10 (External Notification Delivery, Tier 2) already delivers a one-way Slack-compatible webhook
  alert when a lead reaches `awaiting_review`. This candidate closes the loop — approve/reject/edit
  directly from Slack's interactive-message buttons — so a reviewer never has to leave Slack to act. It's
  the natural next chapter of an already-shipped feature, not a duplicate of it (Feature 10 only ever
  sends; this receives). Cost is higher than the other candidates because it's the only one requiring a
  new *inbound* trust boundary: a Slack interactive-component callback endpoint with request-signature
  verification, wired to the existing `POST /reviews/{run_id}/action` logic underneath (no new business
  logic, just a new authenticated entry point to it).

- S-05 Exportable Per-Lead / Date-Range Audit Trail (CSV): Value: Medium | Cost: Low | Priority: P3 | Status: Not Started
  A compliance/audit artifact — "give me a document of everything that happened to this lead" — is a
  common enterprise ask around AI-driven CRM actions and costs little to add: it reuses
  `GET /leads/{lead_id}/history`'s already-merged timeline data verbatim. One new export endpoint (CSV;
  PDF would be a further, separate stretch) and an "Export" button on `LeadHistoryPage.tsx`. Lower
  priority than S-01 through S-04 since it adds credibility polish rather than closing a functional gap.

DECLINED / REJECTED

- Multi-Agent Orchestration, Swappable CRM Interface, Multi-Channel Intake Expansion: not proposed here —
  all three are already `roadmap.md` Tier 3 items. Multi-Agent Orchestration is explicitly, deliberately
  deferred per the source specification's adversarial resolution ("do not re-add mid-build" —
  `.claude/portfolio-reference.md`'s Project Overview restates this). The other two are undecided-future
  roadmap items, not undiscovered gaps. Per §5, redirected to Continual Refinement's Dimension 1 (fidelity
  to the existing plan) rather than duplicated here — Dimension 1 already re-confirmed this exact status
  as recently as `refinement-audit.md`'s own record.
- Bulk/batch review-queue actions (approve/reject several queued items at once): considered, but declined
  this round — `.claude/portfolio-reference.md`'s Key Decisions frames the review queue as an
  architecturally single-operator workflow (no auth/User model, self-reported `reviewer_name` only); at
  that scale, batch tooling solves a volume problem this project doesn't yet have. Revisit if a future
  round's data shows queue volume growing past what one-at-a-time review comfortably handles.

TIE-BREAK DECISION (S-01 vs. S-02, both P1)
Asked the user directly which to pursue first, per §4's tie-break rule. Answer: both, in sequence — S-01
(Failed-Run Retry) goes into CD-1 first; S-02 (What-If Simulator) follows as its own CD round immediately
after, not deferred to a future Scope Expansion round. Status below updated to reflect S-01 entering CD-1
this session.

- S-01: Status: Shipped (2026-09-06) — Feature 16, Failed-Run Retry/Resubmission. CD-1 through CD-4
  all complete; see `.claude/validation-results.md`'s 2026-09-06 entry.
- S-02: Status: Shipped (2026-09-06) — Feature 17, Confidence-Threshold "What-If" Simulator. CD-1
  through CD-4 all complete, same session immediately after S-01, per the user's "both" confirmation.

NEXT ROUND (thirty-first session, 2026-09-06)
Trigger: `docs/next-action-selection.md`'s Dynamic Next-Action Selection ran per idle Step 2 (no
Suggestion, zero OPEN backlog entries, no CD round queued). Evidence favored UI Audit & Refinement
(Feature 17's expanded panel was left visually UNVERIFIED last session, and browser automation is now
confirmed available in this environment) — offered first, user explicitly chose Scope Expansion instead
to continue S-03/S-04.

TIE-BREAK DECISION (S-03 vs. S-04, both P2)
Per §4's tie-break rule, asked the user directly which to pursue first. Answer: both, in sequence — S-03
(Aggregate Lead Funnel & Reviewer Throughput Dashboard) goes into CD-1 first; S-04 (Interactive Slack
Review Actions) follows as its own CD round immediately after, same pattern as the S-01/S-02 round.

- S-03: Status: Shipped (2026-09-06) — Feature 18, Aggregate Lead Funnel & Reviewer Throughput
  Dashboard. CD-1 through CD-4 all complete, live-verified against real accumulated data and
  visually confirmed with real browser automation at all four target viewports; see
  `.claude/validation-results.md`'s CD-4 entry.
- S-04: Status: In Progress — entering CD-1 this session as Feature 19, per the user's "both, in
  sequence" answer.

NEXT ROUND
Once S-03/S-04 ship, all 5 of this round's candidates will be resolved except S-05 (P3, CSV export),
still available but not selected this round. A future idle session should run `docs/next-
action-selection.md`'s Dynamic Next-Action Selection rather than defaulting straight back to another
Scope Expansion round — the UI Audit & Refinement gap flagged above (Feature 17's panel, and now
Feature 18/19's own UI surfaces) should be weighed then too.
