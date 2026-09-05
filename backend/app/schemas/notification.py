from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    """Response shape for `GET /notifications` — mirrors `ReviewQueueItemOut`'s pattern."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    lead_id: str
    outcome_type: str
    message: str
    detail_link: str
    created_at: datetime
