from __future__ import annotations

from app.orchestrator.stages.outcome_notification import OutcomeNotificationStage
from app.orchestrator.state import CrmWriteSlice, IntakeSlice, NotificationInput, RunMetadata, RunStatus
from app.orchestrator.tool_scope import ToolRegistry


def _stage_and_proxy():
    stage = OutcomeNotificationStage()
    registry = ToolRegistry()
    proxy = registry.scoped_proxy(stage.allowed_tools, stage.name)
    return stage, proxy


def test_running_status_produces_auto_processed_outcome_linking_to_lead_detail():
    stage, proxy = _stage_and_proxy()
    data = NotificationInput(
        run=RunMetadata(run_id="run-1", lead_id="lead-1", status=RunStatus.RUNNING),
        intake=IntakeSlice(source_channel="web_form", name="Jane Doe"),
        crm_write=CrmWriteSlice(hubspot_record_id="hs-1", write_status="created"),
    )

    result = stage.run(data, proxy)

    assert result.notified is True
    assert result.outcome_type == "auto_processed"
    assert result.detail_link == "/leads/lead-1"
    assert "Jane Doe" in result.message


def test_awaiting_review_status_produces_awaiting_review_outcome_linking_to_review_queue():
    stage, proxy = _stage_and_proxy()
    data = NotificationInput(
        run=RunMetadata(run_id="run-1", lead_id="lead-1", status=RunStatus.AWAITING_REVIEW),
        intake=IntakeSlice(source_channel="web_form", name="Jane Doe"),
        crm_write=CrmWriteSlice(),
    )

    result = stage.run(data, proxy)

    assert result.outcome_type == "awaiting_review"
    assert result.detail_link == "/reviews/run-1"


def test_rejected_status_produces_rejected_outcome_linking_to_review_queue():
    stage, proxy = _stage_and_proxy()
    data = NotificationInput(
        run=RunMetadata(run_id="run-1", lead_id="lead-1", status=RunStatus.REJECTED),
        intake=IntakeSlice(source_channel="web_form", name="Jane Doe"),
        crm_write=CrmWriteSlice(),
    )

    result = stage.run(data, proxy)

    assert result.outcome_type == "rejected"
    assert result.detail_link == "/reviews/run-1"


def test_failed_status_produces_failed_outcome_describing_the_failure():
    stage, proxy = _stage_and_proxy()
    data = NotificationInput(
        run=RunMetadata(
            run_id="run-1",
            lead_id="lead-1",
            status=RunStatus.FAILED,
            failed_stage="hubspot_crm_write",
            error="HubSpot write failed after 3 retries",
        ),
        intake=IntakeSlice(source_channel="web_form", name="Jane Doe"),
        crm_write=CrmWriteSlice(),
    )

    result = stage.run(data, proxy)

    assert result.outcome_type == "failed"
    assert result.detail_link == "/leads/lead-1"
    assert "hubspot_crm_write" in result.message
    assert "HubSpot write failed after 3 retries" in result.message


def test_null_name_falls_back_to_phone_then_email_then_lead_id():
    stage, proxy = _stage_and_proxy()

    by_phone = stage.run(
        NotificationInput(
            run=RunMetadata(run_id="run-1", lead_id="lead-1", status=RunStatus.RUNNING),
            intake=IntakeSlice(source_channel="web_form", phone="5551234567"),
            crm_write=CrmWriteSlice(),
        ),
        proxy,
    )
    assert "5551234567" in by_phone.message

    by_email = stage.run(
        NotificationInput(
            run=RunMetadata(run_id="run-1", lead_id="lead-1", status=RunStatus.RUNNING),
            intake=IntakeSlice(source_channel="web_form", email="jane@example.com"),
            crm_write=CrmWriteSlice(),
        ),
        proxy,
    )
    assert "jane@example.com" in by_email.message

    by_lead_id = stage.run(
        NotificationInput(
            run=RunMetadata(run_id="run-1", lead_id="lead-1", status=RunStatus.RUNNING),
            intake=IntakeSlice(source_channel="web_form"),
            crm_write=CrmWriteSlice(),
        ),
        proxy,
    )
    assert "lead-1" in by_lead_id.message


def test_outcome_notification_stage_declares_no_tool_access():
    # This stage should never gain tool access - like HumanReviewStage, it's a pure
    # signaling stage over already-computed state, not a caller of external systems.
    assert OutcomeNotificationStage.allowed_tools == frozenset()
