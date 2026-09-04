from __future__ import annotations

import json

from app.core.config import Settings
from app.orchestrator.tool_scope import ToolRegistry
from app.orchestrator.tools import register_default_tools
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
