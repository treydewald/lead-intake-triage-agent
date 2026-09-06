from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.pipeline_run import PipelineRun
from app.models.review_queue import ReviewQueueItem
from app.orchestrator.state import RunStatus
from app.routers.analytics import get_session_factory
from main import app

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _override_session_factory(db_session_factory):
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    yield
    app.dependency_overrides.clear()


def _add_run(
    db,
    *,
    lead_id: str,
    status: str,
    source_channel: str | None,
    confidence_score: float | None,
    created_at: datetime,
    updated_at: datetime,
) -> PipelineRun:
    run = PipelineRun(
        lead_id=lead_id,
        status=status,
        source_channel=source_channel,
        confidence_score=confidence_score,
        created_at=created_at,
        updated_at=updated_at,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def test_funnel_returns_zero_state_for_empty_database(client, db_session_factory):
    response = client.get("/analytics/funnel")

    assert response.status_code == 200
    body = response.json()
    assert body["total_leads"] == 0
    assert body["by_status"] == []
    assert body["by_source_channel"] == []
    assert body["avg_resolution_seconds"] is None
    assert body["reviewer_throughput"] == []


def test_funnel_counts_by_status_sum_to_total_leads(client, db_session_factory):
    db = db_session_factory()
    try:
        _add_run(
            db,
            lead_id="lead-1",
            status=RunStatus.COMPLETED.value,
            source_channel="web_form",
            confidence_score=0.9,
            created_at=BASE,
            updated_at=BASE + timedelta(seconds=10),
        )
        _add_run(
            db,
            lead_id="lead-2",
            status=RunStatus.FAILED.value,
            source_channel="email",
            confidence_score=None,
            created_at=BASE,
            updated_at=BASE + timedelta(seconds=5),
        )
        _add_run(
            db,
            lead_id="lead-3",
            status=RunStatus.RUNNING.value,
            source_channel="web_form",
            confidence_score=None,
            created_at=BASE,
            updated_at=BASE,
        )
    finally:
        db.close()

    response = client.get("/analytics/funnel")

    assert response.status_code == 200
    body = response.json()
    assert body["total_leads"] == 3
    assert sum(entry["count"] for entry in body["by_status"]) == 3
    status_counts = {entry["status"]: entry["count"] for entry in body["by_status"]}
    assert status_counts == {"auto_processed": 1, "failed": 1, "in_progress": 1}


def test_funnel_avg_resolution_excludes_unresolved_runs(client, db_session_factory):
    db = db_session_factory()
    try:
        _add_run(
            db,
            lead_id="lead-resolved-1",
            status=RunStatus.COMPLETED.value,
            source_channel="web_form",
            confidence_score=0.9,
            created_at=BASE,
            updated_at=BASE + timedelta(seconds=10),
        )
        _add_run(
            db,
            lead_id="lead-resolved-2",
            status=RunStatus.REJECTED.value,
            source_channel="web_form",
            confidence_score=0.2,
            created_at=BASE,
            updated_at=BASE + timedelta(seconds=30),
        )
        _add_run(
            db,
            lead_id="lead-unresolved",
            status=RunStatus.AWAITING_REVIEW.value,
            source_channel="web_form",
            confidence_score=0.3,
            created_at=BASE,
            updated_at=BASE + timedelta(hours=5),
        )
    finally:
        db.close()

    response = client.get("/analytics/funnel")

    assert response.status_code == 200
    # Average of 10s and 30s only - the AWAITING_REVIEW run's 5-hour gap must not skew this.
    assert response.json()["avg_resolution_seconds"] == pytest.approx(20.0)


def test_funnel_source_channel_avg_confidence_ignores_null_scores(client, db_session_factory):
    db = db_session_factory()
    try:
        _add_run(
            db,
            lead_id="lead-a",
            status=RunStatus.COMPLETED.value,
            source_channel="email",
            confidence_score=0.8,
            created_at=BASE,
            updated_at=BASE,
        )
        _add_run(
            db,
            lead_id="lead-b",
            status=RunStatus.RUNNING.value,
            source_channel="email",
            confidence_score=None,
            created_at=BASE,
            updated_at=BASE,
        )
        _add_run(
            db,
            lead_id="lead-c",
            status=RunStatus.COMPLETED.value,
            source_channel=None,
            confidence_score=0.5,
            created_at=BASE,
            updated_at=BASE,
        )
    finally:
        db.close()

    response = client.get("/analytics/funnel")

    assert response.status_code == 200
    by_channel = {entry["source_channel"]: entry for entry in response.json()["by_source_channel"]}
    assert by_channel["email"]["count"] == 2
    assert by_channel["email"]["avg_confidence"] == pytest.approx(0.8)
    assert by_channel["unknown"]["count"] == 1


def test_reviewer_throughput_excludes_pending_and_groups_unattributed(client, db_session_factory):
    db = db_session_factory()
    try:
        run_a = _add_run(
            db,
            lead_id="lead-a",
            status=RunStatus.COMPLETED.value,
            source_channel="web_form",
            confidence_score=0.5,
            created_at=BASE,
            updated_at=BASE,
        )
        run_b = _add_run(
            db,
            lead_id="lead-b",
            status=RunStatus.REJECTED.value,
            source_channel="web_form",
            confidence_score=0.4,
            created_at=BASE,
            updated_at=BASE,
        )
        run_c = _add_run(
            db,
            lead_id="lead-c",
            status=RunStatus.AWAITING_REVIEW.value,
            source_channel="web_form",
            confidence_score=0.3,
            created_at=BASE,
            updated_at=BASE,
        )
        db.add(
            ReviewQueueItem(
                run_id=run_a.id,
                lead_id="lead-a",
                status="ACTIONED",
                reviewer_name="Alice",
                state_snapshot="{}",
                created_at=BASE,
                actioned_at=BASE + timedelta(seconds=60),
            )
        )
        db.add(
            ReviewQueueItem(
                run_id=run_b.id,
                lead_id="lead-b",
                status="ACTIONED",
                reviewer_name=None,
                state_snapshot="{}",
                created_at=BASE,
                actioned_at=BASE + timedelta(seconds=120),
            )
        )
        db.add(
            ReviewQueueItem(
                run_id=run_c.id,
                lead_id="lead-c",
                status="PENDING",
                reviewer_name="Alice",
                state_snapshot="{}",
                created_at=BASE,
                actioned_at=None,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/analytics/funnel")

    assert response.status_code == 200
    throughput = {entry["reviewer_name"]: entry for entry in response.json()["reviewer_throughput"]}
    assert set(throughput.keys()) == {"Alice", "Unattributed"}
    assert throughput["Alice"]["actioned_count"] == 1
    assert throughput["Alice"]["avg_resolution_seconds"] == pytest.approx(60.0)
    assert throughput["Unattributed"]["actioned_count"] == 1
    assert throughput["Unattributed"]["avg_resolution_seconds"] == pytest.approx(120.0)
