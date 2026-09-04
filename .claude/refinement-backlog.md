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
renumber. Example entry shape below — replace with real findings as Continual Refinement rounds produce
them; delete the example once the first real entry is added.]

### RB-001 — [Short title]
- **Status:** OPEN
- **Dimension:** [1-8, per `docs/continual-refinement.md`'s Eight Dimensions]
- **Priority:** P1 / P2 / P3
- **Discovered:** Round [N], [YYYY-MM-DD]
- **Finding:** [1-3 sentences, specific enough that a future session recognizes it without re-reading
  the round that found it]
- **Rationale / Evidence:** [why this matters; what was actually observed]
- **Routes to:** [pipeline mechanism, copied verbatim from `docs/continual-refinement.md`'s Routing
  Table — never invented here]
- **Implementation notes:** [blank until the entry moves off OPEN; then what changed, which round/commit
  closed it, or why it was deferred]
