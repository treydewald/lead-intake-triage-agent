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
- Count: 30 at Step 10 capture time, accumulated organically across every session's live
  end-to-end testing since Step 6 (no bulk seed script — see "How it was seeded" below).
- Status mix visible in the captured screenshots: 1 `awaiting_review`, ~26 `failed`, ~2 `rejected`.
  The heavy `failed` skew is expected and documented, not a bug: `HUBSPOT_ACCESS_TOKEN` is
  intentionally left unconfigured in this dev environment (see `.claude/pipeline-reference.md`'s
  Deviations section — creating a real HubSpot sandbox token is a manual, out-of-band step), so
  every run that reaches the `hubspot_crm_write` stage halts there by the architecture's own
  "halt on write failure" design (QA-1 made this a clear `HubSpotWriteError` message rather than a
  leaked transport exception).
- Field values used: `source_channel: "web_form"` for all captured leads;
  `message_body` values drawn from `backend/app/benchmark/dataset.py`'s existing case pool (e.g.
  `"Is this still available?"`, `"Hi, I saw your product online..."`) plus ad hoc names/emails
  (e.g. `name: "Morgan Ellis"`, `email: "morgan.ellis@example.com"`).

### Review Queue item (`ReviewQueueItem`)
- **Consumed 2026-09-06** (Feature 19's CD-4 live verification): the one `awaiting_review` item
  described below (lead `7b0d3af5`) was approved via a real, correctly-signed
  `POST /slack/interactions` call against a disposable second `uvicorn` instance (port 8001, same
  `leads.db` file, `SLACK_SIGNING_SECRET` set only in that process's environment) — deliberately
  chosen as the most valuable verification available (a real signature, a real queued lead, a real
  resume through the orchestrator) over a synthetic example, following the exact same "disposable
  second instance against the same DB file" technique this file already documents below. The review
  queue is now empty; a future Step 10/11/12 or Continual Refinement session capturing fresh
  Review Queue screenshots needs to regenerate a new `awaiting_review` item first, using the same
  technique (a webform submission through a disposable instance with a raised `CONFIDENCE_THRESHOLD`).
- Count: 1 `awaiting_review` item at capture time (lead `7b0d3af5`, draft classification `buyer`,
  confidence 0.90), used for both `05-review-queue.png` and `06-review-detail.png`.
- Why a fresh one was needed: both real pending items from Step 9's live QA testing were consumed
  during that session's Approve/Reject verification (see `qa-report.md`'s Final Verdict note) —
  the queue was empty going into this step.
- How it was produced: the real local `llama3.2:3b` model proved consistently overconfident on
  short ambiguous test messages against the default `CONFIDENCE_THRESHOLD=0.7` (same finding as
  Feature 15's own build session) — a plain webform submission of `"Is this still available?"`
  classified with confidence 0.90, above threshold, and routed straight to `hubspot_crm_write`
  instead of pausing for review. To get a real `awaiting_review` row without touching the running
  dev server's config, a second, disposable `uvicorn` instance was started on port 8001 against the
  same SQLite file (`backend/leads.db`) with `CONFIDENCE_THRESHOLD=0.95` set only in that process's
  environment, one webform lead (`name: "Morgan Ellis"`) was submitted through it, and the instance
  was stopped immediately after. The main dev server (port 8000, `CONFIDENCE_THRESHOLD=0.7`,
  untouched) picked up the new row on its next query since it's the same database file. No `.env`
  file was edited.

### Benchmark Runs (`BenchmarkRun` + `BenchmarkCase`)
- Count: 2, both pre-existing from prior sessions' live runs against the real local `llama3.2:3b`
  model (Feature 09's own build session, 2026-09-05) — not created by this Step 10 session.
  `07-benchmark.png` shows the most recent one: 87.0% accuracy / 90.9% consistency, 22 cases × 3
  repeats, with its Failure & Ambiguous Cases table (4 ambiguous, 3 misclassified `browser→buyer`).
  No new benchmark run needed to be triggered for capture — real historical data was already
  present and representative.

---

## How it was seeded

No bulk seed script exists for this project (documented gap — a future session could add
`backend/scripts/seed.py` if repeated fresh-environment setup becomes common). All data above
accumulated through real usage: live end-to-end pipeline runs during Steps 6-9's own verification
work, plus one additional webform submission this session (via a disposable second `uvicorn`
instance, see above) specifically to produce a fresh `awaiting_review` row for capture. Nothing was
inserted directly into the database — every row passed through the real orchestrator pipeline.
