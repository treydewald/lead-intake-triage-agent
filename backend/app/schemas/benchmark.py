from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BenchmarkCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: str
    category: str
    expected_label: str | None
    is_ambiguous: bool
    predicted_label: str | None
    confidence: float | None
    correct: bool | None
    consistent: bool


class BenchmarkRunSummaryOut(BaseModel):
    """List view: one row per run, no per-case detail — see `BenchmarkRunOut` for that."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: str
    created_at: datetime
    model_used: str
    repeats: int
    total_cases: int
    accuracy: float
    consistency: float


class BenchmarkRunOut(BenchmarkRunSummaryOut):
    """Detail view: summary fields plus every case, including every misclassified one —
    never filtered down to the aggregate score alone, per the feature spec's acceptance
    criteria."""

    cases: list[BenchmarkCaseOut]


class BenchmarkRunListOut(BaseModel):
    items: list[BenchmarkRunSummaryOut]


class ConfidenceThresholdOut(BaseModel):
    """Feature 17: the live `Settings.confidence_threshold` value, read-only — the one
    piece of backend config the What-If Simulator needs to show a "current" baseline
    alongside a candidate threshold. See architecture-plan-feature-17.md."""

    confidence_threshold: float
