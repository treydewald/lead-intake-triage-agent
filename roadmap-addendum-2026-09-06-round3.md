ROADMAP ADDENDUM — 2026-09-06 (Round 3)
========================================

**Round type:** Continued Development (`docs/continued-development.md`), CD-1. Genuinely new
capability (a new inbound HTTP trust boundary plus a new outbound payload shape), not a deepening of
an existing feature — CD-2 spec required.

## Why this round exists

Per `scope-expansion.md`'s Round 1 tie-break decision (S-03 vs. S-04, both P2): "both, in sequence —
S-03 first." Feature 18 (S-03, Aggregate Lead Funnel & Reviewer Throughput Dashboard) shipped
immediately before this round in the same session. This round is S-04.

Feature 10 (External Notification Delivery) already delivers a one-way Slack-compatible webhook
alert when a lead reaches `awaiting_review` — but it only sends. A reviewer who sees that alert still
has to leave Slack, open this app's Review Queue, and act there. This candidate closes the loop:
approve/reject directly from Slack's own interactive-message buttons, so the alert and the action
live in the same place.

## New feature added

**Feature 19: Interactive Slack Review Actions** (Tier: addendum — not part of the original
14-feature roadmap's Tier 1-3 sequencing, added post-hoc per this addendum; proposed by
`docs/scope-expansion.md`'s Scope Expander, Round 1, S-04).

- **Depends on:** Feature 06 (`ReviewQueueItem`/the resume-graph action logic this reuses), Feature
  10 (the existing outbound webhook this extends with interactive buttons), Feature 11
  (`reviewer_name`, the same self-reported-identity field this reuses for Slack-originated actions).
- **Backend:** one new inbound endpoint, `POST /slack/interactions`, verifying Slack's own
  request-signature scheme (HMAC-SHA256 over `v0:{timestamp}:{raw body}`, keyed by an operator-
  configured `SLACK_SIGNING_SECRET`) before trusting anything in the payload — this is the one
  candidate in `scope-expansion.md`'s Round 1 requiring a new *inbound* trust boundary, not just a
  new outbound call or a new read path. `deliver_webhook_notification()` (Feature 10) gains an
  optional interactive-buttons payload (Slack Block Kit `actions` block: Approve/Reject, each
  carrying the run id) so the message a reviewer already receives is the same message they act from —
  without this change, the new inbound endpoint would exist with nothing in Slack ever actually
  linking to it.
- **Scope decision (see architecture-plan-feature-19.md for full reasoning):** Slack's simple button
  interactions carry only a fixed `action_id`/`value` pair — there is no text-input surface without
  building a full Slack *modal* flow (a second, much larger OAuth/`trigger_id` round-trip). This round
  ships **approve/reject only** via buttons; "edit" (which requires a corrected label as free text) is
  explicitly deferred, not silently dropped — a future round could add it via a Slack modal if this
  becomes a real client need.
- **Reuses, not duplicates:** the exact same review-action logic `POST /reviews/{run_id}/action`
  already implements (concurrency-safe atomic claim, resume-graph re-entry, reject-path notification)
  is extracted into a shared function both the existing HTTP endpoint and the new Slack endpoint call
  — Slack is a second caller of one action, not a second implementation of it.
- **Not a new data model** — no new columns, no new tables; `reviewer_name` (Feature 11) receives the
  Slack username, exactly as it already receives a self-reported name from the web UI.

See `implementation_plan.md`'s Feature 19 entry (CD-2) for the full spec, and
`architecture-plan-feature-19.md` (CD-2.5) for the implementation plan.

## Scope boundary note

Per `docs/continued-development.md`'s "Multiple Rounds" section, this addition falling outside the
original Step 1 scope boundaries is not a reason to decline it — it documents why scope is growing:
`scope-expansion.md`'s own Round 1 already identified and prioritized this exact gap (S-04, P2).

## A note on live verification limits

This project has no live Slack workspace/app to test against, the same category of limitation
Feature 05's real HubSpot sandbox write already established a precedent for (a placeholder token
still proves the mechanism, even though the write itself can't succeed in this dev environment). The
signature-verification logic itself is pure cryptography (HMAC-SHA256) and is fully, deterministically
testable without any live Slack service — this round tests that exhaustively. What cannot be
live-verified is a real Slack workspace actually delivering a real button click to this endpoint;
that gap is recorded honestly in `architecture-plan-feature-19.md`, not silently assumed away.

## Queued next round

All 5 candidates from `scope-expansion.md`'s Round 1 will be resolved except S-05 (Exportable Audit
Trail CSV, P3) once this round ships. A future idle session should run `docs/next-action-
selection.md`'s Dynamic Next-Action Selection rather than defaulting straight back to another Scope
Expansion round — the UI Audit & Refinement gap flagged at this round's own start (Feature 17's
panel, still `UNVERIFIED` from its own session) should be weighed then, now that Features 18/19 have
both demonstrated working browser automation is available.
