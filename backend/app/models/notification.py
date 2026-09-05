from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Notification(Base):
    """Feature 07: one persisted in-app notification for a pipeline run's outcome.

    A single-tenant, system-wide inbox item — this project has no `User`/auth model,
    so there is no per-user addressee field (see `.claude/portfolio-reference.md`'s
    Key Decisions / architecture-plan-feature-07.md). `run_id` is not unique the way
    `ReviewQueueItem.run_id` is: a single run can produce more than one notification
    over its lifetime (e.g. an initial `awaiting_review` notification, then a second,
    distinct `auto_processed`/`failed`/`rejected` notification once the reviewer acts).
    """

    __tablename__ = "notification"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_run.id"), index=True)
    lead_id: Mapped[str] = mapped_column(String(36), index=True)
    outcome_type: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    detail_link: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
