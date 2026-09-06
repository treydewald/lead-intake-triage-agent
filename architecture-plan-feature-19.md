IMPLEMENTATION PLAN
====================

Feature / Round: Feature 19 (Interactive Slack Review Actions)
Classification: New feature, Security improvement (a new inbound trust boundary), Cross-system
integration (extends Feature 10's outbound payload to carry Feature 06's action logic back inbound)
Planning Depth: Deep — a new inbound trust boundary (Slack request-signature verification) is
security-sensitive per this doc's own Planning Depth table, even though it touches only 2-3 existing
systems; this gets full scrutiny on the Existing Systems Analysis and Risk sections rather than the
lighter Standard treatment Feature 18 received.

Objective
Close the loop on Feature 10's one-way Slack delivery: let a reviewer approve or reject a lead
directly from the interactive buttons on the Slack message they already receive, verified as
genuinely originating from Slack before any state changes, using the exact same action logic the
existing web UI already uses.

Existing Systems Analysis
- Reusable: `POST /reviews/{run_id}/action`'s existing logic (`routers/reviews.py`) — concurrency-
  safe atomic claim, resume-graph re-entry via `resume_pipeline()`, the reject-path notification call
  — is the entire business logic this feature needs; Slack is a second *caller*, never a second
  *implementation*. `ReviewQueueItem.reviewer_name` (Feature 11) — already exists specifically for
  self-reported identity with no auth model; a Slack username is exactly the same shape of value the
  web UI's "Your name" field already populates it with, no new field needed.
  `deliver_webhook_notification()` (Feature 10) — the existing outbound delivery path; extending it
  (not replacing it) is how the interactive buttons actually reach a real Slack message. The existing
  "never raises, returns status as data" contract for outbound delivery is unaffected — this feature
  only adds an optional payload field.
- Duplication Risk Flagged: **the obvious wrong move here is writing a second, parallel
  "approve/reject a review" implementation inside the new Slack router** — same shape of mistake this
  project's own Key Decisions already warn against elsewhere (e.g. "never a second parallel tool
  binding for the same external system," Feature 09). Resolution: extract `action_review`'s body into
  `orchestrator/review_actions.py::apply_review_action()`; both `routers/reviews.py` and the new
  `routers/slack.py` call it. Verified no behavior change by re-running `test_router_reviews.py`
  unmodified after the extraction.
- Modify: `routers/reviews.py` (`action_review` becomes a thin wrapper), `orchestrator/graph.py`
  (pass `run_id` to the delivery call), `orchestrator/tools/webhook_tools.py` (optional interactive-
  buttons payload), `core/config.py`/`backend/.env.example` (new setting), `main.py` (router
  registration).
- New: `orchestrator/review_actions.py` (the extracted shared function — belongs in `orchestrator/`
  alongside `graph.py`/the stages, not in either router module, since it's domain logic two different
  transport-layer routers call, not HTTP-specific itself). `routers/slack.py` — a new router is
  justified because Slack's payload shape (form-encoded, signature-verified, Slack's own JSON
  envelope) is a completely different contract from `reviews.py`'s own `ReviewActionRequest`/
  `ReviewQueueItemOut` Pydantic schemas; forcing it into `reviews.py` would make that router
  responsible for parsing two unrelated request formats.
  **Where does signature verification itself live?** Not under `orchestrator/tools/` — that
  directory's own Key Decision scopes it to "tool bindings... registered into `ToolRegistry`," and
  signature verification is inbound request authentication invoked by a router before any Stage or
  tool is ever reached, a genuinely different concern. It's defined directly in `routers/slack.py` as
  a small, pure, independently-testable function (`verify_slack_signature()`) — not promoted to its
  own package for one ten-line function (per this project's own "don't build infrastructure ahead of
  a second real need" discipline), but kept as a standalone function specifically so it can be unit-
  tested with self-computed HMACs, independent of the FastAPI request/response cycle.
- Navigation Relationships Flagged: none — this feature has no frontend surface at all (a Slack
  message is the only UI it produces, entirely outside this project's own React app).

System Impact Map

FEATURE 19 — Interactive Slack Review Actions
│
├── Frontend
│   └── none — no UI surface in this project's own app
│
├── Backend
│   ├── `orchestrator/review_actions.py` — new `apply_review_action()`, extracted from
│   │     `routers/reviews.py`
│   ├── `routers/slack.py` — new `POST /slack/interactions` + `verify_slack_signature()`
│   ├── `routers/reviews.py` — `action_review` becomes a thin wrapper
│   ├── `orchestrator/tools/webhook_tools.py` — optional interactive-buttons payload
│   ├── `orchestrator/graph.py` — passes `run_id` through to the delivery call
│   ├── `core/config.py` — new `slack_signing_secret` setting
│   ├── `main.py` — registers the new router
│
├── Database
│   └── none added
│
├── Existing Systems (reused, not duplicated)
│   ├── `POST /reviews/{run_id}/action`'s action logic (now shared via `apply_review_action()`)
│   ├── `ReviewQueueItem.reviewer_name` (Feature 11)
│   ├── `deliver_webhook_notification()`'s existing never-raises delivery contract (Feature 10)
│
├── Navigation
│   └── N/A — no frontend surface
│
└── AI
    └── N/A — no AI integration; this feature only routes an already-made human decision

Implementation Order (Dependency Graph)

`apply_review_action()` (extracted from existing logic) → `routers/reviews.py` re-wired to call it
  (regression check) → `verify_slack_signature()` (new, independent) → `POST /slack/interactions`
  (depends on both) → `deliver_webhook_notification()`'s interactive-buttons payload (independent of
  the above, but only meaningful once the endpoint exists to receive clicks) → `graph.py` wiring
  (depends on the payload change)

1. **`apply_review_action()`** (`orchestrator/review_actions.py`) — purpose: single source of truth
   for "act on a review," callable from any transport. Existing files affected: `routers/reviews.py`
   (its `action_review` body moves here, replaced with a thin wrapper). New files:
   `review_actions.py`. Dependencies: none beyond what `action_review` already imported.
   Requirements: identical behavior to the current `action_review` — same `HTTPException`s (422 for
   edit-without-label, 404 for missing item, 409 for already-actioned), same atomic-claim mechanism,
   same resume-graph re-entry. Validation: `test_router_reviews.py` (existing, unmodified) must still
   pass in full — this is the regression gate proving the extraction changed nothing observable.

2. **`verify_slack_signature()`** (`routers/slack.py`) — purpose: pure HMAC-SHA256 verification,
   independent of any live request. Existing files affected: none. New files: `routers/slack.py` (this
   function plus the endpoint), `tests/test_slack_signature.py`. Dependencies: stdlib `hmac`/
   `hashlib`/`time` only. Requirements: `v0={hmac_sha256(secret, f"v0:{timestamp}:{body}")}` compared
   via `hmac.compare_digest` (constant-time, never `==`); reject if `|now - timestamp| > 300` seconds
   (replay protection); reject if the secret is empty/`None`. Validation: self-computed valid
   signature accepted; a byte-flipped signature rejected; a >5-minute-old timestamp rejected even with
   an otherwise-correct signature; an empty secret always rejects.

3. **`POST /slack/interactions`** (`routers/slack.py`) — purpose: the inbound endpoint itself.
   Existing files affected: `main.py` (registration). New files: `tests/
   test_router_slack_interactions.py`. Dependencies: steps 1-2. Requirements: read the raw body via
   `await request.body()` *before* any parsing (signature covers the exact raw bytes); verify via step
   2, `401` on failure, before touching the body's contents at all; parse the `payload` form field as
   JSON; map `action_id` (`approve_lead`→`approve`, `reject_lead`→`reject`, anything else→`400`); call
   step 1 with the mapped action, the button's `value` as `run_id`, and `user.username` as
   `reviewer_name`; catch `HTTPException` from step 1 for the 404/409 business-outcome cases and
   return `200` with an explanatory `text` body instead of propagating the raw status (per this
   feature's edge-case requirements — Slack retries non-2xx responses, which would misfire against an
   already-idempotent claim). Validation: end-to-end test with a real computed signature covering
   approve, reject, already-actioned, nonexistent-run, unrecognized-action_id, bad-signature, stale-
   timestamp, and no-secret-configured cases.

4. **`deliver_webhook_notification()` interactive-buttons payload** (`webhook_tools.py`) — purpose:
   make the outbound message Slack receives actually carry buttons pointing at step 3. Existing files
   affected: `webhook_tools.py`, `graph.py` (pass `run_id=state.run.run_id`),
   `tests/test_webhook_tools.py`. New files: none. Dependencies: none functionally (this could ship
   independently of steps 1-3), but is meaningless without them — sequenced last so the endpoint it
   points at already exists. Requirements: `run_id: str | None = None` new optional parameter; when
   provided, add a Slack Block Kit `blocks` array (a `section` mirroring the existing `text`, plus an
   `actions` block with Approve/Reject buttons, `value=run_id`); when omitted, payload shape is
   byte-for-byte unchanged from today (existing tests must pass with zero modification). Validation:
   existing `test_webhook_tools.py` tests pass unmodified (no `run_id` passed); one new test asserts
   the `blocks` array's exact shape when `run_id` is passed.

Architecture Rule Changes
- [ ] **Proposed:** "Domain logic reachable from more than one transport-layer entry point (an HTTP
  router, a Slack/webhook callback, a future CLI or scheduled job) lives in `app/orchestrator/`,
  written as a plain function each router calls — never duplicated per-transport, and never left
  inside the first router that happened to need it." Conflict check: no existing Key Decision
  addresses multi-transport reuse directly; this generalizes the existing "reuse at the Python
  function level" pattern (Feature 05's `write_contact`/`search_contact` reuse) to a new trigger
  (a second *inbound* transport, not just a second internal caller) — complementary, not
  contradictory. Feature 19 is the first feature with two transport-layer entry points into the same
  action, so this is a genuinely new, durable rule worth stating now rather than waiting for a third
  transport to force the question.

Feature-Specific Requirements
- "Edit" via Slack is explicitly out of scope for this round — a plain button click's `value` is a
  fixed string (the run id), with no text-input surface; supporting edit would require a Slack
  *modal* (a `trigger_id`-based `views.open` round-trip, a second, materially larger integration this
  round does not build). This is a documented scope decision, not an oversight.
- Slack's own interactive-component contract requires a `200` response within 3 seconds; this
  endpoint's synchronous call into `apply_review_action()` (which can invoke `resume_pipeline()` and
  therefore a real HubSpot write attempt) must stay fast enough in practice — acceptable for this
  project's scale (the same synchronous-write pattern `POST /reviews/{run_id}/action` already uses
  today with no reported latency issue), not re-architected into an async job queue for this round.

Risks
- Risk: an unconfigured or leaked `SLACK_SIGNING_SECRET` lets a forged request act on a real review.
  Mitigation: fail closed (any missing/invalid signature or unconfigured secret rejects with `401`
  before parsing anything); `hmac.compare_digest` used instead of `==` to avoid a timing side-channel;
  the secret itself is never logged, echoed, or included in any response body, error message, or the
  `Notification` table (same "never leak a configured secret/URL" discipline Feature 10's own Key
  Decision already established for `notification_webhook_url`).
- Risk: a replayed (captured-and-resent) valid request re-triggers an action. Mitigation: the
  5-minute timestamp window (Slack's own recommended practice) bounds the replay window, and
  `apply_review_action()`'s existing atomic claim makes a replay of an *already-actioned* review a
  no-op 200 response regardless — two independent layers of protection, not just one.
- Risk: this feature cannot be live-verified against a real Slack workspace in this environment (no
  Slack app/workspace credentials available, the same category of gap Feature 05's real-HubSpot-write
  verification already established a precedent for handling honestly). Mitigation: the cryptographic
  core (`verify_slack_signature()`) is fully, deterministically testable without any live service —
  this round tests it exhaustively — and the action-routing logic is proven identical to the
  already-live-verified `POST /reviews/{run_id}/action` path via the shared-function extraction. What
  remains genuinely unverified — a real Slack workspace actually delivering a real click — is recorded
  honestly here, not silently assumed to work.

Acceptance Criteria
- [ ] All acceptance criteria already stated in `implementation_plan.md`'s Feature 19 spec
- [ ] `test_router_reviews.py` passes unmodified after the `apply_review_action()` extraction (proves
  zero behavior change to the existing, already-live-verified HTTP path)
- [ ] A forged signature, a stale timestamp, and an unconfigured secret are all provably rejected
  *before* any `ReviewQueueItem` row is read or modified (asserted directly in tests, not just "the
  response was 401")

Validation Requirements
- CD-4 must confirm the extraction is behavior-preserving by running the full existing
  `test_router_reviews.py` suite unmodified, not just the new Slack-specific tests
- CD-4 must record, explicitly and honestly, that live verification against a real Slack workspace is
  not possible in this environment — same treatment as Feature 05's HubSpot write limitation — rather
  than silently omitting the caveat

Predicted Footprint
Files predicted to change: 10 (`orchestrator/review_actions.py`, `routers/slack.py`,
`tests/test_slack_signature.py`, `tests/test_router_slack_interactions.py`, `core/config.py`,
`backend/.env.example`, `orchestrator/tools/webhook_tools.py`, `orchestrator/graph.py`,
`routers/reviews.py`, `main.py`, `tests/test_webhook_tools.py`, plus this plan's own Actual Footprint
appendix — 11 including the appendix)
Systems predicted to touch: reviews router/action logic, new Slack router, webhook delivery, graph
notification call site, settings

--- filled in later, by Step 7 / CD-4, once implementation is verified ---
Actual Footprint
Files actually changed: 11 — exactly as predicted: `backend/app/orchestrator/review_actions.py`,
`backend/app/routers/slack.py`, `backend/app/tests/test_slack_signature.py`,
`backend/app/tests/test_router_slack_interactions.py`, `backend/app/core/config.py`,
`backend/.env.example`, `backend/app/orchestrator/tools/webhook_tools.py`,
`backend/app/orchestrator/graph.py`, `backend/app/routers/reviews.py`, `backend/main.py`,
`backend/app/tests/test_webhook_tools.py`, plus this plan's own Actual Footprint appendix.
Deviations from plan: none.
Rework required: none. Full backend suite 171/171 passed (was 154/154 — +17 new tests), including
`test_router_reviews.py` passing completely unmodified after the `apply_review_action()` extraction —
the regression gate this plan's own Implementation Order step 1 required. Coverage held at 98%
(unchanged). No frontend files touched (this feature has no UI surface); frontend suite/build/lint
not re-run since nothing in `frontend/` changed.

**Live verification against the real running backend and the real accumulated dev database**
(deliberately chosen over a purely mocked test — see below):
1. A forged signature (wrong secret) and a stale (10-minute-old) timestamp were both rejected with a
   real `401` from a live HTTP call, confirmed via the real `GET /reviews` endpoint that the targeted
   review-queue item was untouched by either attempt.
2. A real, correctly-signed `POST /slack/interactions` request — computed the same way a genuine
   Slack app would (HMAC-SHA256 over `v0:{timestamp}:{raw body}`) — approved the project's one real
   `awaiting_review` item (lead `7b0d3af5`, per `.claude/seed-data.md`) end-to-end: `GET /reviews`
   went from 1 item to empty, and `GET /leads/{lead_id}` showed the run had resumed through the real
   orchestrator into `hubspot_crm_write`, failing there for the expected, already-documented reason
   (no `HUBSPOT_ACCESS_TOKEN` configured in this dev environment — the same limitation Feature 05's
   own live verification first established). `reviewer_name` was correctly recorded as the Slack
   username from the payload's `user.username` field.
3. A second identical click against the now-actioned item returned `200` with an "already actioned"
   explanatory message, not a raw `409` — confirming the Slack-facing error-translation behavior this
   plan's System Behaviors section required.
4. Verified via a disposable second `uvicorn` instance (port 8001, same `leads.db` file,
   `SLACK_SIGNING_SECRET` set only in that process's environment) — the exact technique
   `.claude/seed-data.md` already documents for producing/consuming real data without disturbing the
   main dev server's configuration. `.claude/seed-data.md` updated to record the consumption.

**What remains genuinely unverified, recorded honestly per this plan's own Validation Requirements:**
a real Slack workspace/app actually delivering a real button click to this endpoint was not tested —
no Slack app credentials are available in this environment. Everything this endpoint does *after*
receiving Slack's documented request shape was verified live against real data; only Slack's own
delivery of that shape was not, the same category of limitation Feature 05's HubSpot-write
verification already established a precedent for stating plainly rather than glossing over.
