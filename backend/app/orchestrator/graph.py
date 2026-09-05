from __future__ import annotations

from typing import Callable

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from app.database.session import SessionLocal
from app.models.notification import Notification
from app.models.pipeline_run import PipelineRun, StageTrace
from app.models.review_queue import ReviewQueueItem
from app.orchestrator.contracts import Stage
from app.orchestrator.stages.data_enrichment import DataEnrichmentStage
from app.orchestrator.stages.human_review import HumanReviewStage
from app.orchestrator.stages.hubspot_crm_write import HubSpotCrmWriteStage
from app.orchestrator.stages.intake import IntakeStage
from app.orchestrator.stages.intent_classification import IntentClassificationStage
from app.orchestrator.stages.outcome_notification import OutcomeNotificationStage
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
    stages["review"] = HumanReviewStage()
    stages["notification"] = OutcomeNotificationStage()
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


def persist_outcome_notification(
    state: LeadPipelineState, stage: Stage, registry: ToolRegistry, session_factory: SessionFactory
) -> NotificationSlice:
    """Feature 07: the shared "resolve merged input, call stage.run(), write
    StageTrace, save Notification row" logic for the three terminal transitions the
    graph's own `notify_stage` node never sees (stage failure, human-review queueing,
    reviewer rejection) — see architecture-plan-feature-07.md. The fourth outcome
    (crm_write success) keeps using the existing generic `_make_node` graph-node path
    unchanged; this helper must never be combined with that path for the same
    transition, or a run would get two notifications instead of one."""
    if stage.input_slices is not None:
        slice_in = stage.input_schema(**{name: getattr(state, name) for name in stage.input_slices})
    else:
        slice_in = getattr(state, stage.effective_input_slice)
    proxy = registry.scoped_proxy(stage.allowed_tools, stage.name)

    output = stage.run(slice_in, proxy)
    _write_trace(session_factory, state.run.run_id, stage.name, slice_in, output, "COMPLETED", None)

    db = session_factory()
    try:
        db.add(
            Notification(
                run_id=state.run.run_id,
                lead_id=state.run.lead_id,
                outcome_type=output.outcome_type,
                message=output.message,
                detail_link=output.detail_link,
            )
        )
        db.commit()
    finally:
        db.close()

    return output


def _make_node(
    stage: Stage,
    registry: ToolRegistry,
    session_factory: SessionFactory,
    notification_stage: Stage | None = None,
) -> Callable[[LeadPipelineState], dict]:
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
            failed_run = state.run.model_copy(
                update={"status": RunStatus.FAILED, "failed_stage": stage.name, "error": error_msg}
            )
            result: dict = {"run": failed_run}
            if notification_stage is not None:
                try:
                    failed_state = state.model_copy(update={"run": failed_run})
                    result["notification"] = persist_outcome_notification(
                        failed_state, notification_stage, registry, session_factory
                    )
                except Exception:
                    # Notification creation is a side effect of a halted run, never a
                    # gating condition - it must not mask or replace the original
                    # stage failure already captured above.
                    pass
            return result

        _write_trace(session_factory, state.run.run_id, stage.name, slice_in, output, "COMPLETED", None)
        return {stage.state_slice: output}

    return node


def _make_human_review_node(
    stage: Stage, registry: ToolRegistry, session_factory: SessionFactory, notification_stage: Stage
) -> Callable[[LeadPipelineState], dict]:
    """Same shape as `_make_node`, but on success also persists a `ReviewQueueItem`
    (with a full-state resume snapshot), moves the run to `AWAITING_REVIEW` — the
    dead `AWAITING_REVIEW` status this feature is what actually activates — and fires
    the awaiting-review outcome notification (Feature 07), since
    `human_review_stage -> END` never visits the graph's own `notify_stage` node. Used
    only for the `"human_review_stage"` node; every other node keeps using `_make_node`."""

    def node(state: LeadPipelineState) -> dict:
        if state.run.status == RunStatus.FAILED:
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

        paused_run = state.run.model_copy(update={"status": RunStatus.AWAITING_REVIEW})
        state_snapshot = state.model_copy(update={stage.state_slice: output, "run": paused_run}).model_dump_json()

        db = session_factory()
        try:
            db.add(
                ReviewQueueItem(
                    run_id=state.run.run_id,
                    lead_id=state.run.lead_id,
                    draft_intent_label=state.classification.intent_label,
                    confidence_score=state.classification.confidence_score,
                    state_snapshot=state_snapshot,
                )
            )
            db.commit()
        finally:
            db.close()

        result: dict = {stage.state_slice: output, "run": paused_run}
        try:
            paused_state = state.model_copy(update={stage.state_slice: output, "run": paused_run})
            result["notification"] = persist_outcome_notification(
                paused_state, notification_stage, registry, session_factory
            )
        except Exception:
            # Notification creation is a side effect of a paused run, never a gating
            # condition - it must not prevent the run from actually pausing above.
            pass
        return result

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

    notification_stage = stages["notification"]
    graph.add_node("intake_stage", _make_node(stages["intake"], registry, session_factory, notification_stage))
    graph.add_node(
        "classify_stage", _make_node(stages["classification"], registry, session_factory, notification_stage)
    )
    graph.add_node(
        "enrich_stage", _make_node(stages["enrichment"], registry, session_factory, notification_stage)
    )
    graph.add_node(
        "crm_write_stage", _make_node(stages["crm_write"], registry, session_factory, notification_stage)
    )
    graph.add_node(
        "human_review_stage",
        _make_human_review_node(stages["review"], registry, session_factory, notification_stage),
    )
    graph.add_node("notify_stage", _make_node(notification_stage, registry, session_factory))

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


def build_resume_graph(
    stages: dict[str, Stage],
    registry: ToolRegistry,
    session_factory: SessionFactory,
) -> CompiledStateGraph:
    """The actual resume mechanism the Feature 06 spec assumes exists: a second,
    smaller compiled graph (`crm_write_stage -> notify_stage`) continuing a paused run
    from where Human Review left off. Reuses the exact same `Stage` instances and the
    generic `_make_node` as the primary graph — no bespoke stage-calling code path —
    so every per-stage tool/state boundary guarantee carries over unchanged."""
    graph = StateGraph(LeadPipelineState)

    notification_stage = stages["notification"]
    graph.add_node(
        "crm_write_stage", _make_node(stages["crm_write"], registry, session_factory, notification_stage)
    )
    graph.add_node("notify_stage", _make_node(notification_stage, registry, session_factory))

    graph.add_edge(START, "crm_write_stage")
    graph.add_conditional_edges(
        "crm_write_stage", _route_or_fail("notify"), {"notify": "notify_stage", "failed": END}
    )
    graph.add_edge("notify_stage", END)

    return graph.compile()


def build_production_resume_graph(session_factory: SessionFactory = SessionLocal) -> CompiledStateGraph:
    from app.core.config import settings
    from app.orchestrator.tools import register_default_tools

    registry = ToolRegistry()
    register_default_tools(registry, settings)
    return build_resume_graph(default_stages(), registry, session_factory)


def _mark_completed_if_still_running(state: LeadPipelineState) -> LeadPipelineState:
    """A run's terminal status is set exactly once, at the point that outcome becomes
    known - `RunStatus.FAILED`/`AWAITING_REVIEW` are already set by the time a compiled
    graph returns (inside `_make_node`'s except block / `_make_human_review_node`).
    If `run.status` is still `RUNNING` here, no other terminal path fired, so this is
    the crm_write-success case reaching the end of the graph normally - the only place
    `RunStatus.COMPLETED` is ever assigned. See `.claude/portfolio-reference.md`'s Key
    Decisions (architecture-plan-feature-07.md)."""
    if state.run.status == RunStatus.RUNNING:
        return state.model_copy(update={"run": state.run.model_copy(update={"status": RunStatus.COMPLETED})})
    return state


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
    final_state = _mark_completed_if_still_running(final_state)

    db = session_factory()
    try:
        run_row = db.get(PipelineRun, run_id)
        if run_row is not None:
            run_row.status = final_state.run.status.value
            db.commit()
    finally:
        db.close()

    return final_state


def resume_pipeline(
    run_id: str,
    state: LeadPipelineState,
    *,
    graph: CompiledStateGraph | None = None,
    session_factory: SessionFactory = SessionLocal,
) -> LeadPipelineState:
    """Continue an existing paused `PipelineRun` from its `state_snapshot`. Unlike
    `run_pipeline`, never creates a new `PipelineRun` row - it only updates the
    existing one, so a resumed run's `StageTrace` rows append under the same
    `run_id` the original run used (see architecture-plan-feature-06.md, step 5's
    validation: must never duplicate run history).

    Resets `run.status` to `RUNNING` before invoking the resume graph - the incoming
    state's status is `AWAITING_REVIEW` (carried in the snapshot), and a resumed leg
    must reach the same terminal status (`RUNNING`/`FAILED`) a normal run would,
    exactly as `run_pipeline` starts every fresh run from `RUNNING`."""
    compiled = graph if graph is not None else build_production_resume_graph(session_factory)

    resumed_state = state.model_copy(update={"run": state.run.model_copy(update={"status": RunStatus.RUNNING})})

    result = compiled.invoke(resumed_state)
    final_state = result if isinstance(result, LeadPipelineState) else LeadPipelineState.model_validate(result)
    final_state = _mark_completed_if_still_running(final_state)

    db = session_factory()
    try:
        run_row = db.get(PipelineRun, run_id)
        if run_row is not None:
            run_row.status = final_state.run.status.value
            db.commit()
    finally:
        db.close()

    return final_state
