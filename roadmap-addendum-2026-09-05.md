ROADMAP ADDENDUM — 2026-09-05
==============================

**Round type:** Continued Development (`docs/continued-development.md`), CD-1. Genuinely new
capability (a new backend endpoint plus a new UI action on an existing page), not a deepening of an
existing feature — CD-2 spec required.

## Why this round exists

`docs/scope-expansion.md`'s Scope Expander, Round 1 (2026-09-05, run at the user's explicit request),
proposed S-01 (Failed-Run Retry/Resubmission) as a P1 candidate: today a `PipelineRun` that reaches
`RunStatus.FAILED` (e.g. a HubSpot write exhausting its retries, per Feature 05's Key Decision on
raising vs. continuing) is a permanent dead end — `LeadDetailPage.tsx`'s failed-state banner shows that
it failed, but nothing lets a user act on it short of manually recreating the lead submission from
scratch. This is architecturally anticipated, not speculative: `.claude/portfolio-reference.md`'s Key
Decisions already states `PipelineRun.lead_id` was deliberately left non-unique "so multi-attempt
history stays representable if a future feature ever adds a retry/resubmit path" (set by Feature 11's
implementation plan). No roadmap tier (`roadmap.md`) ever named this — it's genuinely new, not a
restatement of Feature 06's human-review resume (that resumes a *paused*, not a *failed*, run) or
Feature 11's history view (that only displays past attempts, never lets you start a new one).

S-01 and S-02 (a confidence-threshold what-if simulator) tied at P1 in that round; asked the user
directly which to pursue first per `docs/scope-expansion.md` §4's tie-break rule — chose "both, in
sequence," S-01 first.

## New feature added

**Feature 16: Failed-Run Retry / Resubmission** (Tier: addendum — a Tier 1-completion item extending
the existing pipeline-execution/human-review resume machinery to a third terminal state; not part of
the original 14-feature roadmap's Tier 1-3 sequencing, added post-hoc per this addendum).

- **Depends on:** Feature 01 (Pipeline Orchestration Layer — the `Stage`/`ToolRegistry`/graph-compile
  machinery this reuses), Feature 06 (Human Review & Approval Gate — the existing resume-graph pattern:
  a second, smaller compiled graph starting at a named stage, re-entering the same `Stage` instances
  rather than a bespoke router-level code path), Feature 11 (Per-Lead Audit/History Trail — the
  `PipelineRun.lead_id` non-uniqueness Key Decision this feature is the first to actually exercise).
- **Backend:** one new endpoint, `POST /leads/{lead_id}/retry` — locates the lead's most recent `FAILED`
  `PipelineRun`, re-enters the compiled graph at the failed stage using the same resume-graph
  construction Feature 06 established (never a bespoke tool call from the router layer, per the existing
  Key Decision governing that pattern), and produces either a new `PipelineRun` row or a resumed
  execution of the existing one — CD-2.5 decides which, consistent with how the codebase already
  represents "another attempt at this lead."
- **Frontend:** a "Retry" action on `LeadDetailPage.tsx`'s existing failed-state banner, calling the new
  endpoint and refreshing the page's stage-trace timeline on success.
- **Not a new external integration** — no new tool binding, no new third-party system; this is
  orchestration-layer plumbing reusing existing tool registrations exactly as they're already scoped.

See `implementation_plan.md`'s Feature 16 entry (CD-2) for the full spec, and
`architecture-plan-feature-16.md` (CD-2.5) for the implementation plan.

## Scope boundary note

Per `docs/continued-development.md`'s "Multiple Rounds" section, this addition falling outside the
original Step 1 scope boundaries (a 14-feature, 3-tier roadmap that never named a retry capability) is
not a reason to decline it — it documents why scope is growing: a real gap between what the
architecture already anticipated (the non-unique `lead_id` Key Decision) and what the product actually
lets a user do, surfaced by this session's Scope Expansion round rather than by a client ask.

## Queued next round

Per `scope-expansion.md`'s tie-break decision, S-02 (Confidence-Threshold What-If Simulator) is queued
as its own CD round immediately after this one ships — not deferred to a future Scope Expansion round.
