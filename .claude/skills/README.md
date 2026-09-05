# Skills / Slash-Command Registry — Lead Intake Triage Agent

Project-specific skills or slash commands this project's Claude sessions can invoke by name.
Most portfolio projects use only the pipeline's own numbered prompts and need nothing here —
register an entry only if this project has a genuinely reusable, project-specific workflow that
doesn't already correspond to one of the 16 pipeline steps.

| Name | Purpose | Invocation |
|---|---|---|
| `capture-screenshots.mjs` | Launches the app in a real Chromium instance (via `playwright-core`) and navigates every portfolio route through real in-app link clicks (not `page.goto`), saving PNGs to `./portfolio-screenshots/`. Covers Home, Lead List, Lead Detail, Lead History, Review Queue, Review Detail, Benchmark (desktop 1920×1080) plus Home and Lead List at mobile 390×844. Extend in place for new routes rather than writing a new script. | `cd frontend && node ../.claude/skills/capture-screenshots.mjs` (must run with cwd = `frontend/` so `playwright-core` resolves; requires both dev servers running) |
| `measure-page-whitespace.py` | Introduced Step 11 Round 5 (2026-09-05) to replace visual estimation of "empty space below content" with a reproducible measurement: scans each screenshot from the bottom row up until a row's colors stop matching the page background (`bg-slate-50`), excluding the persistent left sidebar (desktop only, x<240px — a real bug in the first version, see `portfolio-evaluation.md`'s Round 5 Step 12 batch notes) and the bottom-right "Updated" timestamp watermark. Reused by Step 12 Round 5 to verify the whitespace-gap fix (all 7 desktop pages: 30-57% → 2-3% empty). Any future composition/whitespace claim in this project's Step 11 or Step 12 rounds should use this script rather than eyeballing a percentage. | `python .claude/skills/measure-page-whitespace.py ./portfolio-screenshots` (requires Pillow; run against desktop 1920×1080 screenshots for the sidebar-exclusion logic to apply correctly) |
