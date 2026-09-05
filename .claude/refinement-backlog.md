# Refinement Backlog — [PROJECT_NAME]

Persistent, cross-round record of every actionable finding `docs/continual-refinement.md`'s audit loop
has produced. Distinct from `refinement-audit.md` (project root): that file is the historical, per-round
score record; this file is the current, individually-addressable view of unresolved (and resolved) work.
Full schema and lifecycle rules: `docs/continual-refinement.md`'s "Persistent Refinement Backlog" section
— don't restate the rules here, just follow them.

**Read by:** the Master Prompt's Step 0/Step 2, whenever this file exists — an `OPEN`/`IN_PROGRESS`
entry is existing project work, not a new suggestion to independently rediscover.
**Written by:** any Continual Refinement round — every actionable finding gets an entry the same session
it's found, not only the findings that round implements.

---

## Backlog

[Append-only, ordered by ID. Never delete an entry — mark it `COMPLETED` or `DEFERRED` instead. Never
renumber.]

### RB-001 — Flaky notification-ordering test
- **Status:** OPEN
- **Dimension:** 6 (Testing/Reliability, per `docs/continual-refinement.md`'s Eight Dimensions)
- **Priority:** P3
- **Discovered:** Step 6 (Group_F08, Feature 08), 2026-09-04 — not a Continual Refinement round, but
  logged here per the same backlog mechanism since it surfaced mid-implementation and is out of scope
  for the group that found it.
- **Finding:** `backend/app/tests/test_router_notifications.py::test_list_notifications_returns_
  newest_first` fails intermittently (observed 2 failures in 5 reruns in isolation) — it asserts
  `GET /notifications` returns rows ordered by `created_at` descending, but two `Notification` rows
  created back-to-back in the same test can land on the same (or out-of-order) timestamp on this
  platform's clock resolution, making the assertion's expected order nondeterministic.
- **Rationale / Evidence:** Reproduced by re-running the single test in isolation 5 times (2 failed, 3
  passed) — unrelated to any Feature 08 change (Feature 08 touches no file this test or the
  `notifications` router depends on). Not a regression introduced this round; pre-existing since
  Feature 07 (`architecture-plan-feature-07.md`).
- **Routes to:** A scoped Step 6→7 re-entry against `backend/app/routers/notifications.py`'s query
  (add a stable tiebreaker, e.g. `ORDER BY created_at DESC, id DESC`, or the test fixture (assign
  strictly increasing timestamps to the two seeded notifications instead of relying on wall-clock
  ordering) — per `docs/continual-refinement.md`'s routing table for a contained, single-file
  correctness fix.
- **Implementation notes:** (blank — not yet actioned)
