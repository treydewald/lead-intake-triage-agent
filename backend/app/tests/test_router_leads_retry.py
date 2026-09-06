from __future__ import annotations

import pytest

from app.models.pipeline_run import PipelineRun
from app.orchestrator.contracts import Stage
from app.orchestrator.graph import build_graph, build_retry_graph, run_pipeline
from app.orchestrator.state import (
    ClassificationSlice,
    CrmWriteSlice,
    EnrichmentSlice,
    IntakeSlice,
    LeadPipelineState,
    NotificationSlice,
    ReviewSlice,
    RunStatus,
)
from app.orchestrator.tool_scope import ToolRegistry
from app.routers.leads import get_retry_graph_factory, get_session_factory
from main import app


class _FakeStage(Stage):
    def __init__(self, name, state_slice, schema, fn):
        self.name = name
        self.state_slice = state_slice
        self.input_schema = schema
        self.output_schema = schema
        self.allowed_tools = frozenset()
        self._fn = fn

    def run(self, data, tools):
        return self._fn(data, tools)


def _make_stages(*, fail_at: str | None) -> dict[str, Stage]:
    def crm_write_fn(data, tools):
        if fail_at == "crm_write":
            raise RuntimeError("hubspot write boom")
        return CrmWriteSlice(hubspot_record_id="hs-1", write_status="created")

    return {
        "intake": _FakeStage("intake_parsing", "intake", IntakeSlice, lambda data, tools: data),
        "classification": _FakeStage(
            "intent_classification",
            "classification",
            ClassificationSlice,
            lambda data, tools: ClassificationSlice(
                intent_label="buyer", confidence_score=0.95, model_used="test-model"
            ),
        ),
        "enrichment": _FakeStage(
            "data_enrichment", "enrichment", EnrichmentSlice, lambda data, tools: EnrichmentSlice()
        ),
        "crm_write": _FakeStage("hubspot_crm_write", "crm_write", CrmWriteSlice, crm_write_fn),
        "review": _FakeStage(
            "human_review", "review", ReviewSlice, lambda data, tools: ReviewSlice(queued=True)
        ),
        "notification": _FakeStage(
            "outcome_notification",
            "notification",
            NotificationSlice,
            lambda data, tools: NotificationSlice(notified=True, outcome_type="auto_processed"),
        ),
    }


def _create_failed_lead(db_session_factory, lead_id: str = "lead-router-retry") -> LeadPipelineState:
    graph = build_graph(_make_stages(fail_at="crm_write"), ToolRegistry(), db_session_factory, confidence_threshold=0.7)
    final = run_pipeline(
        lead_id,
        LeadPipelineState(intake=IntakeSlice(source_channel="web_form", message_body="I want to buy now")),
        graph=graph,
        session_factory=db_session_factory,
    )
    assert final.run.status == RunStatus.FAILED
    return final


@pytest.fixture(autouse=True)
def _override_session_factory(db_session_factory):
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    yield
    app.dependency_overrides.clear()


def _fake_retry_graph_factory(*, fail_again: bool = False):
    def factory(start_stage: str, session_factory):
        return build_retry_graph(
            start_stage, _make_stages(fail_at="crm_write" if fail_again else None), ToolRegistry(), session_factory,
            confidence_threshold=0.7,
        )

    return lambda: factory


def test_retry_succeeds_and_creates_a_new_completed_run(client, db_session_factory):
    failed = _create_failed_lead(db_session_factory)
    app.dependency_overrides[get_retry_graph_factory] = _fake_retry_graph_factory()

    response = client.post(f"/leads/{failed.run.lead_id}/retry")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == RunStatus.COMPLETED.value
    assert body["id"] != failed.run.run_id

    db = db_session_factory()
    try:
        assert db.query(PipelineRun).filter(PipelineRun.lead_id == failed.run.lead_id).count() == 2
    finally:
        db.close()


def test_retry_with_no_failed_run_returns_409(client, db_session_factory):
    response = client.post("/leads/no-such-lead/retry")

    assert response.status_code == 409


def test_get_lead_detail_reflects_latest_attempt_after_retry(client, db_session_factory):
    failed = _create_failed_lead(db_session_factory)
    app.dependency_overrides[get_retry_graph_factory] = _fake_retry_graph_factory()

    retry_response = client.post(f"/leads/{failed.run.lead_id}/retry")
    assert retry_response.status_code == 200
    new_run_id = retry_response.json()["id"]

    detail_response = client.get(f"/leads/{failed.run.lead_id}")

    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["run_id"] == new_run_id
    assert body["status"] == "auto_processed"


def test_lead_history_shows_both_attempts_after_retry(client, db_session_factory):
    failed = _create_failed_lead(db_session_factory)
    app.dependency_overrides[get_retry_graph_factory] = _fake_retry_graph_factory()

    retry_response = client.post(f"/leads/{failed.run.lead_id}/retry")
    new_run_id = retry_response.json()["id"]

    history_response = client.get(f"/leads/{failed.run.lead_id}/history")

    assert history_response.status_code == 200
    run_ids_in_history = {entry["run_id"] for entry in history_response.json()["entries"]}
    assert failed.run.run_id in run_ids_in_history
    assert new_run_id in run_ids_in_history
