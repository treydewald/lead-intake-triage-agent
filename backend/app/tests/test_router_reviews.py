from __future__ import annotations

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
    RunStatus,
)
from app.orchestrator.tool_scope import ToolRegistry
from app.routers.reviews import get_resume_graph_factory, get_session_factory
from main import app


class _FakeStage(Stage):
    """A test double conforming to the Stage contract - same shape as
    `test_orchestrator_graph.py`'s own `_FakeStage`."""

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


def _paused_stages(confidence: float) -> dict[str, Stage]:
    """Intake/classify/enrich are fakes (only the low-confidence routing matters here);
    `review` is the real `HumanReviewStage` under test's own dependency (proving these
    router tests build on the real queuing path, not a re-fake of Feature 06 itself)."""
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
            "data_enrichment",
            "enrichment",
            EnrichmentSlice,
            lambda data, tools: EnrichmentSlice(),
            input_slice="intake",
        ),
        "crm_write": _FakeStage("hubspot_crm_write", "crm_write", CrmWriteSlice, lambda data, tools: CrmWriteSlice()),
        "review": HumanReviewStage(),
        "notification": _FakeStage(
            "outcome_notification", "notification", NotificationSlice, lambda data, tools: NotificationSlice()
        ),
    }


def _create_paused_run(db_session_factory, lead_id: str = "lead-review") -> LeadPipelineState:
    graph = build_graph(_paused_stages(confidence=0.2), ToolRegistry(), db_session_factory, confidence_threshold=0.7)
    return run_pipeline(
        lead_id,
        LeadPipelineState(intake=IntakeSlice(source_channel="web_form", message_body="just looking")),
        graph=graph,
        session_factory=db_session_factory,
    )


class _CapturingCrmWriteStage(Stage):
    """Fake resume-time stand-in for `HubSpotCrmWriteStage`, deliberately reading
    `classification` (instead of the real stage's intake/enrichment merge) purely to
    prove the router's resume plumbing delivers a possibly-corrected label onward - see
    Feature 06's Acceptance Criteria ("edit resumes with corrected_intent_label
    reflected in state.classification.intent_label by the time HubSpotCrmWriteStage
    runs"). Avoids any real HubSpot/Ollama network call, mirroring how Feature 05's own
    tests never require live credentials."""

    name = "hubspot_crm_write"
    input_schema = ClassificationSlice
    output_schema = CrmWriteSlice
    allowed_tools = frozenset()
    state_slice = "crm_write"
    input_slice = "classification"

    def __init__(self):
        self.received_labels: list[str | None] = []

    def run(self, data: ClassificationSlice, tools) -> CrmWriteSlice:
        self.received_labels.append(data.intent_label)
        return CrmWriteSlice(hubspot_record_id="hs-test", write_status="created")


def _fake_resume_graph_factory(capturing_stage: _CapturingCrmWriteStage):
    notify_stage = _FakeStage(
        "outcome_notification",
        "notification",
        NotificationSlice,
        lambda data, tools: NotificationSlice(notified=True, outcome_type="auto_processed"),
    )

    def factory(session_factory):
        return build_resume_graph(
            {"crm_write": capturing_stage, "notification": notify_stage}, ToolRegistry(), session_factory
        )

    return factory


@pytest.fixture(autouse=True)
def _override_session_factory(db_session_factory):
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    yield
    app.dependency_overrides.clear()


def test_list_pending_reviews_returns_queued_item(client, db_session_factory):
    paused = _create_paused_run(db_session_factory)

    response = client.get("/reviews")

    assert response.status_code == 200
    body = response.json()
    item = next(entry for entry in body if entry["run_id"] == paused.run.run_id)
    assert item["draft_intent_label"] == "browser"
    assert "state_snapshot" not in item


def test_get_review_detail(client, db_session_factory):
    paused = _create_paused_run(db_session_factory)

    response = client.get(f"/reviews/{paused.run.run_id}")

    assert response.status_code == 200
    assert response.json()["lead_id"] == paused.run.lead_id


def test_get_review_detail_404_when_absent(client, db_session_factory):
    response = client.get("/reviews/does-not-exist")

    assert response.status_code == 404


def test_approve_resumes_with_original_label(client, db_session_factory):
    paused = _create_paused_run(db_session_factory)
    capturing = _CapturingCrmWriteStage()
    app.dependency_overrides[get_resume_graph_factory] = lambda: _fake_resume_graph_factory(capturing)

    response = client.post(f"/reviews/{paused.run.run_id}/action", json={"action": "approve"})

    assert response.status_code == 200
    assert response.json()["status"] == RunStatus.RUNNING.value
    assert capturing.received_labels == ["browser"]

    db = db_session_factory()
    try:
        item = db.query(ReviewQueueItem).filter(ReviewQueueItem.run_id == paused.run.run_id).one()
        assert item.status == "ACTIONED"
        assert item.reviewer_action == "approve"
    finally:
        db.close()


def test_edit_resumes_with_corrected_label(client, db_session_factory):
    paused = _create_paused_run(db_session_factory)
    capturing = _CapturingCrmWriteStage()
    app.dependency_overrides[get_resume_graph_factory] = lambda: _fake_resume_graph_factory(capturing)

    response = client.post(
        f"/reviews/{paused.run.run_id}/action",
        json={"action": "edit", "corrected_intent_label": "buyer"},
    )

    assert response.status_code == 200
    assert capturing.received_labels == ["buyer"]

    db = db_session_factory()
    try:
        item = db.query(ReviewQueueItem).filter(ReviewQueueItem.run_id == paused.run.run_id).one()
        assert item.corrected_intent_label == "buyer"
    finally:
        db.close()


def test_edit_requires_corrected_intent_label(client, db_session_factory):
    paused = _create_paused_run(db_session_factory)

    response = client.post(f"/reviews/{paused.run.run_id}/action", json={"action": "edit"})

    assert response.status_code == 422


def test_reject_sets_rejected_status_with_no_further_stage_trace(client, db_session_factory):
    paused = _create_paused_run(db_session_factory)

    response = client.post(f"/reviews/{paused.run.run_id}/action", json={"action": "reject"})

    assert response.status_code == 200
    assert response.json()["status"] == RunStatus.REJECTED.value

    db = db_session_factory()
    try:
        traces = (
            db.query(StageTrace)
            .filter(StageTrace.run_id == paused.run.run_id)
            .order_by(StageTrace.created_at)
            .all()
        )
        assert [t.stage_name for t in traces] == [
            "intake_parsing",
            "intent_classification",
            "data_enrichment",
            "human_review",
        ]

        run_row = db.get(PipelineRun, paused.run.run_id)
        assert run_row.status == RunStatus.REJECTED.value
    finally:
        db.close()


def test_second_action_on_already_actioned_run_returns_409_and_leaves_first_effect_unchanged(
    client, db_session_factory
):
    paused = _create_paused_run(db_session_factory)

    first = client.post(f"/reviews/{paused.run.run_id}/action", json={"action": "reject"})
    assert first.status_code == 200

    second = client.post(f"/reviews/{paused.run.run_id}/action", json={"action": "reject"})
    assert second.status_code == 409

    db = db_session_factory()
    try:
        run_row = db.get(PipelineRun, paused.run.run_id)
        assert run_row.status == RunStatus.REJECTED.value
    finally:
        db.close()
