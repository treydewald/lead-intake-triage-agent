from __future__ import annotations

import json
from typing import Callable

from app.benchmark.dataset import BENCHMARK_DATASET, DatasetItem
from app.core.config import Settings, settings as default_settings
from app.database.session import SessionLocal
from app.models.benchmark import BenchmarkCase, BenchmarkRun
from app.orchestrator.stages.intent_classification import IntentClassificationStage
from app.orchestrator.tool_scope import ToolRegistry
from app.orchestrator.tools import register_default_tools

SessionFactory = Callable[[], object]

_STAGE = IntentClassificationStage()


def _run_one_attempt(item: DatasetItem, proxy: object) -> dict[str, object]:
    """Invoke the real stage for one attempt. A raised exception or the stage's own
    `None`-label failure sentinels count as a failed attempt (label=None), never
    excluded — see architecture-plan-feature-09.md's accuracy definition."""
    try:
        result = _STAGE.run(item.intake, proxy)  # type: ignore[arg-type]
    except Exception:
        return {"label": None, "confidence": None}
    return {"label": result.intent_label, "confidence": result.confidence_score}


def run_benchmark(
    repeats: int = 3,
    session_factory: SessionFactory = SessionLocal,
    settings: Settings = default_settings,
) -> BenchmarkRun:
    """Exercise Feature 03's real `IntentClassificationStage` against the labeled
    dataset, `repeats` times per item, and persist the aggregated result.

    Builds one `ToolRegistry` + `register_default_tools(registry, settings)` for the
    whole run (matching production's one-registry-per-process pattern, not once per
    case) and invokes the stage exactly as the orchestrator's `_make_node` does — no
    classification logic is reimplemented, per architecture-plan-feature-09.md's
    Architecture Rule Change.

    Per-run metrics:
    - Accuracy = correct attempts / total attempts, where "total attempts" is
      non-ambiguous items x `repeats`. A failed attempt (exception or None-label
      sentinel) always counts against accuracy, never excluded.
    - Consistency = items whose `repeats` attempts all produced the identical
      `intent_label` / total items (ambiguous items included — label stability is
      meaningful even without a ground-truth answer; a failed attempt breaks
      consistency for that item).

    Each persisted `BenchmarkCase` additionally records the *first* attempt's label/
    confidence as `predicted_label`/`confidence` — the single representative
    prediction shown in the per-case failure table (`correct` compares this first
    attempt to `expected_label`; `None` for ambiguous items, which have no ground
    truth to score against). This is a display simplification only: the run-level
    `accuracy` above is always computed from every attempt, not just the first.
    """
    registry = ToolRegistry()
    register_default_tools(registry, settings)
    proxy = registry.scoped_proxy(_STAGE.allowed_tools, _STAGE.name)

    correct_attempts = 0
    total_attempts = 0
    consistent_items = 0

    case_rows: list[BenchmarkCase] = []
    for item in BENCHMARK_DATASET:
        attempts = [_run_one_attempt(item, proxy) for _ in range(repeats)]

        is_ambiguous = item.expected_label is None
        if not is_ambiguous:
            total_attempts += repeats
            correct_attempts += sum(1 for a in attempts if a["label"] == item.expected_label)

        labels = {a["label"] for a in attempts}
        is_consistent = len(labels) == 1 and None not in labels
        if is_consistent:
            consistent_items += 1

        first = attempts[0]
        predicted_label = first["label"]
        confidence = first["confidence"]
        correct: bool | None = None if is_ambiguous else predicted_label == item.expected_label

        case_rows.append(
            BenchmarkCase(
                case_id=item.case_id,
                category=item.category,
                expected_label=item.expected_label,
                is_ambiguous=is_ambiguous,
                attempts_json=json.dumps(attempts),
                predicted_label=predicted_label,
                confidence=confidence,
                correct=correct,
                consistent=is_consistent,
            )
        )

    accuracy = correct_attempts / total_attempts if total_attempts > 0 else 0.0
    consistency = consistent_items / len(BENCHMARK_DATASET) if BENCHMARK_DATASET else 0.0

    run = BenchmarkRun(
        model_used=settings.ollama_model,
        repeats=repeats,
        total_cases=len(BENCHMARK_DATASET),
        accuracy=accuracy,
        consistency=consistency,
        cases=case_rows,
    )

    db = session_factory()
    try:
        db.add(run)
        db.commit()
        db.refresh(run)
        _ = list(run.cases)  # force-load the relationship while the session is open
    finally:
        db.close()

    return run
