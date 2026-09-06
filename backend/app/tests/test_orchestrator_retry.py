from __future__ import annotations

import pytest

from app.models.pipeline_run import PipelineRun, StageTrace
from app.orchestrator.contracts import Stage
from app.orchestrator.graph import (
    NoFailedRunError,
    _reconstruct_state_before_stage,
    build_graph,
    build_retry_graph,
    retry_pipeline,
    run_pipeline,
)
from app.orchestrator.state import (
    ClassificationSlice,
    CrmWriteSlice,
    EnrichmentSlice,
    IntakeSlice,
    LeadPipelineState,
    NotificationSlice,
    ReviewSlice,
    RunStatus,
)
from app.orchestrator.tool_scope import ToolRegistry


class _FakeStage(Stage):
    """Same test double shape as `test_orchestrator_graph.py`'s own `_FakeStage`."""

    def __init__(self, name, state_slice, schema, fn):
        self.name = name
        self.state_slice = state_slice
        self.input_schema = schema
        self.output_schema = schema
        self.allowed_tools = frozenset()
        self._fn = fn

    def run(self, data, tools):
        return self._fn(data, tools)


def _make_stages(calls: list[str], *, confidence: float, fail_at: str | None) -> dict[str, Stage]:
    def record(name: str) -> None:
        calls.append(name)

    def intake_fn(data, tools):
        record("intake")
        return data

    def classify_fn(data, tools):
        record("classify")
        return ClassificationSlice(intent_label="buyer", confidence_score=confidence, model_used="test-model")

    def enrich_fn(data, tools):
        record("enrich")
        return EnrichmentSlice(resolved_fields={"source": "test"})

    def crm_write_fn(data, tools):
        record("crm_write")
        if fail_at == "crm_write":
            raise RuntimeError("hubspot write boom")
        return CrmWriteSlice(hubspot_record_id="hs-1", write_status="created")

    def review_fn(data, tools):
        record("human_review")
        return ReviewSlice(queued=True, paused_at_stage="crm_write")

    def notify_fn(data, tools):
        record("notify")
        return NotificationSlice(notified=True, outcome_type="auto_processed")

    return {
        "intake": _FakeStage("intake_parsing", "intake", IntakeSlice, intake_fn),
        "classification": _FakeStage("intent_classification", "classification", ClassificationSlice, classify_fn),
        "enrichment": _FakeStage("data_enrichment", "enrichment", EnrichmentSlice, enrich_fn),
        "crm_write": _FakeStage("hubspot_crm_write", "crm_write", CrmWriteSlice, crm_write_fn),
        "review": _FakeStage("human_review", "review", ReviewSlice, review_fn),
        "notification": _FakeStage("outcome_notification", "notification", NotificationSlice, notify_fn),
    }


def _initial_state() -> LeadPipelineState:
    return LeadPipelineState(intake=IntakeSlice(source_channel="web_form", message_body="I want to buy now"))


def _create_failed_run(db_session_factory, lead_id: str = "lead-retry") -> LeadPipelineState:
    calls: list[str] = []
    stages = _make_stages(calls, confidence=0.95, fail_at="crm_write")
    graph = build_graph(stages, ToolRegistry(), db_session_factory, confidence_threshold=0.7)
    final = run_pipeline(lead_id, _initial_state(), graph=graph, session_factory=db_session_factory)
    assert final.run.status == RunStatus.FAILED
    return final


def test_build_retry_graph_rejects_unsupported_start_stage():
    with pytest.raises(ValueError):
        build_retry_graph(
            "notification", {}, ToolRegistry(), lambda: None, confidence_threshold=0.7  # type: ignore[arg-type]
        )


def test_reconstruct_state_before_stage_replays_prior_stage_outputs(db_session_factory):
    failed = _create_failed_run(db_session_factory)

    state = _reconstruct_state_before_stage(
        failed.run.lead_id, "new-run-id", failed.run.run_id, "crm_write", db_session_factory
    )

    assert state.intake.message_body == "I want to buy now"
    assert state.classification.intent_label == "buyer"
    assert state.classification.confidence_score == 0.95
    assert state.enrichment.resolved_fields == {"source": "test"}
    assert state.crm_write.write_status is None  # crm_write itself never completed
    assert state.run.run_id == "new-run-id"
    assert state.run.lead_id == failed.run.lead_id
    assert state.run.status == RunStatus.RUNNING


def test_retry_pipeline_creates_a_new_run_and_does_not_rerun_earlier_stages(db_session_factory):
    failed = _create_failed_run(db_session_factory)

    retry_calls: list[str] = []
    retry_stages = _make_stages(retry_calls, confidence=0.95, fail_at=None)

    def graph_factory(start_stage: str, session_factory):
        return build_retry_graph(start_stage, retry_stages, ToolRegistry(), session_factory, confidence_threshold=0.7)

    final = retry_pipeline(failed.run.lead_id, graph_factory=graph_factory, session_factory=db_session_factory)

    # Only the failed stage onward is replayed - intake/classify/enrich never re-run.
    assert retry_calls == ["crm_write", "notify"]
    assert final.run.status == RunStatus.COMPLETED
    assert final.crm_write.write_status == "created"
    assert final.run.run_id != failed.run.run_id

    db = db_session_factory()
    try:
        # The original failed row is untouched.
        original = db.get(PipelineRun, failed.run.run_id)
        assert original.status == RunStatus.FAILED.value

        new_row = db.get(PipelineRun, final.run.run_id)
        assert new_row.status == RunStatus.COMPLETED.value
        assert new_row.lead_id == failed.run.lead_id

        # New run's own trace rows contain only the replayed stage(s) onward - the
        # reused prior-stage outputs are read, never re-persisted as duplicate rows.
        new_traces = db.query(StageTrace).filter(StageTrace.run_id == final.run.run_id).all()
        assert {t.stage_name for t in new_traces} == {"hubspot_crm_write", "outcome_notification"}

        assert db.query(PipelineRun).filter(PipelineRun.lead_id == failed.run.lead_id).count() == 2
    finally:
        db.close()


def test_retry_pipeline_raises_when_no_failed_run_exists(db_session_factory):
    calls: list[str] = []
    stages = _make_stages(calls, confidence=0.95, fail_at=None)
    graph = build_graph(stages, ToolRegistry(), db_session_factory, confidence_threshold=0.7)
    run_pipeline("lead-healthy", _initial_state(), graph=graph, session_factory=db_session_factory)

    with pytest.raises(NoFailedRunError):
        retry_pipeline("lead-healthy", session_factory=db_session_factory)


def test_retry_pipeline_retries_most_recent_failed_run_when_multiple_exist(db_session_factory):
    lead_id = "lead-double-fail"
    calls_1: list[str] = []
    stages_1 = _make_stages(calls_1, confidence=0.95, fail_at="crm_write")
    graph_1 = build_graph(stages_1, ToolRegistry(), db_session_factory, confidence_threshold=0.7)
    first_failure = run_pipeline(lead_id, _initial_state(), graph=graph_1, session_factory=db_session_factory)
    assert first_failure.run.status == RunStatus.FAILED

    retry_calls_1: list[str] = []
    retry_stages_1 = _make_stages(retry_calls_1, confidence=0.95, fail_at="crm_write")

    def failing_graph_factory(start_stage: str, session_factory):
        return build_retry_graph(
            start_stage, retry_stages_1, ToolRegistry(), session_factory, confidence_threshold=0.7
        )

    second_failure = retry_pipeline(lead_id, graph_factory=failing_graph_factory, session_factory=db_session_factory)
    assert second_failure.run.status == RunStatus.FAILED
    assert second_failure.run.run_id != first_failure.run.run_id

    retry_calls_2: list[str] = []
    retry_stages_2 = _make_stages(retry_calls_2, confidence=0.95, fail_at=None)

    def succeeding_graph_factory(start_stage: str, session_factory):
        return build_retry_graph(
            start_stage, retry_stages_2, ToolRegistry(), session_factory, confidence_threshold=0.7
        )

    final = retry_pipeline(lead_id, graph_factory=succeeding_graph_factory, session_factory=db_session_factory)

    assert final.run.status == RunStatus.COMPLETED
    # A third, brand-new run - retrying never mutates either prior attempt's row.
    assert final.run.run_id not in (first_failure.run.run_id, second_failure.run.run_id)
    db = db_session_factory()
    try:
        assert db.query(PipelineRun).filter(PipelineRun.lead_id == lead_id).count() == 3
    finally:
        db.close()
