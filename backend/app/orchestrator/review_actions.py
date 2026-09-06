from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from fastapi import HTTPException
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy import update

from app.models.pipeline_run import PipelineRun
from app.models.review_queue import ReviewQueueItem
from app.orchestrator.graph import persist_outcome_notification, resume_pipeline
from app.orchestrator.stages.outcome_notification import OutcomeNotificationStage
from app.orchestrator.state import LeadPipelineState, RunStatus
from app.orchestrator.tool_scope import ToolRegistry
from app.schemas.pipeline import PipelineRunOut

SessionFactory = Callable[[], object]
GraphFactory = Callable[[SessionFactory], CompiledStateGraph]


def apply_review_action(
    run_id: str,
    *,
    action: str,
    corrected_intent_label: str | None,
    reviewer_name: str | None,
    session_factory: SessionFactory,
    resume_graph_factory: GraphFactory,
) -> PipelineRunOut:
    """The single implementation of "act on a queued review" — extracted from
    `routers/reviews.py`'s `action_review` (Feature 06/11) so a second transport-layer
    entry point (Feature 19's Slack callback) can call the exact same logic rather than
    a parallel reimplementation, per architecture-plan-feature-19.md's Architecture Rule
    Change: domain logic reachable from more than one transport lives here, in
    `app/orchestrator/`, never duplicated per-transport.

    Raises the same `HTTPException`s `action_review` always has (422/404/409) — callers
    from a non-HTTP transport (e.g. Slack) are expected to catch and translate these,
    not treat them as unreachable.
    """
    if action == "edit" and not corrected_intent_label:
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
                reviewer_action=action,
                corrected_intent_label=corrected_intent_label,
                reviewer_name=reviewer_name,
                actioned_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=409, detail="Review item already actioned")

        state_snapshot = item.state_snapshot

        if action == "reject":
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
        update={"reviewer_action": action, "corrected_intent_label": corrected_intent_label}
    )
    if action == "edit":
        state.classification = state.classification.model_copy(update={"intent_label": corrected_intent_label})

    final_state = resume_pipeline(
        run_id, state, graph=resume_graph_factory(session_factory), session_factory=session_factory
    )

    db = session_factory()
    try:
        run_row = db.get(PipelineRun, final_state.run.run_id)
        return PipelineRunOut.model_validate(run_row)
    finally:
        db.close()
