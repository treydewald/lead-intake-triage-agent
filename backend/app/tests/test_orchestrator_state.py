from datetime import datetime, timezone

from app.orchestrator.state import (
    ClassificationSlice,
    CrmWriteSlice,
    EnrichmentSlice,
    IntakeSlice,
    LeadPipelineState,
    MergedIntakeEnrichment,
    RunMetadata,
    RunStatus,
)


def test_full_state_round_trips_through_serialization():
    state = LeadPipelineState(
        run=RunMetadata(run_id="run-1", lead_id="lead-1", status=RunStatus.RUNNING),
        intake=IntakeSlice(
            source_channel="web_form",
            name="Jane Doe",
            email="jane@example.com",
            message_body="Interested in a demo",
            received_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        classification=ClassificationSlice(intent_label="buyer", confidence_score=0.92, model_used="llama3.2:3b"),
    )

    round_tripped = LeadPipelineState.model_validate_json(state.model_dump_json())

    assert round_tripped == state
    assert round_tripped.intake.source_channel == "web_form"
    assert round_tripped.classification.confidence_score == 0.92
    assert round_tripped.run.status == RunStatus.RUNNING


def test_default_state_has_all_slices_present():
    state = LeadPipelineState()

    assert state.intake is not None
    assert state.classification is not None
    assert state.enrichment is not None
    assert state.crm_write is not None
    assert state.review is not None
    assert state.notification is not None
    assert state.run.status == RunStatus.RUNNING


def test_enrichment_slice_defaults_are_empty_and_none():
    slice_ = EnrichmentSlice()

    assert slice_.resolved_fields == {}
    assert slice_.sources == {}
    assert slice_.attempted_fields == []
    assert slice_.match_confidence is None
    assert slice_.conflicts == {}
    assert slice_.lookup_error is None


def test_crm_write_slice_defaults():
    slice_ = CrmWriteSlice()

    assert slice_.hubspot_record_id is None
    assert slice_.write_status is None
    assert slice_.dedupe_key_used is None
    assert slice_.dedupe_uncertain is False
    assert slice_.retry_count == 0


def test_merged_intake_enrichment_constructs_from_both_slices():
    merged = MergedIntakeEnrichment(
        intake=IntakeSlice(source_channel="web_form", email=None),
        enrichment=EnrichmentSlice(resolved_fields={"email": "jane@example.com"}),
    )

    assert merged.intake.source_channel == "web_form"
    assert merged.enrichment.resolved_fields["email"] == "jane@example.com"


def test_run_status_rejected_round_trips():
    """A reviewer's explicit rejection is `RunStatus.REJECTED` - a distinct terminal
    outcome from `FAILED`, per Feature 06's implementation plan."""
    state = LeadPipelineState(run=RunMetadata(run_id="run-1", lead_id="lead-1", status=RunStatus.REJECTED))

    round_tripped = LeadPipelineState.model_validate_json(state.model_dump_json())

    assert round_tripped.run.status == RunStatus.REJECTED
    assert round_tripped.run.status != RunStatus.FAILED
