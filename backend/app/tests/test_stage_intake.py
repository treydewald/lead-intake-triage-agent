from __future__ import annotations

import pytest

from app.orchestrator.errors import OutOfScopeToolError
from app.orchestrator.stages.intake import IntakeStage
from app.orchestrator.state import IntakeSlice
from app.orchestrator.tool_scope import ToolRegistry

STAGE = IntakeStage()


def _run(intake: IntakeSlice) -> IntakeSlice:
    registry = ToolRegistry()
    proxy = registry.scoped_proxy(STAGE.allowed_tools, STAGE.name)
    return STAGE.run(intake, proxy)


def test_web_form_payload_with_all_fields_is_fully_populated():
    intake = IntakeSlice(
        source_channel="web_form",
        name="  Jane Doe  ",
        phone="(555) 123-4567",
        email="  JANE@EXAMPLE.COM  ",
        message_body="I want to buy now",
    )
    result = _run(intake)

    assert result.source_channel == "web_form"
    assert result.name == "Jane Doe"
    assert result.phone == "5551234567"
    assert result.email == "jane@example.com"
    assert result.message_body == "I want to buy now"
    assert result.empty_message is False
    assert result.low_identifiability is False


def test_raw_email_text_extracts_sender_fields_and_retains_body():
    raw_email = (
        "From: Jane Doe <jane@example.com>\n"
        "Subject: Interested in a demo\n"
        "\n"
        "Hi, I'd like to schedule a demo. Thanks!"
    )
    intake = IntakeSlice(source_channel="email", message_body=raw_email)
    result = _run(intake)

    assert result.source_channel == "email"
    assert result.name == "Jane Doe"
    assert result.email == "jane@example.com"
    assert result.message_body == "Hi, I'd like to schedule a demo. Thanks!"
    assert result.empty_message is False


def test_malformed_email_falls_back_to_raw_text_with_null_structured_fields():
    raw_text = "not a real email, just some free text someone pasted in"
    intake = IntakeSlice(source_channel="email", message_body=raw_text)
    result = _run(intake)

    assert result.name is None
    assert result.email is None
    assert result.message_body == raw_text
    assert result.low_identifiability is True


def test_callback_transcript_with_no_extractable_fields_retains_transcript():
    transcript = "Hi this is a message, please call me back sometime, thanks."
    intake = IntakeSlice(source_channel="callback", message_body=transcript)
    result = _run(intake)

    assert result.source_channel == "callback"
    assert result.message_body == transcript
    assert result.phone is None
    assert result.low_identifiability is True


def test_callback_transcript_extracts_phone_number():
    transcript = "Hey it's John, you can reach me at 555-987-6543 anytime."
    intake = IntakeSlice(source_channel="callback", message_body=transcript)
    result = _run(intake)

    assert result.phone == "5559876543"
    assert result.message_body == transcript


def test_every_record_is_tagged_with_correct_source_channel():
    for channel in ("web_form", "email", "callback"):
        intake = IntakeSlice(source_channel=channel, message_body="hello")
        result = _run(intake)
        assert result.source_channel == channel


def test_empty_message_body_does_not_raise_and_is_flagged():
    intake = IntakeSlice(source_channel="web_form", name="Jane", message_body="   ")
    result = _run(intake)

    assert result.empty_message is True
    assert result.low_identifiability is False


def test_all_identifying_fields_missing_is_flagged_low_identifiability():
    intake = IntakeSlice(source_channel="web_form", message_body="just a message")
    result = _run(intake)

    assert result.low_identifiability is True


def test_intake_stage_has_no_successful_path_to_any_tool_call():
    """Boundary test consistent with Feature 01's tool-scoping pattern: `allowed_tools`
    is empty, so even a registered tool must be rejected, not silently reachable."""
    registry = ToolRegistry()
    registry.register("hubspot_write", lambda record: {"id": "123"})
    proxy = registry.scoped_proxy(STAGE.allowed_tools, STAGE.name)

    with pytest.raises(OutOfScopeToolError):
        proxy.call("hubspot_write", {})
