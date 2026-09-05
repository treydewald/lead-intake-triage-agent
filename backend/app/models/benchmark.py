from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BenchmarkRun(Base):
    """Feature 09: one execution of the classification accuracy benchmark harness.

    `accuracy`/`consistency` are pre-aggregated at write time by `app/benchmark/harness.py`
    (attempt-level and item-level respectively — see that module's docstring) so the list
    view never recomputes them from `BenchmarkCase.attempts_json` per request.
    """

    __tablename__ = "benchmark_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    model_used: Mapped[str] = mapped_column(String(64))
    repeats: Mapped[int] = mapped_column(Integer)
    total_cases: Mapped[int] = mapped_column(Integer)
    accuracy: Mapped[float] = mapped_column(Float)
    consistency: Mapped[float] = mapped_column(Float)

    cases: Mapped[list["BenchmarkCase"]] = relationship(
        "BenchmarkCase",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="BenchmarkCase.case_id",
    )


class BenchmarkCase(Base):
    """One dataset item's result within a `BenchmarkRun`.

    `attempts_json` holds every repeat's raw `{label, confidence}` result (the source of
    truth the run-level `accuracy`/`consistency` were aggregated from). `correct`/`confidence`
    on this row reflect the *first* attempt only — the representative prediction shown in the
    per-case failure table (architecture-plan-feature-09.md's Implementation Order, step 4);
    `correct` is `None` for ambiguous items, which have no ground-truth label to score against.
    """

    __tablename__ = "benchmark_case"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("benchmark_run.id"), index=True)
    case_id: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32))
    expected_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_ambiguous: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts_json: Mapped[str] = mapped_column(Text)
    predicted_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    consistent: Mapped[bool] = mapped_column(Boolean)

    run: Mapped["BenchmarkRun"] = relationship("BenchmarkRun", back_populates="cases")
