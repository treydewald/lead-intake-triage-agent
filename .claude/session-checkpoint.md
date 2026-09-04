_(This file only exists when a session has handed off mid-task — see `docs/token-discipline.md` §6.
Once consumed by the resuming session, rename it to `session-checkpoint-archive-<date>.md` rather
than deleting it.)_

# Session Checkpoint — [PROJECT_NAME]

**Written:** [TIMESTAMP]

## Completed
[Steps/plan items finished, files modified, commit hashes if any]

## Remaining
[The rest of the original plan]

## Validation State
[Anything pending or blocked — cross-reference `.claude/validation-results.md`]

## Usage State at Checkpoint
[Which limit type triggered this checkpoint — session / weekly / monthly — and which threshold from
`docs/token-discipline.md` §6 was crossed. E.g.: "Session — covered 5 of 6 plan steps plus three large
file rewrites." See `docs/token-discipline.md` §6 for the full auditability requirement.]

## Resume With
[The exact next prompt to paste into a fresh chat]

## Recommended Model
[Per `.claude/model-strategy.md`, for the next step specifically]
