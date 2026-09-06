from __future__ import annotations

from pydantic import BaseModel


class FunnelStatusCountOut(BaseModel):
    status: str
    count: int


class FunnelChannelStatOut(BaseModel):
    source_channel: str
    count: int
    avg_confidence: float | None = None


class ReviewerThroughputOut(BaseModel):
    reviewer_name: str
    actioned_count: int
    avg_resolution_seconds: float | None = None


class FunnelDashboardOut(BaseModel):
    """Feature 18: aggregate lead funnel / reviewer throughput view — every field is
    computed directly from existing `PipelineRun`/`ReviewQueueItem` rows, see
    `app/routers/analytics.py` and architecture-plan-feature-18.md."""

    total_leads: int
    by_status: list[FunnelStatusCountOut]
    by_source_channel: list[FunnelChannelStatOut]
    avg_resolution_seconds: float | None = None
    reviewer_throughput: list[ReviewerThroughputOut]
