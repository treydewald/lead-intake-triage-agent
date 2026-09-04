from datetime import datetime, timezone

from app.orchestrator.state import (
    ClassificationSlice,
    EnrichmentSlice,
    IntakeSlice,
    LeadPipelineState,
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
