from __future__ import annotations

from app.models.pipeline_run import PipelineRun, StageTrace
from app.orchestrator.contracts import Stage
from app.orchestrator.graph import build_graph, default_stages, run_pipeline
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
    """A test double conforming to the Stage contract, used to exercise `graph.py`'s
    routing/transition logic independent of the real (still-stub) Features 02-07."""

    def __init__(self, name, state_slice, schema, fn):
        self.name = name
        self.state_slice = state_slice
        self.input_schema = schema
        self.output_schema = schema
        self.allowed_tools = frozenset()
        self._fn = fn

    def run(self, data, tools):
        return self._fn(data, tools)


def _make_stages(calls: list[str], *, confidence: float, fail_at: str | None = None) -> dict[str, Stage]:
    def record(name: str) -> None:
        calls.append(name)

    def intake_fn(data, tools):
        record("intake")
        return data

    def classify_fn(data, tools):
        record("classify")
        if fail_at == "classify":
            raise RuntimeError("classification boom")
        return ClassificationSlice(intent_label="buyer", confidence_score=confidence, model_used="test-model")

    def enrich_fn(data, tools):
        record("enrich")
        if fail_at == "enrich":
            raise RuntimeError("enrichment boom")
        return EnrichmentSlice()

    def crm_write_fn(data, tools):
        record("crm_write")
        if fail_at == "crm_write":
            raise RuntimeError("crm write boom")
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


def test_high_confidence_lead_skips_human_review(db_session_factory):
    calls: list[str] = []
    stages = _make_stages(calls, confidence=0.95)
    graph = build_graph(stages, ToolRegistry(), db_session_factory, confidence_threshold=0.7)

    final = run_pipeline("lead-high", _initial_state(), graph=graph, session_factory=db_session_factory)

    assert calls == ["intake", "classify", "enrich", "crm_write", "notify"]
    assert final.crm_write.write_status == "created"
    assert final.notification.notified is True
    assert final.review.queued is False


def test_low_confidence_lead_routes_to_human_review_instead_of_crm_write(db_session_factory):
    calls: list[str] = []
    stages = _make_stages(calls, confidence=0.2)
    graph = build_graph(stages, ToolRegistry(), db_session_factory, confidence_threshold=0.7)

    final = run_pipeline("lead-low", _initial_state(), graph=graph, session_factory=db_session_factory)

    assert calls == ["intake", "classify", "enrich", "human_review"]
    assert "crm_write" not in calls
    assert "notify" not in calls
    assert final.crm_write.write_status is None
    assert final.review.queued is True


def test_stage_exception_halts_only_that_leads_run(db_session_factory):
    calls_a: list[str] = []
    stages_a = _make_stages(calls_a, confidence=0.95, fail_at="crm_write")
    graph_a = build_graph(stages_a, ToolRegistry(), db_session_factory, confidence_threshold=0.7)

    final_a = run_pipeline("lead-fail", _initial_state(), graph=graph_a, session_factory=db_session_factory)

    assert final_a.run.status == RunStatus.FAILED
    assert final_a.run.failed_stage == "hubspot_crm_write"
    assert "boom" in (final_a.run.error or "")
    assert "notify" not in calls_a

    # A second, independently-run lead must be unaffected by the first's failure - no
    # shared mutable state across leads (separate state, separate graph invocation).
    calls_b: list[str] = []
    stages_b = _make_stages(calls_b, confidence=0.95)
    graph_b = build_graph(stages_b, ToolRegistry(), db_session_factory, confidence_threshold=0.7)

    final_b = run_pipeline("lead-ok", _initial_state(), graph=graph_b, session_factory=db_session_factory)

    assert final_b.run.status == RunStatus.RUNNING
    assert final_b.crm_write.write_status == "created"


def test_every_stage_transition_produces_a_queryable_stage_trace(db_session_factory):
    calls: list[str] = []
    stages = _make_stages(calls, confidence=0.95)
    graph = build_graph(stages, ToolRegistry(), db_session_factory, confidence_threshold=0.7)

    final = run_pipeline("lead-trace", _initial_state(), graph=graph, session_factory=db_session_factory)

    db = db_session_factory()
    try:
        traces = (
            db.query(StageTrace)
            .join(PipelineRun)
            .filter(PipelineRun.id == final.run.run_id)
            .order_by(StageTrace.created_at)
            .all()
        )
        assert [t.stage_name for t in traces] == [
            "intake_parsing",
            "intent_classification",
            "data_enrichment",
            "hubspot_crm_write",
            "outcome_notification",
        ]
        assert all(t.status == "COMPLETED" for t in traces)
    finally:
        db.close()


def test_default_stages_web_form_payload_reaches_enrichment_with_normalized_intake(db_session_factory):
    """Features 02+03+04: `default_stages()`'s real `IntakeStage` normalizes the raw
    payload, the real `IntentClassificationStage` successfully classifies it, and the
    real `DataEnrichmentStage` runs as a no-op pass-through (all fields already present,
    so no "hubspot_search_contact" call is made). The run then reaches (attempts)
    crm_write_stage - still a stub until Feature 05 lands, so the run halts there as
    FAILED, which is the expected/correct outcome at this point. This proves the real
    Enrichment stage's *success* path chained after real Classification, not just its
    unit tests in isolation - mirroring how Feature 03's graph-level test proved the
    same for classification."""
    stages = default_stages()
    registry = ToolRegistry()
    registry.register("ollama_classify", lambda text: {"intent_label": "buyer", "confidence_score": 0.95})
    registry.register("hubspot_search_contact", lambda **kwargs: (_ for _ in ()).throw(
        AssertionError("tool should not be called - all fields already present")
    ))
    graph = build_graph(stages, registry, db_session_factory, confidence_threshold=0.7)

    initial_state = LeadPipelineState(
        intake=IntakeSlice(
            source_channel="web_form",
            name=" Jane Doe ",
            phone="(555) 123-4567",
            email=" JANE@EXAMPLE.COM ",
            message_body="I want to buy now",
        )
    )
    final = run_pipeline("lead-webform", initial_state, graph=graph, session_factory=db_session_factory)

    assert final.intake.name == "Jane Doe"
    assert final.intake.phone == "5551234567"
    assert final.intake.email == "jane@example.com"
    assert final.intake.empty_message is False
    assert final.classification.intent_label == "buyer"
    assert final.classification.confidence_score == 0.95
    assert final.enrichment.resolved_fields == {}
    assert final.run.status == RunStatus.FAILED
    assert final.run.failed_stage == "hubspot_crm_write"


def test_low_confidence_classification_from_real_stage_reaches_human_review(db_session_factory):
    """Proves a low `confidence_score` produced by the real (non-stub)
    `IntentClassificationStage` reaches Human Review via the existing, unmodified
    `_route_after_enrich` - no new conditional edges added to graph.py. Enrichment is
    faked (still a stub until Feature 04) so this isolates "does low confidence route
    correctly" from "is enrichment implemented yet"."""
    stages = default_stages()
    stages["enrichment"] = _FakeStage(
        "data_enrichment", "enrichment", EnrichmentSlice, lambda data, tools: EnrichmentSlice()
    )
    stages["review"] = _FakeStage(
        "human_review", "review", ReviewSlice, lambda data, tools: ReviewSlice(queued=True, paused_at_stage="crm_write")
    )
    registry = ToolRegistry()
    registry.register("ollama_classify", lambda text: {"intent_label": "browser", "confidence_score": 0.2})
    graph = build_graph(stages, registry, db_session_factory, confidence_threshold=0.7)

    initial_state = LeadPipelineState(
        intake=IntakeSlice(source_channel="web_form", message_body="just browsing around")
    )
    final = run_pipeline("lead-low-conf-real", initial_state, graph=graph, session_factory=db_session_factory)

    assert final.classification.intent_label == "browser"
    assert final.classification.confidence_score == 0.2
    assert final.review.queued is True
    assert final.crm_write.write_status is None


def test_classification_failed_sentinel_from_real_stage_reaches_human_review(db_session_factory):
    """A tool that raises on both attempts produces the `classification_failed` sentinel
    (confidence_score=0.0), which must route to Human Review the same as any other
    below-threshold result - no separate "failed" branch needed in graph.py."""
    stages = default_stages()
    stages["enrichment"] = _FakeStage(
        "data_enrichment", "enrichment", EnrichmentSlice, lambda data, tools: EnrichmentSlice()
    )
    stages["review"] = _FakeStage(
        "human_review", "review", ReviewSlice, lambda data, tools: ReviewSlice(queued=True, paused_at_stage="crm_write")
    )
    registry = ToolRegistry()

    def _always_raise(text):
        raise RuntimeError("ollama unreachable")

    registry.register("ollama_classify", _always_raise)
    graph = build_graph(stages, registry, db_session_factory, confidence_threshold=0.7)

    initial_state = LeadPipelineState(intake=IntakeSlice(source_channel="web_form", message_body="hello there"))
    final = run_pipeline("lead-classify-failed", initial_state, graph=graph, session_factory=db_session_factory)

    assert final.classification.model_used == "classification_failed"
    assert final.review.queued is True


def test_failed_stage_transition_is_traced_with_error(db_session_factory):
    calls: list[str] = []
    stages = _make_stages(calls, confidence=0.95, fail_at="enrich")
    graph = build_graph(stages, ToolRegistry(), db_session_factory, confidence_threshold=0.7)

    final = run_pipeline("lead-trace-fail", _initial_state(), graph=graph, session_factory=db_session_factory)

    db = db_session_factory()
    try:
        traces = (
            db.query(StageTrace)
            .join(PipelineRun)
            .filter(PipelineRun.id == final.run.run_id)
            .order_by(StageTrace.created_at)
            .all()
        )
        assert [t.stage_name for t in traces] == ["intake_parsing", "intent_classification", "data_enrichment"]
        assert traces[-1].status == "FAILED"
        assert "boom" in (traces[-1].error or "")
    finally:
        db.close()
