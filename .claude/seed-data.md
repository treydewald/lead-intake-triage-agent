# Seed Data — Lead Intake Triage Agent

The realistic dataset this project's screenshots were captured against — entity names, counts, and
field values, as a plain fixture list, not an executable script. Written by `prompts/10_screenshot-
capture.md`'s Step 6.8 the first time it constructs data for capture; read back by that same step (and
by Step 11/12 or a Continual Refinement round) so a later session reconstructs the *same* dataset
deterministically instead of reverse-engineering it by pixel-inspecting committed screenshots. Full
spec: `docs/claude-directory-spec.md`'s `seed-data.md` entry.

**Update this file whenever the seeded data changes materially** — a new entity type, a renamed field,
a different data volume. A stale fixture list is worse than none: it looks authoritative but no longer
matches what the screenshots actually show.

---

## Entities

### Leads / Pipeline Runs (`PipelineRun` + `Lead`)
- **Regenerated 2026-09-06** (Continued Development — CRM Write Simulated-Success Fallback,
  deepens Feature 05): the prior 30-lead dataset (below, kept for history) was ~89% `failed`
  because every run hit the unconfigured-HubSpot-token halt at `hubspot_crm_write`. That's fixed
  now — `hubspot_tools.write_contact` returns a `status="simulated"` success instead of raising
  when no token is configured — so the dataset was wiped (old `backend/leads.db` backed up to
  `backend/leads.db.pre-simulated-write-backup-2026-09-06`, gitignored either way) and rebuilt from
  scratch by submitting 16 real leads through the live fixed pipeline (`backend/app/benchmark/
  dataset.py`'s buyer/browser/spam message pool, 13 of them; 3 ambiguous/ near-boundary messages
  for the review-queue examples), using the same disposable-second-`uvicorn`-instance technique
  documented below to reliably land 3 of them in Human Review.
- **Current count: 18 pipeline runs.** Status mix: 16 `COMPLETED` (13 auto-processed at
  `CONFIDENCE_THRESHOLD=0.7` + 1 approved-from-review), 1 `AWAITING_REVIEW` (the current pending
  review item, below), 1 `REJECTED`. Every `COMPLETED` run's `hubspot_crm_write` stage trace shows
  `write_status: "simulated"` (surfaced in the UI as an amber "Simulated write — no live HubSpot
  token configured" note on `LeadDetailPage.tsx`) — an honest label, not a claim of a real CRM
  write. Field values: `source_channel: "web_form"`; names/emails are ad hoc
  (`name: "Morgan Ellis"`, `email: "morgan.ellis@example.com"`, etc.), 3 leads deliberately given a
  generic `name: "no-reply"` for the spam cases.
- **Superseded note (prior dataset, 2026-09-04 through 2026-09-06):** 30 leads accumulated
  organically across every session's live end-to-end testing since Step 6. Status mix: 1
  `awaiting_review`, ~26 `failed`, ~2 `rejected`. The heavy `failed` skew was expected and
  documented at the time, not a bug: `HUBSPOT_ACCESS_TOKEN` was intentionally left unconfigured in
  this dev environment, so every run reaching `hubspot_crm_write` halted there by the
  architecture's then-current "halt on write failure" design (QA-1 made this a clear
  `HubSpotWriteError` message rather than a leaked transport exception). Superseded by the
  simulated-write fallback above — kept here only as a historical record of what the dataset
  looked like before that fix.

### Review Queue item (`ReviewQueueItem`)
- **Regenerated 2026-09-06** (Continued Development — CRM Write Simulated-Success Fallback, same
  round as the Leads/Pipeline Runs reset above — the whole DB was wiped, so this item is new too,
  not merely refreshed): produced using this file's own documented disposable-second-instance
  technique. Three near-boundary messages were submitted against a `CONFIDENCE_THRESHOLD=0.95`
  disposable instance (port 8001) to force them below threshold: `name: "Harper Lin"` (confidence
  0.79, draft `browser`) and `name: "Skyler Voss"` (confidence 0.766, draft `browser`) were actioned
  through the main port-8000 server — Harper approved (now `COMPLETED`, simulated CRM write), Skyler
  rejected (`REJECTED`) — populating the Review Queue's "Recently Processed" panel with one of each
  outcome. A third, `name: "Quinn Ashby"` (`message_body: "Hi, saw your product online, might be a
  fit for us but I am mostly just comparing options right now."`), was left `PENDING` as the
  dataset's current `awaiting_review` item.
- Count: 1 `PENDING` item (Quinn Ashby) + 2 `ACTIONED` (Harper Lin approved, Skyler Voss rejected).
- **Superseded note (prior dataset, through 2026-09-06):** see the Leads/Pipeline Runs section above
  — the entire DB predating the simulated-write fallback (including this section's own prior
  Jordan Reyes / 7b0d3af5 entries) was backed up to
  `backend/leads.db.pre-simulated-write-backup-2026-09-06` and superseded, not merged forward.
- How it was produced (general technique, reusable): the real local `llama3.2:3b` model is prone to
  classifying short, plausible-buyer messages above the default `CONFIDENCE_THRESHOLD=0.7` even when
  the message reads as ambiguous to a human — to reliably get a fresh `awaiting_review` row without
  touching the running dev server's config, start a second, disposable `uvicorn` instance on a spare
  port against the same SQLite file with a temporarily raised `CONFIDENCE_THRESHOLD` (0.90-0.95) set
  only in that process's environment, submit one webform lead, confirm `AWAITING_REVIEW`, then stop
  the instance immediately. No `.env` file is ever edited.

### Benchmark Runs (`BenchmarkRun` + `BenchmarkCase`)
- **Regenerated 2026-09-06** (Continued Development — CRM Write Simulated-Success Fallback round):
  the DB wipe above also cleared prior benchmark runs, and this round's classification-prompt fix
  (tighter buyer-vs-browser label definitions + few-shot examples in `ollama_tools._SYSTEM_PROMPT`)
  needed a fresh run to prove it actually worked, not a stale one. Triggered `POST /benchmark/run`
  with `repeats=3` against the real local `llama3.2:3b` model (~140s response time observed, run
  fully in the background).
- Count: 1. **Result: 100.0% accuracy / 95.5% consistency** (up from the pre-fix baseline of ~87%
  accuracy — itself later found on the same day to only be genuinely reproducing at ~83% — and 90.9%
  consistency). Every buyer/browser/spam case (18 of 22) classified correctly; the 4 `ambiguous`
  cases (no ground-truth label, excluded from accuracy) include 3 correctly landing on `browser` at
  0.72-0.77 confidence and one ("Okay thanks.", case `ambiguous-004`) that still produces a genuine
  `classification_failed` (confidence 0.0, no label) — an expected, pre-existing edge case for
  near-content-free text, not a regression from this round. Confidence values now range 0.72-0.90
  across every case, with every *correct* classification's confidence continuous and non-clustered
  (no repeats at the old fake-looking 0.80/0.85/0.90 round numbers) — see
  `.claude/portfolio-reference.md`'s Key Decisions on `confidence_scoring.py` for why.
- **Superseded note (prior dataset, through 2026-09-06):** 2 runs, most recent showing 87.0%
  accuracy / 90.9% consistency, with 3 misclassified `browser→buyer` cases driving the confusion
  this round's prompt fix targeted directly. Superseded, not merged forward — see the Leads/Pipeline
  Runs section above for the same DB-wipe context.

---

## How it was seeded

No bulk seed script exists for this project (documented gap — a future session could add
`backend/scripts/seed.py` if repeated fresh-environment setup becomes common). All data above
accumulated through real usage: live end-to-end pipeline runs during Steps 6-9's own verification
work, plus one additional webform submission this session (via a disposable second `uvicorn`
instance, see above) specifically to produce a fresh `awaiting_review` row for capture. Nothing was
inserted directly into the database — every row passed through the real orchestrator pipeline.

**2026-09-06 full reset (CRM Write Simulated-Success Fallback round):** `backend/leads.db` backed up
to `backend/leads.db.pre-simulated-write-backup-2026-09-06` (gitignored, local only) and recreated
via `alembic upgrade head`. 16 leads submitted through the live fixed pipeline on the main port-8000
server (13 from `backend/app/benchmark/dataset.py`'s buyer/browser/spam pool, 1 verification lead,
2 more ambiguous messages that still auto-processed), plus 3 near-boundary leads submitted to a
disposable `CONFIDENCE_THRESHOLD=0.95` second instance on port 8001 to reliably land in Human
Review — 2 of those then actioned (1 approved, 1 rejected) via the main server, 1 left pending. One
fresh `POST /benchmark/run` (`repeats=3`) triggered on the main server. Every row passed through the
real orchestrator pipeline and a real Ollama call; nothing was inserted directly into the database.
