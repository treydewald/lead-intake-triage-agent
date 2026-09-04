from __future__ import annotations

import pytest

from app.routers.leads import get_session_factory
from main import app


@pytest.fixture(autouse=True)
def _override_session_factory(db_session_factory):
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    yield
    app.dependency_overrides.clear()


def test_webform_endpoint_creates_a_pipeline_run(client):
    response = client.post(
        "/leads/webform",
        json={
            "source_channel": "web_form",
            "name": "Jane Doe",
            "phone": "555-123-4567",
            "email": "jane@example.com",
            "message_body": "I want to buy now",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lead_id"]
    # Classification (Feature 03) is still a stub, so the run halts there - intake itself
    # must show as having completed successfully with the normalized record.
    stage_names = [t["stage_name"] for t in body["stage_traces"]]
    assert "intake_parsing" in stage_names
    intake_trace = next(t for t in body["stage_traces"] if t["stage_name"] == "intake_parsing")
    assert intake_trace["status"] == "COMPLETED"


def test_email_endpoint_creates_a_pipeline_run(client):
    response = client.post(
        "/leads/email",
        json={"raw_text": "From: Jane Doe <jane@example.com>\nSubject: Hi\n\nInterested, please call me."},
    )

    assert response.status_code == 200
    body = response.json()
    intake_trace = next(t for t in body["stage_traces"] if t["stage_name"] == "intake_parsing")
    assert intake_trace["status"] == "COMPLETED"


def test_callback_endpoint_creates_a_pipeline_run(client):
    response = client.post(
        "/leads/callback",
        json={"transcript": "Hi, call me back at 555-987-6543, thanks."},
    )

    assert response.status_code == 200
    body = response.json()
    intake_trace = next(t for t in body["stage_traces"] if t["stage_name"] == "intake_parsing")
    assert intake_trace["status"] == "COMPLETED"
