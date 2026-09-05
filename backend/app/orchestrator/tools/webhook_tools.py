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
    """
    payload = {"text": f"{message}\n{detail_link}"}
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
