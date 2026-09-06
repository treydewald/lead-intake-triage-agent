ROADMAP ADDENDUM — 2026-09-06
==============================

**Round type:** Continued Development (`docs/continued-development.md`), CD-1. Genuinely new
capability (a new backend endpoint plus a new, connected UI panel), not a deepening of an existing
feature — CD-2 spec required.

## Why this round exists

`docs/scope-expansion.md`'s Scope Expander, Round 1 (2026-09-05), proposed S-02 (Confidence-
Threshold "What-If" Simulator) as a P1 candidate, tied with S-01 (Failed-Run Retry/Resubmission,
shipped as Feature 16 on 2026-09-06). Per that round's tie-break decision ("both, in sequence — S-01
first"), S-02 is this round's work, immediately after Feature 16 shipped, in the same session per
the user's explicit "both" confirmation.

Today two systems exist independently but have never been connected: Feature 09's benchmark harness
(a 22-item labeled dataset with a per-case confidence score already persisted) and the live
`CONFIDENCE_THRESHOLD` setting that gates auto-processing vs. human review (Feature 06). Nothing
today lets anyone see how many labeled leads would land on each side of a *candidate* threshold
before actually changing the real setting — a genuinely new capability, not a restatement of Tier
2's existing Benchmark Report (which measures accuracy/consistency at the *current* threshold, not
threshold sensitivity).

## New feature added

**Feature 17: Confidence-Threshold "What-If" Simulator** (Tier: addendum — connects two existing
Tier 1/Tier 2 systems that were never wired together; not part of the original 14-feature roadmap's
Tier 1-3 sequencing, added post-hoc per this addendum).

- **Depends on:** Feature 06 (the live `CONFIDENCE_THRESHOLD` setting this simulates against),
  Feature 09 (the benchmark dataset/per-case confidence values this reuses verbatim).
- **Backend:** one new read-only endpoint, `GET /benchmark/confidence-threshold`, exposing the
  live `Settings.confidence_threshold` value — nothing today exposes any config to the frontend, and
  this is the one non-sensitive value the simulator needs to show a "current" baseline. No new
  simulation-computation endpoint (see CD-2.5's Existing Systems Analysis for why the originally-
  proposed "derived endpoint computing the auto/review split" turned out to be unnecessary
  duplication once the actual data shape was checked).
- **Frontend:** a collapsible "Threshold Simulator" panel on `BenchmarkPage.tsx` — a slider over a
  candidate confidence threshold, live-recomputing (client-side, from data the page already has)
  how many of the current run's cases would land on each side of that candidate threshold, versus
  the live current threshold.
- **Not a new external integration** — no new tool binding, no new third-party system; this connects
  two already-shipped, already-tested systems' existing data.

See `implementation_plan.md`'s Feature 17 entry (CD-2) for the full spec, and
`architecture-plan-feature-17.md` (CD-2.5) for the implementation plan.

## Scope boundary note

Per `docs/continued-development.md`'s "Multiple Rounds" section, this addition falling outside the
original Step 1 scope boundaries is not a reason to decline it — it documents why scope is growing:
`scope-expansion.md`'s own Round 1 already identified and prioritized this exact gap.

## Queued next round

None forced. Per `scope-expansion.md`'s own "NEXT ROUND" note, a natural future candidate once both
P1s (S-01, S-02) have shipped is extending this simulator into a live "preview this threshold
against real pending reviews" view — not committed to here, left for a future Scope Expansion or
Continual Refinement round to actually prioritize.
