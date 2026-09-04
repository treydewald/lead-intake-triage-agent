# Model Strategy — Lead Intake Triage Agent

**Last Updated:** 2026-09-04

Full rationale: `docs/token-discipline.md` §8. Use the smallest capable model for each task;
reserve the largest for irreplaceable reasoning.

| Task | Model | Why |
|---|---|---|
| Plan generation (Step 3, `docs/plan-execute-review.md` Plan Phase) | Opus | Architectural judgment, hard to correct cheaply if wrong |
| Code review / Gate 2 / Gate 1 (Steps 7, 13) | Opus | Needs to catch what the implementer missed |
| Feature implementation (Step 6 Execute phase) | Sonnet | Standard scoped development work |
| Test writing, refactoring, docs (Steps 8, 9, 14) | Sonnet | Medium-complexity, well-specified |
| Lint/format fixes, validation re-runs | Haiku | Mechanical, low-judgment |
| Reference-doc updates (`.claude/portfolio-reference.md` changelog entries) | Haiku | Routine transcription |
| Screenshot cleanup (Step 10) | Haiku | File management, no judgment calls |

**Escalation rule:** if a Haiku-tier task's output needs judgment it wasn't given, escalate to
Sonnet/Opus rather than iterating at the lower tier — note the escalation in
`.claude/validation-results.md`.
