from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReviewQueueItem(Base):
    """Feature 06: one reviewer-actionable task for a run paused at Human Review.

    Distinct from `PipelineRun`/`StageTrace` (an execution *log*) — this is a
    domain-specific task queue carrying its own resume payload (`state_snapshot`)
    and reviewer decision, not a stretch of the execution-log tables. `status` is
    deliberately a two-value gate (`PENDING`/`ACTIONED`): the actual outcome lives in
    `reviewer_action`, so `status` only needs to answer "has this been claimed yet."
    See `.claude/portfolio-reference.md`'s Key Decisions
    (`architecture-plan-feature-06.md`).
    """

    __tablename__ = "review_queue_item"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_run.id"), unique=True, index=True)
    lead_id: Mapped[str] = mapped_column(String(36), index=True)
    draft_intent_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    reviewer_action: Mapped[str | None] = mapped_column(String(16), nullable=True)
    corrected_intent_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state_snapshot: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    actioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
