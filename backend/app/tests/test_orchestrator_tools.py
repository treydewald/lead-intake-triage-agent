from __future__ import annotations

import json

import pytest

from app.core.config import Settings
from app.orchestrator.tool_scope import ToolRegistry
from app.orchestrator.tools import register_default_tools
from app.orchestrator.tools.hubspot_tools import HubSpotWriteError, search_contact, write_contact
from app.orchestrator.tools.ollama_tools import classify_intent


class _FakeChatClient:
    """A lightweight double with the `.chat()` shape `classify_intent` calls, mirroring
    `test_orchestrator_tool_scope.py`'s style — no mocking library needed."""

    def __init__(self, content: str) -> None:
        self._content = content
        self.last_call: dict | None = None

    def chat(self, model, messages, format, options):
        self.last_call = {"model": model, "messages": messages, "format": format, "options": options}
        return {"message": {"content": self._content}}


def test_classify_intent_parses_json_response_from_chat_call():
    client = _FakeChatClient(json.dumps({"intent_label": "buyer", "confidence_score": 0.9}))

    result = classify_intent(client, "llama3.2:3b", "I want to buy now")

    assert result == {"intent_label": "buyer", "confidence_score": 0.9}


def test_classify_intent_calls_with_deterministic_json_mode_options():
    client = _FakeChatClient(json.dumps({"intent_label": "browser", "confidence_score": 0.4}))

    classify_intent(client, "llama3.2:3b", "just looking")

    assert client.last_call["model"] == "llama3.2:3b"
    assert client.last_call["format"] == "json"
    assert client.last_call["options"] == {"temperature": 0}
    assert client.last_call["messages"][-1] == {"role": "user", "content": "just looking"}


def test_register_default_tools_registers_ollama_classify():
    registry = ToolRegistry()
    settings = Settings(ollama_base_url="http://localhost:11434", ollama_model="llama3.2:3b")

    register_default_tools(registry, settings)

    assert callable(registry._tools.get("ollama_classify"))  # registered under the expected name


def test_register_default_tools_registers_hubspot_search_contact():
    registry = ToolRegistry()
    settings = Settings(hubspot_base_url="https://api.hubapi.com", hubspot_access_token="test-token")

    register_default_tools(registry, settings)

    assert callable(registry._tools.get("hubspot_search_contact"))


def test_register_default_tools_registers_hubspot_write_distinct_from_search():
    registry = ToolRegistry()
    settings = Settings(hubspot_base_url="https://api.hubapi.com", hubspot_access_token="test-token")

    register_default_tools(registry, settings)

    assert callable(registry._tools.get("hubspot_write"))
    assert registry._tools["hubspot_write"] is not registry._tools["hubspot_search_contact"]


class _FakeHttpResponse:
    def __init__(self, payload: dict, *, status_error: Exception | None = None) -> None:
        self._payload = payload
        self._status_error = status_error

    def raise_for_status(self) -> None:
        if self._status_error is not None:
            raise self._status_error

    def json(self) -> dict:
        return self._payload


class _FakeHttpClient:
    """A lightweight double with the `.post()` shape `search_contact` calls, mirroring
    `_FakeChatClient`'s style above - no mocking library needed."""

    def __init__(self, response: _FakeHttpResponse) -> None:
        self._response = response
        self.last_call: dict | None = None

    def post(self, url, *, json, headers):
        self.last_call = {"url": url, "json": json, "headers": headers}
        return self._response


def test_search_contact_returns_properties_on_exact_match_hit():
    response = _FakeHttpResponse({"results": [{"properties": {"email": "jane@example.com", "name": "Jane Doe"}}]})
    client = _FakeHttpClient(response)

    result = search_contact(client, "https://api.hubapi.com", "token-123", phone="5551234567")

    assert result == {"email": "jane@example.com", "name": "Jane Doe"}
    assert client.last_call["headers"] == {"Authorization": "Bearer token-123"}
    filters = client.last_call["json"]["filterGroups"][0]["filters"]
    assert filters == [{"propertyName": "phone", "operator": "EQ", "value": "5551234567"}]


def test_search_contact_returns_none_on_no_results():
    response = _FakeHttpResponse({"results": []})
    client = _FakeHttpClient(response)

    result = search_contact(client, "https://api.hubapi.com", "token-123", email="nobody@example.com")

    assert result is None


def test_search_contact_propagates_http_error():
    response = _FakeHttpResponse({}, status_error=RuntimeError("HubSpot unavailable"))
    client = _FakeHttpClient(response)

    with pytest.raises(RuntimeError, match="HubSpot unavailable"):
        search_contact(client, "https://api.hubapi.com", "token-123", email="nobody@example.com")


def test_search_contact_uses_fuzzy_name_filter_when_no_phone_or_email():
    response = _FakeHttpResponse({"results": []})
    client = _FakeHttpClient(response)

    search_contact(client, "https://api.hubapi.com", "token-123", name="Jane Doe")

    filters = client.last_call["json"]["filterGroups"][0]["filters"]
    assert filters == [{"propertyName": "name", "operator": "CONTAINS_TOKEN", "value": "Jane Doe"}]


class _FakeWriteResponse:
    """A lightweight double carrying `status_code`/`headers`, the fields `write_contact`
    inspects on a `httpx.HTTPStatusError` - mirrors `_FakeHttpResponse` above but adds
    what the retry/error-classification logic needs."""

    def __init__(self, payload: dict | None = None, *, status_code: int = 200, headers: dict | None = None) -> None:
        self.payload = payload or {}
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError(f"status {self.status_code}", request=None, response=self)

    def json(self) -> dict:
        return self.payload


class _FakeWriteClient:
    """A lightweight double with `.post()`/`.patch()`, responses consumed in order -
    `write_contact` calls `search_contact` (post, to the search endpoint) then either
    `.post()` (create) or `.patch()` (update) each attempt, so tests queue exactly the
    sequence a given scenario needs."""

    def __init__(self, responses: list["_FakeWriteResponse"]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict]] = []

    def post(self, url, *, json, headers):
        self.calls.append(("post", url, json))
        return self._responses.pop(0)

    def patch(self, url, *, json, headers):
        self.calls.append(("patch", url, json))
        return self._responses.pop(0)


def test_write_contact_creates_when_no_existing_match():
    client = _FakeWriteClient([
        _FakeWriteResponse({"results": []}),
        _FakeWriteResponse({"id": "hs-1"}),
    ])

    result = write_contact(
        client,
        "https://api.hubapi.com",
        "token-123",
        email="jane@example.com",
        properties={"email": "jane@example.com"},
        sleep=lambda _seconds: None,
    )

    assert result == {
        "id": "hs-1",
        "status": "created",
        "dedupe_key_used": "email",
        "dedupe_uncertain": False,
        "retry_count": 0,
    }
    assert [call[0] for call in client.calls] == ["post", "post"]


def test_write_contact_updates_when_existing_match_found():
    client = _FakeWriteClient([
        _FakeWriteResponse({"results": [{"properties": {"phone": "5551234567"}}]}),
        _FakeWriteResponse({"id": "hs-2"}),
    ])

    result = write_contact(
        client,
        "https://api.hubapi.com",
        "token-123",
        phone="5551234567",
        properties={"phone": "5551234567"},
        sleep=lambda _seconds: None,
    )

    assert result["status"] == "updated"
    assert result["dedupe_key_used"] == "phone"
    assert result["id"] == "hs-2"
    assert [call[0] for call in client.calls] == ["post", "patch"]


def test_write_contact_retries_once_on_429_then_succeeds():
    sleeps: list[float] = []
    client = _FakeWriteClient([
        _FakeWriteResponse({"results": []}),
        _FakeWriteResponse({}, status_code=429, headers={"Retry-After": "0"}),
        _FakeWriteResponse({"results": []}),
        _FakeWriteResponse({"id": "hs-3"}),
    ])

    result = write_contact(
        client,
        "https://api.hubapi.com",
        "token-123",
        email="jane@example.com",
        properties={},
        sleep=lambda seconds: sleeps.append(seconds),
    )

    assert result["retry_count"] == 1
    assert result["id"] == "hs-3"
    assert sleeps == [0.0]


def test_write_contact_raises_after_exhausting_retries_on_429():
    responses = []
    for _ in range(4):  # max_retries=3 -> 4 total attempts
        responses.append(_FakeWriteResponse({"results": []}))
        responses.append(_FakeWriteResponse({}, status_code=429))
    client = _FakeWriteClient(responses)

    with pytest.raises(HubSpotWriteError, match="after 3 retries"):
        write_contact(
            client,
            "https://api.hubapi.com",
            "token-123",
            email="jane@example.com",
            properties={},
            max_retries=3,
            sleep=lambda _seconds: None,
        )


def test_write_contact_raises_immediately_on_401_with_no_retry():
    sleeps: list[float] = []
    client = _FakeWriteClient([
        _FakeWriteResponse({"results": []}),
        _FakeWriteResponse({}, status_code=401),
    ])

    with pytest.raises(HubSpotWriteError, match="auth failed"):
        write_contact(
            client,
            "https://api.hubapi.com",
            "token-123",
            email="jane@example.com",
            properties={},
            sleep=lambda seconds: sleeps.append(seconds),
        )

    assert sleeps == []


def test_write_contact_raises_immediately_on_other_4xx_with_no_retry():
    client = _FakeWriteClient([
        _FakeWriteResponse({"results": []}),
        _FakeWriteResponse({}, status_code=400),
    ])

    with pytest.raises(HubSpotWriteError, match="rejected"):
        write_contact(
            client,
            "https://api.hubapi.com",
            "token-123",
            email="jane@example.com",
            properties={},
            sleep=lambda _seconds: None,
        )


def test_write_contact_with_no_identifying_field_creates_directly_with_dedupe_uncertain():
    client = _FakeWriteClient([_FakeWriteResponse({"id": "hs-4"})])

    result = write_contact(
        client,
        "https://api.hubapi.com",
        "token-123",
        properties={"firstname": "Unknown"},
        sleep=lambda _seconds: None,
    )

    assert result["dedupe_uncertain"] is True
    assert result["dedupe_key_used"] is None
    assert [call[0] for call in client.calls] == ["post"]  # zero dedupe-lookup calls
