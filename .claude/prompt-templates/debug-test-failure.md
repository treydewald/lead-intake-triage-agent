# Prompt Template: Debug Test Failure

Fill in the blanks; see `docs/token-discipline.md` §2.

```
Test [test name] fails with: [exact error/output].

Diagnose the root cause — check [suspected file(s)] first, but don't assume the cause without
confirming.
Fix: apply the minimal targeted correction, not a surrounding rewrite.
Re-verify: re-run [test name] (and any test likely affected by the same code path) to confirm.
Log: append the result to .claude/validation-results.md.
```
