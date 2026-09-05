from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ReviewActionRequest(BaseModel):
    """Body for `POST /reviews/{run_id}/action`. `corrected_intent_label` is required
    only when `action == "edit"` - validated in the route, not here, so the field stays
    genuinely optional for approve/reject (see architecture-plan-feature-06.md, step 6)."""

    action: Literal["approve", "reject", "edit"]
    corrected_intent_label: str | None = None
    reviewer_name: str | None = None


class ReviewQueueItemOut(BaseModel):
    """Reviewer-facing shape. Deliberately excludes `state_snapshot` (internal resume
    payload) and `status`/`reviewer_action` (only meaningful once actioned, and this
    listing is PENDING-only)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    lead_id: str
    draft_intent_label: str | None = None
    confidence_score: float | None = None
    created_at: datetime
