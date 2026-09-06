from __future__ import annotations

import pytest

from app.orchestrator import confidence_scoring
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


def _fixed_response_tool(label: str, confidence: float):
    """A tool double answering every call (primary or confirmation) identically —
    `temperature` is accepted and ignored, mirroring how a real deterministic double would
    behave if asked the same question twice. Used by tests that only care about the primary
    self-reported value flowing into the composite, not about consistency effects."""

    def tool_fn(text: str, temperature: float = 0.0) -> dict:
        return {"intent_label": label, "confidence_score": confidence}

    return tool_fn


def _expected_composite(text: str, label: str, self_reported: float, *, has_contact_info: bool, consistency):
    lexical = confidence_scoring.lexical_signal(text, label, has_contact_info=has_contact_info)
    return confidence_scoring.combine(self_reported, lexical, consistency)


def test_clear_buyer_message_produces_buyer_label_with_composite_confidence():
    intake = _intake()
    result = _run(intake, _fixed_response_tool("buyer", 0.95))

    assert result.intent_label == "buyer"
    assert result.model_used == "ollama_local"
    # Confirmation call agrees (same fixed response) -> consistency=1.0
    expected = _expected_composite(
        "I want to buy a house now", "buyer", 0.95, has_contact_info=False, consistency=1.0
    )
    assert result.confidence_score == pytest.approx(expected)
    assert result.confidence_score != 0.95  # composite, not a passthrough of the raw self-report


def test_empty_message_short_circuits_without_calling_tool():
    calls = []

    def tool_fn(text, temperature: float = 0.0):
        calls.append(text)
        return {"intent_label": "buyer", "confidence_score": 0.9}

    result = _run(IntakeSlice(source_channel="web_form", message_body="", empty_message=True), tool_fn)

    assert calls == []
    assert result.intent_label is None
    assert result.confidence_score == 0.0
    assert result.model_used == "empty_message_short_circuit"


def test_tool_call_raising_on_both_attempts_produces_classification_failed_sentinel():
    def tool_fn(text, temperature: float = 0.0):
        raise RuntimeError("ollama unreachable")

    result = _run(_intake(), tool_fn)

    assert result.intent_label is None
    assert result.confidence_score == 0.0
    assert result.model_used == "classification_failed"


def test_invalid_label_on_both_attempts_produces_classification_failed_sentinel():
    result = _run(_intake(), _fixed_response_tool("not_a_real_label", 0.9))

    assert result.model_used == "classification_failed"


def test_tool_call_fails_once_then_succeeds_on_retry_returns_successful_result():
    attempts = {"count": 0}

    def tool_fn(text, temperature: float = 0.0):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient error")
        return {"intent_label": "browser", "confidence_score": 0.6}

    result = _run(_intake(), tool_fn)

    # 2 retry attempts for the primary call, plus 1 confirmation call once a valid primary
    # response is in hand.
    assert attempts["count"] == 3
    assert result.intent_label == "browser"
    assert result.model_used == "ollama_local"


def test_run_never_raises_out_of_run_for_expected_failure_modes():
    def tool_fn(text, temperature: float = 0.0):
        raise RuntimeError("boom")

    # Should not raise - the failure is encoded as data, per Architecture Rule Change #2.
    result = _run(_intake(), tool_fn)
    assert result.model_used == "classification_failed"


def test_allowed_tools_contains_only_ollama_classify():
    assert STAGE.allowed_tools == frozenset({"ollama_classify"})

    registry = ToolRegistry()
    registry.register("ollama_classify", _fixed_response_tool("buyer", 0.9))
    registry.register("hubspot_write", lambda record: {"id": "123"})
    proxy = registry.scoped_proxy(STAGE.allowed_tools, STAGE.name)

    with pytest.raises(OutOfScopeToolError):
        proxy.call("hubspot_write", {})


def test_repeated_calls_with_same_response_produce_identical_result():
    tool_fn = _fixed_response_tool("spam", 0.85)

    first = _run(_intake(), tool_fn)
    second = _run(_intake(), tool_fn)

    assert first == second


def test_confirmation_disagreement_lowers_confidence_relative_to_agreement():
    text = "I want to buy a house now"

    def agreeing_tool(t, temperature: float = 0.0):
        return {"intent_label": "buyer", "confidence_score": 0.9}

    calls = {"n": 0}

    def disagreeing_tool(t, temperature: float = 0.0):
        calls["n"] += 1
        # Primary call (temperature default 0.0) agrees on the label; the confirmation
        # call (nonzero temperature) disagrees.
        if calls["n"] == 1:
            return {"intent_label": "buyer", "confidence_score": 0.9}
        return {"intent_label": "browser", "confidence_score": 0.9}

    agreeing_result = _run(_intake(text), agreeing_tool)
    disagreeing_result = _run(_intake(text), disagreeing_tool)

    assert agreeing_result.intent_label == "buyer"
    assert disagreeing_result.intent_label == "buyer"  # confirmation never overrides the label
    assert disagreeing_result.confidence_score < agreeing_result.confidence_score


def test_confirmation_call_failure_falls_back_without_failing_the_classification():
    calls = {"n": 0}

    def tool_fn(t, temperature: float = 0.0):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"intent_label": "buyer", "confidence_score": 0.9}
        raise RuntimeError("confirmation call unreachable")

    result = _run(_intake(), tool_fn)

    assert result.intent_label == "buyer"
    assert result.model_used == "ollama_local"
    expected = _expected_composite(
        "I want to buy a house now", "buyer", 0.9, has_contact_info=False, consistency=None
    )
    assert result.confidence_score == pytest.approx(expected)


def test_confirmation_call_receives_nonzero_temperature():
    seen_temperatures: list[float] = []

    def tool_fn(t, temperature: float = 0.0):
        seen_temperatures.append(temperature)
        return {"intent_label": "buyer", "confidence_score": 0.9}

    _run(_intake(), tool_fn)

    assert seen_temperatures == [0.0, confidence_scoring.CONFIRMATION_TEMPERATURE]
