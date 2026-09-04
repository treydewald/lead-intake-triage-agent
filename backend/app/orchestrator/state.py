from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    REJECTED = "REJECTED"


class IntakeSlice(BaseModel):
    """Feature 02's slice: the normalized lead record."""

    source_channel: str | None = None
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    message_body: str | None = None
    raw_input_ref: str | None = None
    received_at: datetime | None = None
    low_identifiability: bool = False
    empty_message: bool = False


class ClassificationSlice(BaseModel):
    """Feature 03's slice: intent classification result."""

    model_config = {"protected_namespaces": ()}

    intent_label: str | None = None
    confidence_score: float | None = None
    model_used: str | None = None


class EnrichmentSlice(BaseModel):
    """Feature 04's slice: fields resolved via external lookup."""

    resolved_fields: dict[str, Any] = Field(default_factory=dict)
    sources: dict[str, str] = Field(default_factory=dict)
    attempted_fields: list[str] = Field(default_factory=list)
    match_confidence: float | None = None
    conflicts: dict[str, Any] = Field(default_factory=dict)
    lookup_error: str | None = None


class CrmWriteSlice(BaseModel):
    """Feature 05's slice: HubSpot write result."""

    hubspot_record_id: str | None = None
    write_status: str | None = None  # "created" | "updated" — never "failed": a failed
    # write raises instead of returning a slice, see architecture-plan-feature-05.md
    dedupe_key_used: str | None = None
    dedupe_uncertain: bool = False
    retry_count: int = 0


class MergedIntakeEnrichment(BaseModel):
    """Feature 05's read-time merge input: `HubSpotCrmWriteStage.input_slices` names
    `("intake", "enrichment")`, and `_make_node` builds this generically by matching
    field names to slice names — see architecture-plan-feature-05.md."""

    intake: IntakeSlice
    enrichment: EnrichmentSlice


class ReviewSlice(BaseModel):
    """Feature 06's slice: human review queue/action state."""

    queued: bool = False
    reviewer_action: str | None = None  # approve | reject | edit
    corrected_intent_label: str | None = None
    paused_at_stage: str | None = None


class NotificationSlice(BaseModel):
    """Feature 07's slice: outcome notification state."""

    notified: bool = False
    outcome_type: str | None = None


class RunMetadata(BaseModel):
    """Run-level metadata — not owned by any single stage."""

    run_id: str | None = None
    lead_id: str | None = None
    status: RunStatus = RunStatus.RUNNING
    failed_stage: str | None = None
    error: str | None = None


class LeadPipelineState(BaseModel):
    """The full graph state. Each stage reads/writes only its own declared slice,
    named by `Stage.state_slice` — never another stage's slice directly."""

    run: RunMetadata = Field(default_factory=RunMetadata)
    intake: IntakeSlice = Field(default_factory=IntakeSlice)
    classification: ClassificationSlice = Field(default_factory=ClassificationSlice)
    enrichment: EnrichmentSlice = Field(default_factory=EnrichmentSlice)
    crm_write: CrmWriteSlice = Field(default_factory=CrmWriteSlice)
    review: ReviewSlice = Field(default_factory=ReviewSlice)
    notification: NotificationSlice = Field(default_factory=NotificationSlice)
