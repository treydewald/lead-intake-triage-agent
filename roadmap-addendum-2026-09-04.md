ROADMAP ADDENDUM — 2026-09-04
==============================

**Round type:** Continued Development (`docs/continued-development.md`), CD-1. Genuinely new
capability (a new frontend route/UI surface), not a deepening of an existing feature — CD-2 spec
required.

## Why this round exists

Step 7 (Implementation Verification, Gate 2, 2026-09-04) found that `frontend/src/components/
Layout.tsx`'s sidebar has shipped a "Review Queue" nav item since Step 4's bootstrap scaffold, but no
route named `review` has ever been registered — navigating to it renders a completely blank page.
Logged as `.claude/refinement-backlog.md`'s RB-002. The backend routes this UI would consume
(`GET /reviews`, `GET /reviews/{run_id}`, `POST /reviews/{run_id}/action`) have worked correctly since
Feature 06 and are already covered by Feature 06's own tests plus Step 7's live verification of the
approve path.

RB-002's own "Routes to" note named two options: remove the dead nav link, or build the real page
against the already-working backend. Asked directly this session — the user chose to build the page
(the backend has supported this entire workflow since Feature 06; removing the link would throw that
existing capability away rather than surface it).

## New feature added

**Feature 15: Review Queue Frontend UI** (Tier: addendum — functionally a Tier 1/2-boundary
completion item, since it exposes a Tier 1 backend capability (Feature 06) that shipped with no
frontend of its own; not part of the original 14-feature roadmap's Tier 1-3 sequencing, added post-hoc
per this addendum).

- **Depends on:** Feature 06 (Human Review & Approval Gate — the backend routes), Feature 08
  (Observability / Monitoring View — established the frontend page/routing/API-client conventions this
  feature reuses).
- **Not a new backend capability** — zero backend files change. This is scoped entirely to
  `frontend/src/` plus `frontend/src/lib/api.ts`'s typed client additions.

See `implementation_plan.md`'s Feature 15 entry (CD-2) for the full spec, and
`architecture-plan-feature-15.md` (CD-2.5) for the implementation plan.

## Scope boundary note

Per `docs/continued-development.md`'s "Multiple Rounds" section, this addition falling outside the
original Step 1 scope boundaries (a 14-feature, 3-tier roadmap that never named a Review Queue UI) is
not a reason to decline it — it documents why scope is growing: a real gap between what the backend
supports and what the UI exposes, found by verification rather than invented.
