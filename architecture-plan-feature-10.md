IMPLEMENTATION PLAN
====================

Feature / Round: Feature 10 (External Notification Delivery)
Classification: Feature expansion, Backend change, Cross-system integration
Planning Depth: Standard — one new external system (a generic Slack-compatible incoming webhook) and a
schema change, but the extension point (`persist_outcome_notification()`) already exists and was named
explicitly by Feature 07's own Key Decision; no new Stage, no state-machine/graph edge change, no new
frontend surface.

Objective
Deliver a best-effort external (webhook) alert alongside the existing in-app `Notification` whenever a
lead lands in `awaiting_review` — the one outcome where a reviewer not actively watching the app most
needs a push — without ever blocking, retrying indefinitely, or affecting the underlying pipeline run.

Existing Systems Analysis
- Reusable: `app/orchestrator/graph.py`'s `persist_outcome_notification()` (Feature 07) — the exact
  extension point `.claude/portfolio-reference.md`'s Key Decisions already named in advance ("Feature 10
  ... extends `persist_outcome_notification()` and its three direct call sites, not a new parallel
  notification mechanism"). All three existing call sites (`_make_node`'s except block,
  `_make_human_review_node`, `reviews.py`'s reject branch) already wrap the whole call in
  `try/except: pass`, so a defensive-safe extension inside the helper needs zero call-site signature
  changes. Also reusable: the `app/orchestrator/tools/` one-module-per-external-system convention
  (`hubspot_tools.py`'s shape), `Settings`/`.env.example`'s existing config pattern, and `Notification`
  (Feature 07) as the row external delivery status attaches to.
- Duplication Risk Flagged: none found — grep-confirmed no email/webhook/delivery code exists anywhere
  in the codebase yet, and no logging framework is configured anywhere in `backend/app` to duplicate
  (`import logging` matches zero files) — a DB-column status, not ambient log output, is this project's
  only existing "durable record" pattern for outcome events.
- Modify: `app/models/notification.py` (two new nullable columns), `app/core/config.py` +
  `backend/.env.example` (one new setting), `app/orchestrator/graph.py`'s `persist_outcome_notification()`
  (the delivery call, gated to the `awaiting_review` outcome only), `app/schemas/notification.py`'s
  `NotificationOut` (surface the two new fields on the existing `GET /notifications` response — no new
  endpoint).
- New: `app/orchestrator/tools/webhook_tools.py` — nothing existing does an outbound HTTP POST to an
  operator-configured destination; this is a genuinely new external system (distinct from HubSpot/Ollama).
- Navigation Relationships Flagged: none found — this feature adds no new UI screen or route; the
  existing `/reviews/{run_id}` `detail_link` convention (Feature 07) is reused unchanged inside the
  webhook payload.

System Impact Map
```
backend/
  app/
    core/config.py                          [MODIFY] + notification_webhook_url setting
    models/notification.py                  [MODIFY] + external_delivery_status/_error columns
    orchestrator/
      tools/webhook_tools.py                [NEW] deliver_webhook_notification() — never raises
      graph.py                              [MODIFY] persist_outcome_notification() delivery hook
    schemas/notification.py                 [MODIFY] NotificationOut + 2 fields
  alembic/versions/<new>_add_notification_delivery_columns.py  [NEW]
  .env.example                              [MODIFY] + NOTIFICATION_WEBHOOK_URL
```
(No `frontend/` branch — Feature 10 has no UI requirement of its own; existing `GET /notifications`
consumers see the new fields automatically via response-model extension.)

Implementation Order (Dependency Graph)
1. `app/models/notification.py` — add `external_delivery_status: Mapped[str | None]` (`"sent" |
   "failed" | "skipped"`) and `external_delivery_error: Mapped[str | None]`, both nullable. | Existing
   files: `notification.py`. | New: none. | Dependencies: none. | Requirement: columns nullable so
   every pre-existing `Notification` row (Features 07/08/09/15's own notifications) remains valid.
   | Validation: model imports and existing `test_router_notifications.py` fixtures still construct
   rows without passing the new fields.
2. Alembic migration adding those two columns to the `notification` table. | Existing: none touched
   beyond the migration chain. | New: one revision file, `down_revision` = the current head
   (`5f3cbe979b96_*`). | Dependencies: step 1. | Validation: `alembic upgrade head` succeeds on the dev
   SQLite DB with existing rows intact.
3. `app/core/config.py` — add `notification_webhook_url: str | None = None`; `backend/.env.example` —
   add `NOTIFICATION_WEBHOOK_URL=` with a comment describing it as an optional Slack-compatible incoming
   webhook URL, left unset by default (free-by-default, per `.claude/portfolio-reference.md`'s Key
   Constraints — no paid delivery service required). | Dependencies: none. | Validation: `Settings()`
   still constructs with no `.env` changes required (field defaults to `None`).
4. `app/orchestrator/tools/webhook_tools.py` (new) — `deliver_webhook_notification(webhook_url, *,
   message, detail_link, timeout=5.0) -> dict`. POSTs a Slack-compatible `{"text": ...}` JSON body
   (message + detail_link) to `webhook_url`. Catches `httpx.HTTPError`/timeout/connection errors and a
   non-2xx response internally — **never raises** — and returns
   `{"delivered": bool, "status_code": int | None, "error": str | None}`. Single attempt only, no retry
   loop (per the feature spec's own "do not retry indefinitely" edge case). | Dependencies: none (new
   module). | Validation: unit-testable with a fake/mocked HTTP client the same way
   `test_orchestrator_tools*.py` already fakes `httpx`/`ollama` clients for `hubspot_tools.py`.
5. `app/orchestrator/graph.py`'s `persist_outcome_notification()` — after computing `output` (the
   `NotificationSlice` from `OutcomeNotificationStage.run()`), if `output.outcome_type ==
   "awaiting_review"`: lazily import `settings` (matching `build_production_graph()`'s existing local-
   import style) and, if `settings.notification_webhook_url` is set, call step 4's function and map its
   result to `external_delivery_status`/`external_delivery_error`; if unset, record `"skipped"`/`None`
   without attempting a call. For every other `outcome_type`, both fields stay `None` — no delivery
   attempted. Pass both values into the existing `Notification(...)` row construction. | Existing:
   `graph.py`. | New: none. | Dependencies: steps 1-4. | Requirement: this logic lives inside
   `persist_outcome_notification()` itself, not at any of its three call sites, and not as a new
   `OutcomeNotificationStage.allowed_tools` entry (that Stage stays pure-signaling, no tool access — an
   existing Feature 06/07 Key Decision this plan does not touch). | Validation: since step 4's function
   never raises, and this block sits before the function's existing `return output`, no additional
   `try/except` is needed here — the three existing call-site wrappers remain the only defensive layer,
   unchanged.
6. `app/schemas/notification.py`'s `NotificationOut` — add `external_delivery_status: str | None` and
   `external_delivery_error: str | None`. | Existing: `notifications.py` router needs no change — it
   already does `NotificationOut.model_validate(item)` over every column. | Dependencies: step 1.
   | Validation: `GET /notifications` response includes the two new fields for every row (`null` for
   pre-Feature-10 rows and for non-`awaiting_review` outcomes).

Architecture Rule Changes
- [ ] **New:** A `tools/` binding invoked by non-Stage orchestrator plumbing (e.g.
  `persist_outcome_notification()`) is called directly by that plumbing, not through
  `ToolRegistry`/`ScopedToolProxy` — the scoped-proxy boundary exists specifically to enforce a
  *Stage's* declared `allowed_tools`, which doesn't apply to code that isn't a Stage's own `run()`.
  — Conflict check: the existing "stage module ... only ever reaches [a tool] through its
  `ScopedToolProxy`" Key Decision (Feature 03) is scoped to *stage modules*; `persist_outcome_notification`
  already bypasses the scoped-proxy pattern for its direct `Notification` DB write, so this states
  explicitly, for the first time, a distinction the codebase already practiced implicitly. No conflict —
  a clarification of scope, not a contradiction.
- [ ] **New:** A side-channel delivery invoked from `persist_outcome_notification()` (or any future
  outcome-consuming extension) must be internally exception-safe — return a status, never raise — so a
  downstream delivery failure can never affect already-decided pipeline or in-app-notification state.
  Its result is recorded as data on the owning `Notification` row (`external_delivery_status`/`_error`),
  never a separate log table. — Conflict check: the existing "a stage's own external-system failure is
  encoded as data, never raised, when the spec wants the pipeline to continue past it" Key Decision
  (Features 03-05) governs a *Stage's* `run()` method deciding whether to halt *this lead's run*; this
  rule governs plumbing invoked strictly *after* a stage has already completed, where halting was never
  an option in the first place. Adjacent, not competing — no conflict.

Both approved and applied to `.claude/portfolio-reference.md`'s Key Decisions this session.

Feature-Specific Requirements
- External delivery fires only for `outcome_type == "awaiting_review"` — not `auto_processed`,
  `failed`, or `rejected` (the spec's own "filtered to review-pending outcomes specifically" language;
  `rejected`/`failed` are terminal outcomes a reviewer is, by definition, already looking at the app to
  produce or discover).
- Payload contents: the same `message`/`detail_link` `OutcomeNotificationStage` already computes for the
  in-app `Notification` — no second, differently-worded summary maintained separately.
- No batching: each `awaiting_review` event gets its own independent delivery attempt, even under a
  rapid burst of leads (per the spec's edge case) — satisfied automatically since delivery happens
  synchronously inline with each individual `persist_outcome_notification()` call, with no queue or
  batching layer introduced.
- `NOTIFICATION_WEBHOOK_URL` unset is a normal, expected configuration (free-by-default project
  constraint) — not an error condition, and never raises or logs at error severity.

Risks
- Risk: A slow or hanging external webhook adds latency to the request that pauses a run into
  `awaiting_review` (currently synchronous). Mitigation: a short client-side timeout (`5.0s`, matching
  `hubspot_tools.py`'s existing `httpx.Client` convention) inside `deliver_webhook_notification`, and no
  retry loop — a single bounded attempt.
- Risk: `external_delivery_error` could leak the configured `notification_webhook_url` value (a
  potential secret/destination) into the `Notification` table, which `GET /notifications` serves with no
  auth in this project. Mitigation: `deliver_webhook_notification`'s returned `error` string is built
  from the HTTP status code / exception type / short message only — the webhook URL itself is never
  interpolated into it.
- Risk: Adding a second required-looking field pair to `Notification` could look like it needs
  backfilling for the ~dozens of pre-Feature-10 rows already in dev databases. Mitigation: both columns
  are nullable with no default-value assumption beyond `None`; `None` is a valid, meaningful value
  ("this outcome never attempted delivery"), not a migration gap to fill.

Acceptance Criteria
- [ ] A review-pending (`awaiting_review`) outcome triggers both the existing in-app `Notification` row
  and, when `NOTIFICATION_WEBHOOK_URL` is configured, one external webhook POST containing the outcome's
  `message` and `detail_link`.
- [ ] A webhook delivery failure (non-2xx, timeout, connection error) is caught inside
  `deliver_webhook_notification`, recorded as `external_delivery_status="failed"` /
  `external_delivery_error=<reason>` on the `Notification` row, and never raises out of
  `persist_outcome_notification()` or changes `PipelineRun.status`.
- [ ] `auto_processed`, `failed`, and `rejected` outcomes never attempt external delivery —
  `external_delivery_status` stays `None` on those rows.
- [ ] `NOTIFICATION_WEBHOOK_URL` unset → `external_delivery_status="skipped"`, no HTTP call attempted,
  the in-app `Notification` row is still created exactly as before Feature 10.
- [ ] No retry loop — exactly one delivery attempt per `awaiting_review` outcome event.

Validation Requirements
- Live-verify (not unit-test-only, per this project's established Step 6/7 practice): trigger a real
  low-confidence lead through to `awaiting_review` against a real external endpoint (a disposable
  request-bin / local receiver, or a real Slack incoming webhook if available) and confirm the delivered
  payload's `message`/`detail_link` match the in-app `Notification` row exactly; separately confirm the
  skip path with `NOTIFICATION_WEBHOOK_URL` unset and the failure path against a deliberately unreachable
  URL (both via `GET /notifications`, checking `external_delivery_status`).
- Confirm zero regressions in `test_orchestrator_graph.py`, `test_router_notifications.py`, and
  `test_router_reviews.py` — none of the three `persist_outcome_notification()` call sites change
  signature, so all three should pass unchanged.
- Confirm `GET /notifications` still validates against `NotificationOut` for pre-Feature-10 rows (the
  two new columns read back as `null`/`None` with no schema error).

Predicted Footprint
Files predicted to change: 7 — `app/models/notification.py`, one new Alembic revision,
`app/core/config.py`, `backend/.env.example`, `app/orchestrator/tools/webhook_tools.py` (new),
`app/orchestrator/graph.py`, `app/schemas/notification.py`.
Systems predicted to touch: `Notification` persistence (Feature 07), orchestrator plumbing
(`persist_outcome_notification()`), Settings/`.env` config, one genuinely new external system (a
generic Slack-compatible webhook endpoint).
