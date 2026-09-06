from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.core.config import settings
from app.models.pipeline_run import PipelineRun
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
from app.routers.slack import get_resume_graph_factory, get_session_factory
from main import app

SECRET = "test-signing-secret"


class _FakeStage(Stage):
    """Same test-double shape as `test_router_reviews.py`'s own `_FakeStage` - kept
    self-contained per this project's existing test-file convention rather than shared
    across files."""

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


def _create_paused_run(db_session_factory, lead_id: str = "lead-slack") -> LeadPipelineState:
    graph = build_graph(_paused_stages(confidence=0.2), ToolRegistry(), db_session_factory, confidence_threshold=0.7)
    return run_pipeline(
        lead_id,
        LeadPipelineState(intake=IntakeSlice(source_channel="web_form", message_body="just looking")),
        graph=graph,
        session_factory=db_session_factory,
    )


def _fake_resume_graph_factory():
    crm_write = _FakeStage(
        "hubspot_crm_write", "crm_write", CrmWriteSlice, lambda data, tools: CrmWriteSlice(hubspot_record_id="hs-1")
    )
    notify_stage = _FakeStage(
        "outcome_notification",
        "notification",
        NotificationSlice,
        lambda data, tools: NotificationSlice(notified=True, outcome_type="auto_processed"),
    )

    def factory(session_factory):
        return build_resume_graph({"crm_write": crm_write, "notification": notify_stage}, ToolRegistry(), session_factory)

    return factory


@pytest.fixture(autouse=True)
def _override_session_factory(db_session_factory):
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    yield
    app.dependency_overrides.clear()


def _slack_body(*, action_id: str, run_id: str, username: str | None = "jordan") -> bytes:
    payload = {
        "type": "block_actions",
        "user": {"id": "U123", "username": username},
        "actions": [{"action_id": action_id, "value": run_id}],
    }
    return urlencode({"payload": json.dumps(payload)}).encode()


def _sign(*, secret: str, timestamp: str, body: bytes) -> str:
    basestring = b"v0:" + timestamp.encode() + b":" + body
    return "v0=" + hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()


def _post_signed(client, body: bytes, *, secret: str = SECRET, timestamp: str | None = None, signature: str | None = None):
    ts = timestamp if timestamp is not None else str(int(time.time()))
    sig = signature if signature is not None else _sign(secret=secret, timestamp=ts, body=body)
    return client.post(
        "/slack/interactions",
        content=body,
        headers={
            "X-Slack-Request-Timestamp": ts,
            "X-Slack-Signature": sig,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )


def test_approve_via_slack_resumes_the_run(client, db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "slack_signing_secret", SECRET)
    app.dependency_overrides[get_resume_graph_factory] = _fake_resume_graph_factory
    paused = _create_paused_run(db_session_factory)

    body = _slack_body(action_id="approve_lead", run_id=paused.run.run_id, username="jordan")
    response = _post_signed(client, body)

    assert response.status_code == 200
    assert "jordan" in response.json()["text"]

    db = db_session_factory()
    try:
        run_row = db.get(PipelineRun, paused.run.run_id)
        assert run_row.status == RunStatus.COMPLETED.value
        item = db.query(ReviewQueueItem).filter(ReviewQueueItem.run_id == paused.run.run_id).one()
        assert item.reviewer_name == "jordan"
        assert item.reviewer_action == "approve"
    finally:
        db.close()


def test_reject_via_slack_sets_rejected_status(client, db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "slack_signing_secret", SECRET)
    paused = _create_paused_run(db_session_factory)

    body = _slack_body(action_id="reject_lead", run_id=paused.run.run_id)
    response = _post_signed(client, body)

    assert response.status_code == 200

    db = db_session_factory()
    try:
        run_row = db.get(PipelineRun, paused.run.run_id)
        assert run_row.status == RunStatus.REJECTED.value
    finally:
        db.close()


def test_invalid_signature_is_rejected_before_touching_the_review(client, db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "slack_signing_secret", SECRET)
    paused = _create_paused_run(db_session_factory)

    body = _slack_body(action_id="approve_lead", run_id=paused.run.run_id)
    response = _post_signed(client, body, secret="wrong-secret")

    assert response.status_code == 401

    db = db_session_factory()
    try:
        item = db.query(ReviewQueueItem).filter(ReviewQueueItem.run_id == paused.run.run_id).one()
        assert item.status == "PENDING"
    finally:
        db.close()


def test_stale_timestamp_is_rejected(client, db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "slack_signing_secret", SECRET)
    paused = _create_paused_run(db_session_factory)

    stale_ts = str(int(time.time()) - 600)
    body = _slack_body(action_id="approve_lead", run_id=paused.run.run_id)
    response = _post_signed(client, body, timestamp=stale_ts)

    assert response.status_code == 401


def test_no_signing_secret_configured_rejects_every_request(client, db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "slack_signing_secret", None)
    paused = _create_paused_run(db_session_factory)

    body = _slack_body(action_id="approve_lead", run_id=paused.run.run_id)
    response = _post_signed(client, body, secret="anything")

    assert response.status_code == 401


def test_unrecognized_action_id_returns_400(client, db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "slack_signing_secret", SECRET)
    paused = _create_paused_run(db_session_factory)

    body = _slack_body(action_id="edit_lead", run_id=paused.run.run_id)
    response = _post_signed(client, body)

    assert response.status_code == 400


def test_already_actioned_review_returns_200_with_explanatory_text(client, db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "slack_signing_secret", SECRET)
    paused = _create_paused_run(db_session_factory)

    first = _post_signed(client, _slack_body(action_id="reject_lead", run_id=paused.run.run_id))
    assert first.status_code == 200

    second = _post_signed(client, _slack_body(action_id="reject_lead", run_id=paused.run.run_id))
    assert second.status_code == 200
    assert "already" in second.json()["text"].lower() or "actioned" in second.json()["text"].lower()


def test_nonexistent_run_returns_200_with_explanatory_text(client, db_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "slack_signing_secret", SECRET)

    body = _slack_body(action_id="approve_lead", run_id="no-such-run")
    response = _post_signed(client, body)

    assert response.status_code == 200
    assert "not found" in response.json()["text"].lower()
