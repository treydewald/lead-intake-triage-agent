ROADMAP ADDENDUM — 2026-09-06 (Round 2)
========================================

**Round type:** Continued Development (`docs/continued-development.md`), CD-1. Genuinely new
capability (a new backend endpoint plus a new, nav-linked frontend page), not a deepening of an
existing feature — CD-2 spec required.

## Why this round exists

`docs/next-action-selection.md`'s Dynamic Next-Action Selection ran at Step 2 (idle: no Suggestion,
zero `OPEN` backlog entries, no CD round queued). Evidence favored UI Audit & Refinement (Feature
17's expanded panel was left visually `UNVERIFIED` last session), but offered to the user first per
the selection procedure's mandatory confirmation step, the user explicitly chose to continue Scope
Expansion instead — specifically S-03/S-04, the two P2 candidates left over from `scope-expansion.md`
Round 1 (2026-09-05) after both P1s (S-01/S-02) shipped as Features 16/17.

Per that round's own tie-break rule (S-03 vs. S-04, both P2), asked the user directly which to
pursue first. Answer: both, in sequence — S-03 first, then S-04 — same pattern as the S-01/S-02
round.

`project-definition.md`'s Use Case 4 already names a "sales manager" persona wanting to see pipeline
performance, but every existing page answers "what happened to this one lead" (`LeadListPage.tsx`/
`LeadDetailPage.tsx`) or "how accurate is classification at a point in time" (`BenchmarkPage.tsx`) —
nothing answers "how is the whole pipeline performing across every lead": conversion rate by source
channel, average time-to-resolution, review-queue throughput per reviewer. This is a genuinely new
question, not a restyle of an existing page.

## New feature added

**Feature 18: Aggregate Lead Funnel & Reviewer Throughput Dashboard** (Tier: addendum — not part of
the original 14-feature roadmap's Tier 1-3 sequencing, added post-hoc per this addendum; proposed by
`docs/scope-expansion.md`'s Scope Expander, Round 1, S-03).

- **Depends on:** Feature 08 (`PipelineRun`'s denormalized `source_channel`/`confidence_score`
  columns this reuses verbatim), Feature 06 (`ReviewQueueItem`, whose `reviewer_name`/`actioned_at`
  this reads for throughput).
- **Backend:** one new read-only endpoint, `GET /analytics/funnel`, computing every number below by
  querying existing `PipelineRun`/`ReviewQueueItem` rows directly — no new columns, no new tables, no
  new write path, no new external integration.
- **Frontend:** a new page, `FunnelDashboardPage.tsx`, at a new persistent nav route (`/analytics`) —
  unlike `LeadHistoryPage.tsx`/`ReviewDetailPage.tsx` (reached only via a link from a parent page),
  this page answers a standalone question a sales-manager persona would navigate to directly, so it
  earns its own `Layout.tsx` nav entry. Also linked from `HomePage.tsx`'s existing section-card grid,
  per this project's established in-app-cohesion pattern (RB-004).
- **Not a new external integration, not a new data model** — this is the purest "read-path
  aggregation over data the project already persists" candidate from `scope-expansion.md` Round 1.

See `implementation_plan.md`'s Feature 18 entry (CD-2) for the full spec, and
`architecture-plan-feature-18.md` (CD-2.5) for the implementation plan.

## Scope boundary note

Per `docs/continued-development.md`'s "Multiple Rounds" section, this addition falling outside the
original Step 1 scope boundaries is not a reason to decline it — it documents why scope is growing:
`scope-expansion.md`'s own Round 1 already identified and prioritized this exact gap (S-03, P2).

## Queued next round

S-04 (Interactive Slack Review Actions) follows Feature 18 in this same session, per the user's
"both, in sequence" tie-break answer — see `scope-expansion.md`'s updated tie-break record. S-05
(Exportable Audit Trail CSV, P3) remains available but not selected this round.
