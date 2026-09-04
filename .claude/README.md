# templates/claude-dir/ — Per-Project `.claude/` Scaffold Source

Everything in this directory is copied verbatim (with placeholders filled in) into a new portfolio
project's own `.claude/` directory by `prompts/04_environment-bootstrap.md`, or backfilled by
`prompts/05_workspace-recovery.md` if a recovered project doesn't have one yet.

Full spec of what each file is for, who writes it, and when it's updated: `docs/claude-directory-spec.md`.

Do not hand-edit a project's copy of these files expecting changes to propagate back here — this
is the source; a project's `.claude/PIPELINE-SYNC.md` tracks which version it was copied from.
