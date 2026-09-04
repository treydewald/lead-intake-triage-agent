from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PipelineRun(Base):
    """One execution of the orchestrator graph for a single lead.

    Stage execution/transition data persists here and in `StageTrace` — any future
    stage's execution record belongs to this pair of tables, not a bespoke per-feature
    log table (see `.claude/portfolio-reference.md`'s Key Decisions).
    """

    __tablename__ = "pipeline_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    lead_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(32), default="RUNNING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    stage_traces: Mapped[list["StageTrace"]] = relationship(
        "StageTrace",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="StageTrace.created_at",
    )


class StageTrace(Base):
    """One stage transition within a `PipelineRun` — the persisted trace Feature 08's
    monitoring view reads."""

    __tablename__ = "stage_trace"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_run.id"), index=True)
    stage_name: Mapped[str] = mapped_column(String(64))
    input_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    run: Mapped["PipelineRun"] = relationship("PipelineRun", back_populates="stage_traces")
