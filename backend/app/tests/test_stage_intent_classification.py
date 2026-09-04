from __future__ import annotations

import pytest

from app.orchestrator.errors import OutOfScopeToolError
from app.orchestrator.stages.intent_classification import IntentClassificationStage
from app.orchestrator.state import IntakeSlice
from app.orchestrator.tool_scope import ToolRegistry

STAGE = IntentClassificationStage()


def _run(intake: IntakeSlice, tool_fn):
    registry = ToolRegistry()
    registry.register("ollama_classify", tool_fn)
    proxy = registry.scoped_proxy(STAGE.allowed_tools, STAGE.name)
    return STAGE.run(intake, proxy)


def _intake(message_body: str = "I want to buy a house now", **kwargs) -> IntakeSlice:
    return IntakeSlice(source_channel="web_form", message_body=message_body, empty_message=False, **kwargs)


def test_clear_buyer_message_produces_buyer_label_with_high_confidence():
    result = _run(_intake(), lambda text: {"intent_label": "buyer", "confidence_score": 0.95})

    assert result.intent_label == "buyer"
    assert result.confidence_score == 0.95
    assert result.model_used == "ollama_local"


def test_empty_message_short_circuits_without_calling_tool():
    calls = []

    def tool_fn(text):
        calls.append(text)
        return {"intent_label": "buyer", "confidence_score": 0.9}

    result = _run(IntakeSlice(source_channel="web_form", message_body="", empty_message=True), tool_fn)

    assert calls == []
    assert result.intent_label is None
    assert result.confidence_score == 0.0
    assert result.model_used == "empty_message_short_circuit"


def test_tool_call_raising_on_both_attempts_produces_classification_failed_sentinel():
    def tool_fn(text):
        raise RuntimeError("ollama unreachable")

    result = _run(_intake(), tool_fn)

    assert result.intent_label is None
    assert result.confidence_score == 0.0
    assert result.model_used == "classification_failed"


def test_invalid_label_on_both_attempts_produces_classification_failed_sentinel():
    result = _run(_intake(), lambda text: {"intent_label": "not_a_real_label", "confidence_score": 0.9})

    assert result.model_used == "classification_failed"


def test_tool_call_fails_once_then_succeeds_on_retry_returns_successful_result():
    attempts = {"count": 0}

    def tool_fn(text):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient error")
        return {"intent_label": "browser", "confidence_score": 0.6}

    result = _run(_intake(), tool_fn)

    assert attempts["count"] == 2
    assert result.intent_label == "browser"
    assert result.confidence_score == 0.6
    assert result.model_used == "ollama_local"


def test_run_never_raises_out_of_run_for_expected_failure_modes():
    def tool_fn(text):
        raise RuntimeError("boom")

    # Should not raise - the failure is encoded as data, per Architecture Rule Change #2.
    result = _run(_intake(), tool_fn)
    assert result.model_used == "classification_failed"


def test_allowed_tools_contains_only_ollama_classify():
    assert STAGE.allowed_tools == frozenset({"ollama_classify"})

    registry = ToolRegistry()
    registry.register("ollama_classify", lambda text: {"intent_label": "buyer", "confidence_score": 0.9})
    registry.register("hubspot_write", lambda record: {"id": "123"})
    proxy = registry.scoped_proxy(STAGE.allowed_tools, STAGE.name)

    with pytest.raises(OutOfScopeToolError):
        proxy.call("hubspot_write", {})


def test_repeated_calls_with_same_response_produce_identical_result():
    tool_fn = lambda text: {"intent_label": "spam", "confidence_score": 0.85}  # noqa: E731

    first = _run(_intake(), tool_fn)
    second = _run(_intake(), tool_fn)

    assert first == second
