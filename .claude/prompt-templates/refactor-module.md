# Prompt Template: Refactor Module

Fill in the blanks; see `docs/token-discipline.md` §2.

```
Refactor [module/file] to [specific goal — e.g. "extract duplicated validation logic"] without
changing external behavior.

Scope: [specific file(s)] only.
Constraint: no behavior change — validate with [existing test suite / specific manual check]
before and after.
Log: append to .claude/execution-log.md when done.
```
