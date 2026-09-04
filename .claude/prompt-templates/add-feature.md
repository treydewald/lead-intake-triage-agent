# Prompt Template: Add Feature

Fill in the blanks; see `docs/token-discipline.md` §2.

```
Add [narrow, specific behavior] to [file/module].

Scope: touch only [specific file(s)/function(s)] — do not refactor surrounding code.
Reference: `.claude/portfolio-reference.md` for architecture context before reading source.
Validate: [the specific check that proves this works — a test, a manual repro step]
Log: append to .claude/execution-log.md when done.
```
