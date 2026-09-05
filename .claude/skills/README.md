# Skills / Slash-Command Registry — Lead Intake Triage Agent

Project-specific skills or slash commands this project's Claude sessions can invoke by name.
Most portfolio projects use only the pipeline's own numbered prompts and need nothing here —
register an entry only if this project has a genuinely reusable, project-specific workflow that
doesn't already correspond to one of the 16 pipeline steps.

| Name | Purpose | Invocation |
|---|---|---|
| `capture-screenshots.mjs` | Launches the app in a real Chromium instance (via `playwright-core`) and navigates every portfolio route through real in-app link clicks (not `page.goto`), saving PNGs to `./portfolio-screenshots/`. Covers Home, Lead List, Lead Detail, Lead History, Review Queue, Review Detail, Benchmark (desktop 1920×1080) plus Home and Lead List at mobile 390×844. Extend in place for new routes rather than writing a new script. | `cd frontend && node ../.claude/skills/capture-screenshots.mjs` (must run with cwd = `frontend/` so `playwright-core` resolves; requires both dev servers running) |
