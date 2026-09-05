from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class TriggerPipelineRunRequest(BaseModel):
    """Request shape for triggering a pipeline run from a normalized lead record
    (Feature 02's output). Reused as-is for the web-form intake channel."""

    source_channel: str
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    message_body: str | None = None
    raw_input_ref: str | None = None


class EmailIntakeRequest(BaseModel):
    """Raw inbound email text — Feature 02's email intake channel."""

    raw_text: str
    raw_input_ref: str | None = None


class CallbackIntakeRequest(BaseModel):
    """Missed-call callback transcript — Feature 02's callback intake channel."""

    transcript: str
    raw_input_ref: str | None = None


class StageTraceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    stage_name: str
    status: str
    error: str | None = None
    created_at: datetime


class PipelineRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lead_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    stage_traces: list[StageTraceOut] = []


# Feature 08: a `PipelineRun`'s post-persistence display status, computed for any
# read-only view built after a run has terminated or paused. Deliberately separate
# from `outcome_notification.py`'s `_OUTCOME_TYPE_BY_STATUS` — that map is evaluated at
# `notify_stage`/`persist_outcome_notification` call time, before `RunStatus.COMPLETED`
# is ever assigned, so it has no `COMPLETED` entry and treats `RUNNING` as the success
# case. This map answers a different question (what does this row's status mean *now*,
# read back after the fact) and must never be unified with that one — see
# `.claude/portfolio-reference.md`'s Key Decisions (architecture-plan-feature-08.md).
_DISPLAY_STATUS_BY_RUN_STATUS: dict[str, str] = {
    "COMPLETED": "auto_processed",
    "FAILED": "failed",
    "AWAITING_REVIEW": "awaiting_review",
    "REJECTED": "rejected",
    "RUNNING": "in_progress",
}


def display_status_for(run_status: str) -> str:
    """Map a `PipelineRun.status` value to the display status shown in the monitoring
    view (Feature 08). See `_DISPLAY_STATUS_BY_RUN_STATUS` above for why this is a
    separate function from Feature 07's notification-time outcome mapping."""
    return _DISPLAY_STATUS_BY_RUN_STATUS.get(run_status, run_status.lower())


_RUN_STATUS_BY_DISPLAY_STATUS: dict[str, str] = {v: k for k, v in _DISPLAY_STATUS_BY_RUN_STATUS.items()}


def run_status_for_display(display_status: str) -> str | None:
    """Inverse of `display_status_for` — used by `GET /leads`'s `status` filter, which
    accepts the same display-status vocabulary the list/detail responses use, not the
    raw `PipelineRun.status` enum values."""
    return _RUN_STATUS_BY_DISPLAY_STATUS.get(display_status)


class LeadListItemOut(BaseModel):
    lead_id: str
    run_id: str
    status: str
    source_channel: str | None = None
    confidence_score: float | None = None
    created_at: datetime
    updated_at: datetime


class LeadListOut(BaseModel):
    items: list[LeadListItemOut]
    total: int
    page: int
    page_size: int


class StageDetailOut(BaseModel):
    stage_key: str
    stage_label: str
    status: str  # "COMPLETED" | "FAILED" | "NOT_YET_RUN"
    decision: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime | None = None


class LeadDetailOut(BaseModel):
    lead_id: str
    run_id: str
    status: str
    source_channel: str | None = None
    confidence_score: float | None = None
    created_at: datetime
    updated_at: datetime
    failed_stage: str | None = None
    error: str | None = None
    stages: list[StageDetailOut]
