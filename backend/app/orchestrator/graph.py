from __future__ import annotations

from typing import Callable

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from app.database.session import SessionLocal
from app.models.pipeline_run import PipelineRun, StageTrace
from app.orchestrator.contracts import Stage
from app.orchestrator.stages.data_enrichment import DataEnrichmentStage
from app.orchestrator.stages.hubspot_crm_write import HubSpotCrmWriteStage
from app.orchestrator.stages.intake import IntakeStage
from app.orchestrator.stages.intent_classification import IntentClassificationStage
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

SessionFactory = Callable[[], object]

# The six pipeline stages in graph-node order. Keys match `LeadPipelineState`'s slice
# field names; values are the (node name, owning feature) this stage belongs to.
_STAGE_ORDER: list[tuple[str, str, str]] = [
    ("intake", "intake_parsing", "Feature 02"),
    ("classification", "intent_classification", "Feature 03"),
    ("enrichment", "data_enrichment", "Feature 04"),
    ("crm_write", "hubspot_crm_write", "Feature 05"),
    ("review", "human_review", "Feature 06"),
    ("notification", "outcome_notification", "Feature 07"),
]


class _StubStage(Stage):
    """Placeholder body for a stage whose real feature hasn't landed yet.

    Defines this graph's shape and transition logic only, per
    `architecture-plan-feature-01.md`'s Implementation Order — not a durable design.
    Each downstream feature (02-07) replaces its stub with a real `Stage` implementation
    when its own Step 6 group lands; `build_graph` accepts an explicit `stages` mapping
    so that swap never requires touching this file's wiring.
    """

    def __init__(self, name: str, state_slice: str, feature_id: str, schema: type[BaseModel]) -> None:
        self.name = name
        self.state_slice = state_slice
        self.input_schema = schema
        self.output_schema = schema
        self.allowed_tools = frozenset()
        self._feature_id = feature_id

    def run(self, data: BaseModel, tools: object) -> BaseModel:
        raise NotImplementedError(f"Stage '{self.name}' is not yet implemented — see {self._feature_id}")


def default_stages() -> dict[str, Stage]:
    """Production stage set: Features 02-04's stages are real; the remaining three stay
    stubs until Features 05-07 land."""
    schemas: dict[str, type[BaseModel]] = {
        "intake": IntakeSlice,
        "classification": ClassificationSlice,
        "enrichment": EnrichmentSlice,
        "crm_write": CrmWriteSlice,
        "review": ReviewSlice,
        "notification": NotificationSlice,
    }
    stages: dict[str, Stage] = {
        slice_name: _StubStage(node_name, slice_name, feature_id, schemas[slice_name])
        for slice_name, node_name, feature_id in _STAGE_ORDER
    }
    stages["intake"] = IntakeStage()
    stages["classification"] = IntentClassificationStage()
    stages["enrichment"] = DataEnrichmentStage()
    stages["crm_write"] = HubSpotCrmWriteStage()
    return stages


def _write_trace(
    session_factory: SessionFactory,
    run_id: str | None,
    stage_name: str,
    input_slice: BaseModel | None,
    output_slice: BaseModel | None,
    status: str,
    error: str | None,
) -> None:
    if run_id is None:
        return
    db = session_factory()
    try:
        db.add(
            StageTrace(
                run_id=run_id,
                stage_name=stage_name,
                input_snapshot=input_slice.model_dump_json() if input_slice is not None else None,
                output_snapshot=output_slice.model_dump_json() if output_slice is not None else None,
                status=status,
                error=error,
            )
        )
        db.commit()
    finally:
        db.close()


def _make_node(stage: Stage, registry: ToolRegistry, session_factory: SessionFactory) -> Callable[[LeadPipelineState], dict]:
    def node(state: LeadPipelineState) -> dict:
        if state.run.status == RunStatus.FAILED:
            # Should be unreachable given the conditional edges below (a FAILED run
            # always routes to END), but never silently proceed past a halted run.
            return {}

        if stage.input_slices is not None:
            slice_in = stage.input_schema(**{name: getattr(state, name) for name in stage.input_slices})
        else:
            slice_in = getattr(state, stage.effective_input_slice)
        proxy = registry.scoped_proxy(stage.allowed_tools, stage.name)

        try:
            output = stage.run(slice_in, proxy)
        except Exception as exc:  # a stage failure halts only this lead's run
            error_msg = str(exc)
            _write_trace(session_factory, state.run.run_id, stage.name, slice_in, None, "FAILED", error_msg)
            return {
                "run": state.run.model_copy(
                    update={"status": RunStatus.FAILED, "failed_stage": stage.name, "error": error_msg}
                )
            }

        _write_trace(session_factory, state.run.run_id, stage.name, slice_in, output, "COMPLETED", None)
        return {stage.state_slice: output}

    return node


def _route_or_fail(next_node: str) -> Callable[[LeadPipelineState], str]:
    def route(state: LeadPipelineState) -> str:
        return "failed" if state.run.status == RunStatus.FAILED else next_node

    return route


def _route_after_enrich(confidence_threshold: float) -> Callable[[LeadPipelineState], str]:
    def route(state: LeadPipelineState) -> str:
        if state.run.status == RunStatus.FAILED:
            return "failed"
        confidence = state.classification.confidence_score
        if confidence is None or confidence < confidence_threshold:
            return "human_review"
        return "crm_write"

    return route


def build_graph(
    stages: dict[str, Stage],
    registry: ToolRegistry,
    session_factory: SessionFactory,
    confidence_threshold: float,
) -> CompiledStateGraph:
    """Wire the 6-stage state machine: deterministic edges Intake -> Classify -> Enrich,
    a conditional branch after Enrich into Human Review (low confidence) or CRM Write ->
    Notify (high confidence), and an error edge from every node straight to END on any
    stage exception (that lead's run only — no shared mutable state across leads)."""
    # Node names are deliberately distinct from LeadPipelineState's field names
    # ("intake", "crm_write", ...) - langgraph forbids a node sharing a state-key name.
    graph = StateGraph(LeadPipelineState)

    graph.add_node("intake_stage", _make_node(stages["intake"], registry, session_factory))
    graph.add_node("classify_stage", _make_node(stages["classification"], registry, session_factory))
    graph.add_node("enrich_stage", _make_node(stages["enrichment"], registry, session_factory))
    graph.add_node("crm_write_stage", _make_node(stages["crm_write"], registry, session_factory))
    graph.add_node("human_review_stage", _make_node(stages["review"], registry, session_factory))
    graph.add_node("notify_stage", _make_node(stages["notification"], registry, session_factory))

    graph.add_edge(START, "intake_stage")
    graph.add_conditional_edges(
        "intake_stage", _route_or_fail("classify"), {"classify": "classify_stage", "failed": END}
    )
    graph.add_conditional_edges(
        "classify_stage", _route_or_fail("enrich"), {"enrich": "enrich_stage", "failed": END}
    )
    graph.add_conditional_edges(
        "enrich_stage",
        _route_after_enrich(confidence_threshold),
        {"crm_write": "crm_write_stage", "human_review": "human_review_stage", "failed": END},
    )
    graph.add_conditional_edges(
        "crm_write_stage", _route_or_fail("notify"), {"notify": "notify_stage", "failed": END}
    )
    graph.add_edge("human_review_stage", END)
    graph.add_edge("notify_stage", END)

    return graph.compile()


def build_production_graph(session_factory: SessionFactory = SessionLocal) -> CompiledStateGraph:
    from app.core.config import settings
    from app.orchestrator.tools import register_default_tools

    registry = ToolRegistry()
    register_default_tools(registry, settings)
    return build_graph(default_stages(), registry, session_factory, settings.confidence_threshold)


def run_pipeline(
    lead_id: str,
    initial_state: LeadPipelineState,
    *,
    graph: CompiledStateGraph | None = None,
    session_factory: SessionFactory = SessionLocal,
) -> LeadPipelineState:
    """Create the `PipelineRun` row, invoke the graph, and persist the final status.
    The entry point downstream features call to start a lead through the pipeline."""
    compiled = graph if graph is not None else build_production_graph(session_factory)

    db = session_factory()
    try:
        run_row = PipelineRun(lead_id=lead_id, status=RunStatus.RUNNING.value)
        db.add(run_row)
        db.commit()
        db.refresh(run_row)
        run_id = run_row.id
    finally:
        db.close()

    initial_state.run = initial_state.run.model_copy(update={"run_id": run_id, "lead_id": lead_id})

    result = compiled.invoke(initial_state)
    final_state = result if isinstance(result, LeadPipelineState) else LeadPipelineState.model_validate(result)

    db = session_factory()
    try:
        run_row = db.get(PipelineRun, run_id)
        if run_row is not None:
            run_row.status = final_state.run.status.value
            db.commit()
    finally:
        db.close()

    return final_state
