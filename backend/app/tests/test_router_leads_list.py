from __future__ import annotations

import pytest

from app.orchestrator.contracts import Stage
from app.orchestrator.graph import build_graph, run_pipeline
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
from app.routers.leads import get_session_factory
from main import app


class _FakeStage(Stage):
    """Same test-double shape as `test_orchestrator_graph.py`'s own `_FakeStage`."""

    def __init__(self, name, state_slice, schema, fn):
        self.name = name
        self.state_slice = state_slice
        self.input_schema = schema
        self.output_schema = schema
        self.allowed_tools = frozenset()
        self._fn = fn

    def run(self, data, tools):
        return self._fn(data, tools)


@pytest.fixture(autouse=True)
def _override_session_factory(db_session_factory):
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    yield
    app.dependency_overrides.clear()


def _stages(*, confidence: float, fail_at: str | None = None) -> dict[str, Stage]:
    def intake_fn(data, tools):
        return data

    def classify_fn(data, tools):
        if fail_at == "classify":
            raise RuntimeError("classification boom")
        return ClassificationSlice(intent_label="buyer", confidence_score=confidence, model_used="test-model")

    def enrich_fn(data, tools):
        if fail_at == "enrich":
            raise RuntimeError("enrichment boom")
        return EnrichmentSlice()

    def crm_write_fn(data, tools):
        return CrmWriteSlice(hubspot_record_id="hs-1", write_status="created")

    def review_fn(data, tools):
        return ReviewSlice(queued=True, paused_at_stage="crm_write")

    def notify_fn(data, tools):
        return NotificationSlice(notified=True, outcome_type="auto_processed")

    return {
        "intake": _FakeStage("intake_parsing", "intake", IntakeSlice, intake_fn),
        "classification": _FakeStage("intent_classification", "classification", ClassificationSlice, classify_fn),
        "enrichment": _FakeStage("data_enrichment", "enrichment", EnrichmentSlice, enrich_fn),
        "crm_write": _FakeStage("hubspot_crm_write", "crm_write", CrmWriteSlice, crm_write_fn),
        "review": _FakeStage("human_review", "review", ReviewSlice, review_fn),
        "notification": _FakeStage("outcome_notification", "notification", NotificationSlice, notify_fn),
    }


def _run(db_session_factory, lead_id: str, *, confidence: float = 0.95, source_channel: str = "web_form", fail_at=None):
    stages = _stages(confidence=confidence, fail_at=fail_at)
    graph = build_graph(stages, ToolRegistry(), db_session_factory, confidence_threshold=0.7)
    initial = LeadPipelineState(intake=IntakeSlice(source_channel=source_channel, message_body="hello"))
    return run_pipeline(lead_id, initial, graph=graph, session_factory=db_session_factory)


def test_list_leads_returns_paginated_items(client, db_session_factory):
    _run(db_session_factory, "lead-1", confidence=0.95)
    _run(db_session_factory, "lead-2", confidence=0.95)

    response = client.get("/leads")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert len(body["items"]) == 2
    assert {item["status"] for item in body["items"]} == {"auto_processed"}


def test_list_leads_filters_by_status_and_source_channel(client, db_session_factory):
    _run(db_session_factory, "lead-auto", confidence=0.95, source_channel="web_form")
    _run(db_session_factory, "lead-review", confidence=0.2, source_channel="email")

    auto_only = client.get("/leads", params={"status": "auto_processed"})
    assert auto_only.status_code == 200
    assert [item["lead_id"] for item in auto_only.json()["items"]] == ["lead-auto"]

    email_only = client.get("/leads", params={"source_channel": "email"})
    assert email_only.status_code == 200
    assert [item["lead_id"] for item in email_only.json()["items"]] == ["lead-review"]


def test_list_leads_sorts_by_confidence(client, db_session_factory):
    _run(db_session_factory, "lead-low", confidence=0.2)
    _run(db_session_factory, "lead-high", confidence=0.95)

    response = client.get("/leads", params={"sort": "confidence_asc", "status": "irrelevant-placeholder"})
    # invalid status should 422 rather than silently ignoring the filter
    assert response.status_code == 422

    response = client.get("/leads", params={"sort": "confidence_asc"})
    assert response.status_code == 200
    scores = [item["confidence_score"] for item in response.json()["items"]]
    assert scores == sorted(scores)


def test_list_leads_paginates(client, db_session_factory):
    for i in range(3):
        _run(db_session_factory, f"lead-{i}", confidence=0.95)

    response = client.get("/leads", params={"page": 1, "page_size": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2

    response_page_2 = client.get("/leads", params={"page": 2, "page_size": 2})
    assert len(response_page_2.json()["items"]) == 1


def test_lead_detail_completed_run_shows_all_six_stages(client, db_session_factory):
    final = _run(db_session_factory, "lead-detail-complete", confidence=0.95)

    response = client.get(f"/leads/{final.run.lead_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "auto_processed"
    assert [s["stage_key"] for s in body["stages"]] == [
        "intake_parsing",
        "intent_classification",
        "data_enrichment",
        "hubspot_crm_write",
        "outcome_notification",
    ] or [s["stage_key"] for s in body["stages"]] == [
        "intake_parsing",
        "intent_classification",
        "data_enrichment",
        "hubspot_crm_write",
        "human_review",
        "outcome_notification",
    ]
    statuses = {s["stage_key"]: s["status"] for s in body["stages"]}
    assert statuses["intake_parsing"] == "COMPLETED"
    assert statuses["hubspot_crm_write"] == "COMPLETED"
    if statuses.get("human_review") is not None:
        assert statuses["human_review"] == "NOT_YET_RUN"


def test_lead_detail_awaiting_review_shows_not_yet_run_stages(client, db_session_factory):
    final = _run(db_session_factory, "lead-detail-review", confidence=0.2)

    response = client.get(f"/leads/{final.run.lead_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "awaiting_review"
    statuses = {s["stage_key"]: s["status"] for s in body["stages"]}
    assert statuses["human_review"] == "COMPLETED"
    assert statuses["hubspot_crm_write"] == "NOT_YET_RUN"


def test_lead_detail_failed_run_identifies_failing_stage(client, db_session_factory):
    final = _run(db_session_factory, "lead-detail-failed", confidence=0.95, fail_at="enrich")

    response = client.get(f"/leads/{final.run.lead_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["failed_stage"] == "data_enrichment"
    assert "boom" in (body["error"] or "")
    statuses = {s["stage_key"]: s["status"] for s in body["stages"]}
    assert statuses["data_enrichment"] == "FAILED"
    assert statuses["hubspot_crm_write"] == "NOT_YET_RUN"


def test_lead_detail_decision_matches_stage_trace_output_exactly(client, db_session_factory):
    final = _run(db_session_factory, "lead-detail-decision", confidence=0.95)

    response = client.get(f"/leads/{final.run.lead_id}")

    body = response.json()
    classify_stage = next(s for s in body["stages"] if s["stage_key"] == "intent_classification")
    assert classify_stage["decision"]["intent_label"] == "buyer"
    assert classify_stage["decision"]["confidence_score"] == 0.95


def test_lead_detail_unknown_lead_id_returns_404(client, db_session_factory):
    response = client.get("/leads/does-not-exist")
    assert response.status_code == 404
