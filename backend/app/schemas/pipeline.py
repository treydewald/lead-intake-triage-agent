from __future__ import annotations

from datetime import datetime

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
