from __future__ import annotations

import pytest

from app.models.notification import Notification
from app.models.pipeline_run import PipelineRun
from app.orchestrator.state import RunStatus
from app.routers.notifications import get_session_factory
from main import app


@pytest.fixture(autouse=True)
def _override_session_factory(db_session_factory):
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    yield
    app.dependency_overrides.clear()


def _seed_run_and_notifications(db_session_factory) -> str:
    db = db_session_factory()
    try:
        run = PipelineRun(lead_id="lead-1", status=RunStatus.COMPLETED.value)
        db.add(run)
        db.commit()
        db.refresh(run)

        db.add(
            Notification(
                run_id=run.id,
                lead_id="lead-1",
                outcome_type="awaiting_review",
                message="Lead Jane Doe is awaiting human review.",
                detail_link=f"/reviews/{run.id}",
            )
        )
        db.commit()
        db.add(
            Notification(
                run_id=run.id,
                lead_id="lead-1",
                outcome_type="auto_processed",
                message="Lead Jane Doe was auto-processed and written to CRM.",
                detail_link="/leads/lead-1",
            )
        )
        db.commit()
        return run.id
    finally:
        db.close()


def test_list_notifications_returns_newest_first(client, db_session_factory):
    run_id = _seed_run_and_notifications(db_session_factory)

    response = client.get("/notifications")

    assert response.status_code == 200
    body = response.json()
    matching = [n for n in body if n["run_id"] == run_id]
    assert [n["outcome_type"] for n in matching] == ["auto_processed", "awaiting_review"]


def test_list_notifications_empty_when_none_created(client, db_session_factory):
    response = client.get("/notifications")

    assert response.status_code == 200
    assert response.json() == []
