from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends

from app.database.session import SessionLocal
from app.models.pipeline_run import PipelineRun
from app.models.review_queue import ReviewQueueItem
from app.schemas.analytics import (
    FunnelChannelStatOut,
    FunnelDashboardOut,
    FunnelStatusCountOut,
    ReviewerThroughputOut,
)
from app.schemas.pipeline import display_status_for

router = APIRouter(prefix="/analytics", tags=["analytics"])

SessionFactory = Callable[[], object]

# A run's outcome is resolved (has reached a terminal state) once its raw `PipelineRun.status`
# is one of these — RUNNING/AWAITING_REVIEW haven't resolved yet and are excluded from
# `avg_resolution_seconds`, per architecture-plan-feature-18.md.
_RESOLVED_STATUSES = {"COMPLETED", "FAILED", "REJECTED"}


def get_session_factory() -> SessionFactory:
    """FastAPI dependency, overridden in tests — same pattern every other router uses."""
    return SessionLocal


@router.get("/funnel", response_model=FunnelDashboardOut)
def get_funnel_dashboard(session_factory: SessionFactory = Depends(get_session_factory)) -> FunnelDashboardOut:
    """Feature 18: aggregate lead funnel / reviewer throughput, computed directly from
    existing `PipelineRun`/`ReviewQueueItem` rows — no new columns, no new tables, see
    architecture-plan-feature-18.md."""
    db = session_factory()
    try:
        runs = db.query(PipelineRun).all()

        status_counts: dict[str, int] = {}
        channel_counts: dict[str, int] = {}
        channel_confidence_sums: dict[str, float] = {}
        channel_confidence_n: dict[str, int] = {}
        resolution_seconds: list[float] = []

        for run in runs:
            display_status = display_status_for(run.status)
            status_counts[display_status] = status_counts.get(display_status, 0) + 1

            channel = run.source_channel or "unknown"
            channel_counts[channel] = channel_counts.get(channel, 0) + 1
            if run.confidence_score is not None:
                channel_confidence_sums[channel] = channel_confidence_sums.get(channel, 0.0) + run.confidence_score
                channel_confidence_n[channel] = channel_confidence_n.get(channel, 0) + 1

            if run.status in _RESOLVED_STATUSES:
                resolution_seconds.append((run.updated_at - run.created_at).total_seconds())

        by_status = [
            FunnelStatusCountOut(status=status, count=count) for status, count in sorted(status_counts.items())
        ]
        by_source_channel = [
            FunnelChannelStatOut(
                source_channel=channel,
                count=count,
                avg_confidence=(
                    channel_confidence_sums[channel] / channel_confidence_n[channel]
                    if channel in channel_confidence_n
                    else None
                ),
            )
            for channel, count in sorted(channel_counts.items())
        ]
        avg_resolution_seconds = (
            sum(resolution_seconds) / len(resolution_seconds) if resolution_seconds else None
        )

        reviewer_seconds: dict[str, list[float]] = {}
        reviewer_actioned_counts: dict[str, int] = {}
        for item in db.query(ReviewQueueItem).filter(ReviewQueueItem.status == "ACTIONED").all():
            reviewer = item.reviewer_name or "Unattributed"
            reviewer_actioned_counts[reviewer] = reviewer_actioned_counts.get(reviewer, 0) + 1
            reviewer_seconds.setdefault(reviewer, [])
            if item.actioned_at is not None:
                reviewer_seconds[reviewer].append((item.actioned_at - item.created_at).total_seconds())

        reviewer_throughput = [
            ReviewerThroughputOut(
                reviewer_name=reviewer,
                actioned_count=reviewer_actioned_counts[reviewer],
                avg_resolution_seconds=(sum(seconds) / len(seconds) if seconds else None),
            )
            for reviewer, seconds in sorted(reviewer_seconds.items())
        ]

        return FunnelDashboardOut(
            total_leads=len(runs),
            by_status=by_status,
            by_source_channel=by_source_channel,
            avg_resolution_seconds=avg_resolution_seconds,
            reviewer_throughput=reviewer_throughput,
        )
    finally:
        db.close()
