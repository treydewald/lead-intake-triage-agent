from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException
from langgraph.graph.state import CompiledStateGraph

from app.database.session import SessionLocal
from app.models.review_queue import ReviewQueueItem
from app.orchestrator.graph import build_production_resume_graph
from app.orchestrator.review_actions import apply_review_action
from app.orchestrator.state import LeadPipelineState
from app.schemas.pipeline import PipelineRunOut
from app.schemas.review import ReviewActionRequest, ReviewQueueItemOut

router = APIRouter(prefix="/reviews", tags=["reviews"])

SessionFactory = Callable[[], object]
GraphFactory = Callable[[SessionFactory], CompiledStateGraph]


def get_session_factory() -> SessionFactory:
    """FastAPI dependency, overridden in tests - same pattern as
    `app.routers.leads.get_session_factory`."""
    return SessionLocal


def _to_review_out(item: ReviewQueueItem) -> ReviewQueueItemOut:
    """Reviewer-facing shape plus the lead's original message body, pulled from the
    paused run's `state_snapshot` rather than a new column - the value already exists
    there (`LeadPipelineState.intake.message_body`) since Feature 02, and this is a
    read-only projection, not a new source of truth for it."""
    out = ReviewQueueItemOut.model_validate(item)
    try:
        state = LeadPipelineState.model_validate_json(item.state_snapshot)
        out = out.model_copy(update={"message_body": state.intake.message_body})
    except Exception:
        pass
    return out


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
        return [_to_review_out(item) for item in items]
    finally:
        db.close()


@router.get("/{run_id}", response_model=ReviewQueueItemOut)
def get_review(run_id: str, session_factory: SessionFactory = Depends(get_session_factory)) -> ReviewQueueItemOut:
    db = session_factory()
    try:
        item = db.query(ReviewQueueItem).filter(ReviewQueueItem.run_id == run_id).first()
        if item is None:
            raise HTTPException(status_code=404, detail="Review queue item not found")
        return _to_review_out(item)
    finally:
        db.close()


@router.post("/{run_id}/action", response_model=PipelineRunOut)
def action_review(
    run_id: str,
    payload: ReviewActionRequest,
    session_factory: SessionFactory = Depends(get_session_factory),
    resume_graph_factory: GraphFactory = Depends(get_resume_graph_factory),
) -> PipelineRunOut:
    """Feature 19: thin wrapper over `apply_review_action()` — the actual logic now
    lives in `orchestrator/review_actions.py` so the new Slack callback endpoint
    (`routers/slack.py`) can call the exact same implementation rather than a parallel
    one. See architecture-plan-feature-19.md."""
    return apply_review_action(
        run_id,
        action=payload.action,
        corrected_intent_label=payload.corrected_intent_label,
        reviewer_name=payload.reviewer_name,
        session_factory=session_factory,
        resume_graph_factory=resume_graph_factory,
    )
