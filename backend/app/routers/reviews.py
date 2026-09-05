from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy import update

from app.database.session import SessionLocal
from app.models.pipeline_run import PipelineRun
from app.models.review_queue import ReviewQueueItem
from app.orchestrator.graph import build_production_resume_graph, persist_outcome_notification, resume_pipeline
from app.orchestrator.stages.outcome_notification import OutcomeNotificationStage
from app.orchestrator.state import LeadPipelineState, RunStatus
from app.orchestrator.tool_scope import ToolRegistry
from app.schemas.pipeline import PipelineRunOut
from app.schemas.review import ReviewActionRequest, ReviewQueueItemOut

router = APIRouter(prefix="/reviews", tags=["reviews"])

SessionFactory = Callable[[], object]
GraphFactory = Callable[[SessionFactory], CompiledStateGraph]


def get_session_factory() -> SessionFactory:
    """FastAPI dependency, overridden in tests - same pattern as
    `app.routers.leads.get_session_factory`."""
    return SessionLocal


def get_resume_graph_factory() -> GraphFactory:
    """FastAPI dependency, overridden in tests to inject a resume graph built with
    fake tool bindings - keeps the approve/edit path testable without live
    HubSpot/Ollama credentials, the same reason `get_session_factory` exists. Does not
    introduce a second resume mechanism - `resume_pipeline` stays the only path; this
    only makes which compiled graph it invokes pluggable, same technique already used
    for the DB session factory."""
    return build_production_resume_graph


@router.get("", response_model=list[ReviewQueueItemOut])
def list_pending_reviews(session_factory: SessionFactory = Depends(get_session_factory)) -> list[ReviewQueueItemOut]:
    db = session_factory()
    try:
        items = db.query(ReviewQueueItem).filter(ReviewQueueItem.status == "PENDING").all()
        return [ReviewQueueItemOut.model_validate(item) for item in items]
    finally:
        db.close()


@router.get("/{run_id}", response_model=ReviewQueueItemOut)
def get_review(run_id: str, session_factory: SessionFactory = Depends(get_session_factory)) -> ReviewQueueItemOut:
    db = session_factory()
    try:
        item = db.query(ReviewQueueItem).filter(ReviewQueueItem.run_id == run_id).first()
        if item is None:
            raise HTTPException(status_code=404, detail="Review queue item not found")
        return ReviewQueueItemOut.model_validate(item)
    finally:
        db.close()


@router.post("/{run_id}/action", response_model=PipelineRunOut)
def action_review(
    run_id: str,
    payload: ReviewActionRequest,
    session_factory: SessionFactory = Depends(get_session_factory),
    resume_graph_factory: GraphFactory = Depends(get_resume_graph_factory),
) -> PipelineRunOut:
    if payload.action == "edit" and not payload.corrected_intent_label:
        raise HTTPException(status_code=422, detail="corrected_intent_label is required when action is 'edit'")

    state_snapshot: str | None = None

    db = session_factory()
    try:
        item = db.query(ReviewQueueItem).filter(ReviewQueueItem.run_id == run_id).first()
        if item is None:
            raise HTTPException(status_code=404, detail="Review queue item not found")

        # Concurrency-safe claim: the atomic UPDATE's matched-row-count is the only
        # authority for whether this is the first action applied - never a
        # separate SELECT-then-branch on `status`. A second concurrent/sequential
        # call on an already-actioned item matches zero rows and is rejected.
        result = db.execute(
            update(ReviewQueueItem)
            .where(ReviewQueueItem.run_id == run_id, ReviewQueueItem.status == "PENDING")
            .values(
                status="ACTIONED",
                reviewer_action=payload.action,
                corrected_intent_label=payload.corrected_intent_label,
                reviewer_name=payload.reviewer_name,
                actioned_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=409, detail="Review item already actioned")

        state_snapshot = item.state_snapshot

        if payload.action == "reject":
            run_row = db.get(PipelineRun, run_id)
            if run_row is not None:
                run_row.status = RunStatus.REJECTED.value
                db.commit()
                db.refresh(run_row)
            try:
                rejected_state = LeadPipelineState.model_validate_json(state_snapshot)
                rejected_state.run = rejected_state.run.model_copy(update={"status": RunStatus.REJECTED})
                persist_outcome_notification(
                    rejected_state, OutcomeNotificationStage(), ToolRegistry(), session_factory
                )
            except Exception:
                # Notification creation is a side effect of a reviewer decision, never
                # a gating condition - it must not affect the REJECTED status already
                # committed above.
                pass
            return PipelineRunOut.model_validate(run_row)
    finally:
        db.close()

    # approve / edit: reconstruct the paused state and re-enter the orchestrator via
    # resume_pipeline - never a bespoke API code path calling stage tools directly.
    state = LeadPipelineState.model_validate_json(state_snapshot)
    state.review = state.review.model_copy(
        update={"reviewer_action": payload.action, "corrected_intent_label": payload.corrected_intent_label}
    )
    if payload.action == "edit":
        state.classification = state.classification.model_copy(
            update={"intent_label": payload.corrected_intent_label}
        )

    final_state = resume_pipeline(
        run_id, state, graph=resume_graph_factory(session_factory), session_factory=session_factory
    )

    db = session_factory()
    try:
        run_row = db.get(PipelineRun, final_state.run.run_id)
        return PipelineRunOut.model_validate(run_row)
    finally:
        db.close()
