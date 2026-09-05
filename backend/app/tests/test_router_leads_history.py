from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.pipeline_run import PipelineRun, StageTrace
from app.models.review_queue import ReviewQueueItem
from app.orchestrator.contracts import Stage
from app.orchestrator.graph import build_graph, build_resume_graph, run_pipeline
from app.orchestrator.stages.human_review import HumanReviewStage
from app.orchestrator.state import (
    ClassificationSlice,
    CrmWriteSlice,
    EnrichmentSlice,
    IntakeSlice,
    LeadPipelineState,
    NotificationSlice,
    ReviewSlice,
)
from app.orchestrator.tool_scope import ToolRegistry
from app.routers.leads import get_session_factory as get_leads_session_factory
from app.routers.reviews import get_resume_graph_factory, get_session_factory as get_reviews_session_factory
from main import app


class _FakeStage(Stage):
    """Same test-double shape as `test_router_reviews.py`'s own `_FakeStage`."""

    def __init__(self, name, state_slice, schema, fn, input_slice=None):
        self.name = name
        self.state_slice = state_slice
        self.input_schema = schema
        self.output_schema = schema
        self.allowed_tools = frozenset()
        self.input_slice = input_slice
        self._fn = fn

    def run(self, data, tools):
        return self._fn(data, tools)


class _CapturingCrmWriteStage(Stage):
    name = "hubspot_crm_write"
    input_schema = ClassificationSlice
    output_schema = CrmWriteSlice
    allowed_tools = frozenset()
    state_slice = "crm_write"
    input_slice = "classification"

    def run(self, data, tools):
        return CrmWriteSlice(hubspot_record_id="hs-test", write_status="created")


def _paused_stages(confidence: float) -> dict[str, Stage]:
    return {
        "intake": _FakeStage("intake_parsing", "intake", IntakeSlice, lambda data, tools: data),
        "classification": _FakeStage(
            "intent_classification",
            "classification",
            ClassificationSlice,
            lambda data, tools: ClassificationSlice(
                intent_label="browser", confidence_score=confidence, model_used="test-model"
            ),
            input_slice="intake",
        ),
        "enrichment": _FakeStage(
            "data_enrichment", "enrichment", EnrichmentSlice, lambda data, tools: EnrichmentSlice(), input_slice="intake"
        ),
        "crm_write": _FakeStage("hubspot_crm_write", "crm_write", CrmWriteSlice, lambda data, tools: CrmWriteSlice()),
        "review": HumanReviewStage(),
        "notification": _FakeStage(
            "outcome_notification",
            "notification",
            NotificationSlice,
            lambda data, tools: NotificationSlice(
                notified=True, outcome_type="awaiting_review", message="test", detail_link="/reviews/test"
            ),
        ),
    }


def _create_paused_run(db_session_factory, lead_id: str):
    graph = build_graph(_paused_stages(confidence=0.2), ToolRegistry(), db_session_factory, confidence_threshold=0.7)
    return run_pipeline(
        lead_id,
        LeadPipelineState(intake=IntakeSlice(source_channel="web_form", message_body="just looking")),
        graph=graph,
        session_factory=db_session_factory,
    )


def _fake_resume_graph_factory():
    notify_stage = _FakeStage(
        "outcome_notification",
        "notification",
        NotificationSlice,
        lambda data, tools: NotificationSlice(notified=True, outcome_type="auto_processed"),
    )

    def factory(session_factory):
        return build_resume_graph({"crm_write": _CapturingCrmWriteStage(), "notification": notify_stage}, ToolRegistry(), session_factory)

    return factory


def _run_auto_processed(db_session_factory, lead_id: str):
    stages = {
        "intake": _FakeStage("intake_parsing", "intake", IntakeSlice, lambda data, tools: data),
        "classification": _FakeStage(
            "intent_classification",
            "classification",
            ClassificationSlice,
            lambda data, tools: ClassificationSlice(intent_label="buyer", confidence_score=0.95, model_used="test-model"),
        ),
        "enrichment": _FakeStage("data_enrichment", "enrichment", EnrichmentSlice, lambda data, tools: EnrichmentSlice()),
        "crm_write": _FakeStage(
            "hubspot_crm_write", "crm_write", CrmWriteSlice,
            lambda data, tools: CrmWriteSlice(hubspot_record_id="hs-1", write_status="created"),
        ),
        "review": _FakeStage(
            "human_review", "review", ReviewSlice,
            lambda data, tools: ReviewSlice(queued=True, paused_at_stage="crm_write"),
        ),
        "notification": _FakeStage(
            "outcome_notification", "notification", NotificationSlice,
            lambda data, tools: NotificationSlice(notified=True, outcome_type="auto_processed"),
        ),
    }
    graph = build_graph(stages, ToolRegistry(), db_session_factory, confidence_threshold=0.7)
    return run_pipeline(
        lead_id,
        LeadPipelineState(intake=IntakeSlice(source_channel="web_form", message_body="hello")),
        graph=graph,
        session_factory=db_session_factory,
    )


@pytest.fixture(autouse=True)
def _override_session_factories(db_session_factory):
    app.dependency_overrides[get_leads_session_factory] = lambda: db_session_factory
    app.dependency_overrides[get_reviews_session_factory] = lambda: db_session_factory
    yield
    app.dependency_overrides.clear()


def test_history_unknown_lead_id_returns_404(client, db_session_factory):
    response = client.get("/leads/does-not-exist/history")
    assert response.status_code == 404


def test_history_auto_processed_lead_has_stage_entries_only(client, db_session_factory):
    final = _run_auto_processed(db_session_factory, "lead-auto-history")

    response = client.get(f"/leads/{final.run.lead_id}/history")

    assert response.status_code == 200
    body = response.json()
    assert body["lead_id"] == final.run.lead_id
    assert len(body["entries"]) > 0
    assert all(entry["kind"] == "stage" for entry in body["entries"])
    timestamps = [entry["created_at"] for entry in body["entries"]]
    assert timestamps == sorted(timestamps)


def test_history_pending_review_produces_no_fabricated_review_entry(client, db_session_factory):
    paused = _create_paused_run(db_session_factory, "lead-pending-history")

    response = client.get(f"/leads/{paused.run.lead_id}/history")

    assert response.status_code == 200
    body = response.json()
    assert all(entry["kind"] != "review_action" for entry in body["entries"])


def test_history_reviewed_lead_shows_stage_and_review_action_ordered(client, db_session_factory):
    paused = _create_paused_run(db_session_factory, "lead-reviewed-history")
    app.dependency_overrides[get_resume_graph_factory] = _fake_resume_graph_factory

    action_response = client.post(
        f"/reviews/{paused.run.run_id}/action",
        json={"action": "approve", "reviewer_name": "Jordan"},
    )
    assert action_response.status_code == 200

    response = client.get(f"/leads/{paused.run.lead_id}/history")

    assert response.status_code == 200
    body = response.json()
    kinds = [entry["kind"] for entry in body["entries"]]
    assert "stage" in kinds
    assert "review_action" in kinds

    review_entry = next(entry for entry in body["entries"] if entry["kind"] == "review_action")
    assert review_entry["reviewer_action"] == "approve"
    assert review_entry["reviewer_name"] == "Jordan"

    timestamps = [entry["created_at"] for entry in body["entries"]]
    assert timestamps == sorted(timestamps)


def test_history_reject_shows_terminal_review_action_distinct_from_failed_stage(client, db_session_factory):
    paused = _create_paused_run(db_session_factory, "lead-rejected-history")

    action_response = client.post(f"/reviews/{paused.run.run_id}/action", json={"action": "reject"})
    assert action_response.status_code == 200

    response = client.get(f"/leads/{paused.run.lead_id}/history")

    assert response.status_code == 200
    body = response.json()
    review_entries = [entry for entry in body["entries"] if entry["kind"] == "review_action"]
    assert len(review_entries) == 1
    assert review_entries[0]["reviewer_action"] == "reject"
    # The reject decision must never be conflated with a FAILED stage entry - no stage
    # trace in this run's history is itself FAILED (the run paused normally at review).
    assert all(entry.get("status") != "FAILED" for entry in body["entries"] if entry["kind"] == "stage")


def test_history_multi_run_lead_shows_both_attempts_distinctly(client, db_session_factory):
    """Fixture-seeded directly at the DB level, per architecture-plan-feature-11.md's
    multi-attempt gap note - no live endpoint resubmits an existing lead_id, so this is
    the only way to exercise the acceptance criterion covering that scenario."""
    lead_id = "lead-multi-run-history"
    db = db_session_factory()
    try:
        first_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        second_time = first_time + timedelta(hours=1)

        run_1 = PipelineRun(lead_id=lead_id, status="FAILED", created_at=first_time, updated_at=first_time)
        run_2 = PipelineRun(
            lead_id=lead_id, status="COMPLETED", created_at=second_time, updated_at=second_time
        )
        db.add_all([run_1, run_2])
        db.commit()

        run_1_id, run_2_id = run_1.id, run_2.id

        db.add_all(
            [
                StageTrace(
                    run_id=run_1_id,
                    stage_name="intake_parsing",
                    status="COMPLETED",
                    created_at=first_time,
                ),
                StageTrace(
                    run_id=run_1_id,
                    stage_name="intent_classification",
                    status="FAILED",
                    error="boom",
                    created_at=first_time + timedelta(minutes=1),
                ),
                StageTrace(
                    run_id=run_2_id,
                    stage_name="intake_parsing",
                    status="COMPLETED",
                    created_at=second_time,
                ),
                StageTrace(
                    run_id=run_2_id,
                    stage_name="intent_classification",
                    status="COMPLETED",
                    created_at=second_time + timedelta(minutes=1),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get(f"/leads/{lead_id}/history")

    assert response.status_code == 200
    body = response.json()
    run_ids = {entry["run_id"] for entry in body["entries"]}
    assert run_ids == {run_1_id, run_2_id}
    assert len(body["entries"]) == 4
    # Chronological order across both runs, not grouped/collapsed by run.
    stage_names_in_order = [entry["stage_key"] for entry in body["entries"]]
    assert stage_names_in_order == [
        "intake_parsing",
        "intent_classification",
        "intake_parsing",
        "intent_classification",
    ]
