from __future__ import annotations

import httpx
import pytest

from app.orchestrator.tools.webhook_tools import deliver_webhook_notification


class _FakeWebhookResponse:
    def __init__(self, *, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://hooks.example.com/incoming")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(f"status {self.status_code}", request=request, response=response)


class _FakeWebhookClient:
    """Mirrors `test_orchestrator_tools.py`'s `_FakeHttpClient` style - no mocking
    library needed."""

    def __init__(self, response: _FakeWebhookResponse | None = None, *, raises: Exception | None = None) -> None:
        self._response = response
        self._raises = raises
        self.last_call: dict | None = None

    def post(self, url, *, json):
        self.last_call = {"url": url, "json": json}
        if self._raises is not None:
            raise self._raises
        return self._response


def test_deliver_webhook_notification_success_returns_delivered_true():
    client = _FakeWebhookClient(_FakeWebhookResponse(status_code=200))

    result = deliver_webhook_notification(
        "https://hooks.example.com/incoming",
        message="Lead Jane Doe is awaiting human review.",
        detail_link="/reviews/run-1",
        client=client,
    )

    assert result == {"delivered": True, "status_code": 200, "error": None}
    assert client.last_call["url"] == "https://hooks.example.com/incoming"
    assert client.last_call["json"] == {"text": "Lead Jane Doe is awaiting human review.\n/reviews/run-1"}


def test_deliver_webhook_notification_non_2xx_returns_failed_without_raising():
    client = _FakeWebhookClient(_FakeWebhookResponse(status_code=500))

    result = deliver_webhook_notification(
        "https://hooks.example.com/incoming", message="msg", detail_link="/reviews/run-1", client=client
    )

    assert result["delivered"] is False
    assert result["status_code"] == 500
    assert "500" in result["error"]


def test_deliver_webhook_notification_connection_error_returns_failed_without_raising():
    client = _FakeWebhookClient(raises=httpx.ConnectError("connection refused"))

    result = deliver_webhook_notification(
        "https://hooks.example.com/incoming", message="msg", detail_link="/reviews/run-1", client=client
    )

    assert result == {"delivered": False, "status_code": None, "error": "ConnectError"}


def test_deliver_webhook_notification_timeout_returns_failed_without_raising():
    client = _FakeWebhookClient(raises=httpx.TimeoutException("timed out"))

    result = deliver_webhook_notification(
        "https://hooks.example.com/incoming", message="msg", detail_link="/reviews/run-1", client=client
    )

    assert result == {"delivered": False, "status_code": None, "error": "TimeoutException"}


def test_deliver_webhook_notification_includes_interactive_buttons_when_run_id_given():
    """Feature 19: when `run_id` is provided, the payload gains a Slack Block Kit
    `actions` block with Approve/Reject buttons carrying that run id - see
    architecture-plan-feature-19.md."""
    client = _FakeWebhookClient(_FakeWebhookResponse(status_code=200))

    result = deliver_webhook_notification(
        "https://hooks.example.com/incoming",
        message="Lead Jane Doe is awaiting human review.",
        detail_link="/reviews/run-1",
        run_id="run-1",
        client=client,
    )

    assert result["delivered"] is True
    sent = client.last_call["json"]
    assert sent["text"] == "Lead Jane Doe is awaiting human review.\n/reviews/run-1"
    actions_block = next(block for block in sent["blocks"] if block["type"] == "actions")
    buttons = {el["action_id"]: el for el in actions_block["elements"]}
    assert set(buttons.keys()) == {"approve_lead", "reject_lead"}
    assert buttons["approve_lead"]["value"] == "run-1"
    assert buttons["reject_lead"]["value"] == "run-1"


def test_deliver_webhook_notification_error_never_includes_the_webhook_url():
    """Risk mitigation from architecture-plan-feature-10.md: `error` must be built from
    the status code/exception type only, never interpolate the configured URL (a
    potential secret/destination) - GET /notifications serves this table with no auth."""
    secret_url = "https://hooks.example.com/T00/B00/super-secret-token"
    client = _FakeWebhookClient(_FakeWebhookResponse(status_code=404))

    result = deliver_webhook_notification(secret_url, message="msg", detail_link="/reviews/run-1", client=client)

    assert secret_url not in (result["error"] or "")
