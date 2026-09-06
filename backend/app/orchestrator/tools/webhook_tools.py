from __future__ import annotations

from typing import Protocol

import httpx


class _HttpClient(Protocol):
    def post(self, url: str, *, json: dict) -> "_HttpResponse":
        ...


class _HttpResponse(Protocol):
    status_code: int

    def raise_for_status(self) -> None:
        ...


def deliver_webhook_notification(
    webhook_url: str,
    *,
    message: str,
    detail_link: str,
    run_id: str | None = None,
    timeout: float = 5.0,
    client: _HttpClient | None = None,
) -> dict:
    """Best-effort, single-attempt delivery of a Slack-compatible `{"text": ...}` payload
    to an operator-configured incoming webhook.

    Called directly by `persist_outcome_notification()` (see
    architecture-plan-feature-10.md's Architecture Rule Change #1) rather than through
    `ToolRegistry`/`ScopedToolProxy` — that boundary exists to enforce a Stage's own
    declared `allowed_tools`, which doesn't apply to plumbing invoked after a stage has
    already completed. Never raises: any HTTP/timeout/connection error, or a non-2xx
    response, is caught and returned as data, since a downstream delivery failure must
    never affect already-decided pipeline or in-app-notification state. The returned
    `error` is built from the status code / exception type only — the webhook URL itself
    is never interpolated into it, since `GET /notifications` serves this table with no
    auth. Exactly one attempt, no retry loop (per the feature spec's "do not retry
    indefinitely" edge case).

    Feature 19: when `run_id` is provided (the caller only ever does this for
    `awaiting_review` deliveries — see `graph.py`'s call site), the payload also carries
    a Slack Block Kit `actions` block with Approve/Reject buttons whose `value` is the
    run id, so `POST /slack/interactions` can route a click back to
    `apply_review_action()`. When `run_id` is omitted (every other outcome type), the
    payload shape is byte-for-byte unchanged from before this feature — no regression to
    a non-`awaiting_review` delivery.
    """
    payload: dict = {"text": f"{message}\n{detail_link}"}
    if run_id is not None:
        payload["blocks"] = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"{message}\n{detail_link}"}},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "style": "primary",
                        "action_id": "approve_lead",
                        "value": run_id,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Reject"},
                        "style": "danger",
                        "action_id": "reject_lead",
                        "value": run_id,
                    },
                ],
            },
        ]
    try:
        if client is not None:
            response = client.post(webhook_url, json=payload)
        else:
            with httpx.Client(timeout=timeout) as http_client:
                response = http_client.post(webhook_url, json=payload)
        response.raise_for_status()
        return {"delivered": True, "status_code": response.status_code, "error": None}
    except httpx.HTTPStatusError as exc:
        return {
            "delivered": False,
            "status_code": exc.response.status_code,
            "error": f"non-2xx response: {exc.response.status_code}",
        }
    except httpx.HTTPError as exc:
        return {"delivered": False, "status_code": None, "error": type(exc).__name__}
