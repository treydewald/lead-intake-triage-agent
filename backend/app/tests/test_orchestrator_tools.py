from __future__ import annotations

import json

import pytest

from app.core.config import Settings
from app.orchestrator.tool_scope import ToolRegistry
from app.orchestrator.tools import register_default_tools
from app.orchestrator.tools.hubspot_tools import search_contact
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
