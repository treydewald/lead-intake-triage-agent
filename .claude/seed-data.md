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
- **Regenerated 2026-09-06** (UI Audit & Refinement — full-app pass, Round 1): the prior item (lead
  `7b0d3af5`) was consumed by Feature 19's own live verification (see the superseded note below,
  kept for history). A fresh `awaiting_review` item was produced using the exact same disposable-
  second-instance technique this file already documented: a second `uvicorn` instance on port 8001
  against the same `backend/leads.db` file, `CONFIDENCE_THRESHOLD=0.95` set only in that process's
  environment (main port-8000 server and its `.env` untouched), one webform lead submitted
  (`name: "Jordan Reyes"`, `email: "jordan.reyes@example.com"`,
  `message_body: "Hey, saw your post about the service, not totally sure if this is what I need but
  figured Id ask what it costs"`), landing as `AWAITING_REVIEW` (lead `b5a847c8-99fb-49f0-9d5f-
  1005cea70d0e`, run `86dee829-132a-4f09-9aec-5740ca8a8f67`, draft classification `buyer`,
  confidence 0.80). The disposable instance was stopped immediately after (`taskkill /F` on its
  PID); the main server picked up the new row via the shared DB file on its next `GET /reviews`
  call, confirmed live. This is the current `awaiting_review` item used for `05-review-queue.png`
  and `06-review-detail.png` in this round's re-capture.
- Count: 1 `awaiting_review` item at capture time (lead `b5a847c8`, draft classification `buyer`,
  confidence 0.80).
- **Superseded note (2026-09-06, Feature 19's CD-4 live verification):** the prior `awaiting_review`
  item (lead `7b0d3af5`, confidence 0.90) was approved via a real, correctly-signed
  `POST /slack/interactions` call against a disposable second `uvicorn` instance (port 8001, same
  `leads.db` file, `SLACK_SIGNING_SECRET` set only in that process's environment) — deliberately
  chosen as the most valuable verification available (a real signature, a real queued lead, a real
  resume through the orchestrator) over a synthetic example. This consumed the queue down to empty,
  which is why the regeneration above was needed for this round's screenshot capture.
- How it was produced (general technique, reusable): the real local `llama3.2:3b` model is prone to
  classifying short, plausible-buyer messages above the default `CONFIDENCE_THRESHOLD=0.7` even when
  the message reads as ambiguous to a human — to reliably get a fresh `awaiting_review` row without
  touching the running dev server's config, start a second, disposable `uvicorn` instance on a spare
  port against the same SQLite file with a temporarily raised `CONFIDENCE_THRESHOLD` (0.90-0.95) set
  only in that process's environment, submit one webform lead, confirm `AWAITING_REVIEW`, then stop
  the instance immediately. No `.env` file is ever edited.

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
