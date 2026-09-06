from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database.session import SessionLocal
from app.models.pipeline_run import PipelineRun, StageTrace
from app.models.review_queue import ReviewQueueItem
from app.orchestrator.graph import (
    STAGE_ORDER,
    NoFailedRunError,
    RetryGraphFactory,
    build_production_retry_graph,
    retry_pipeline,
    run_pipeline,
)
from app.orchestrator.state import IntakeSlice, LeadPipelineState
from app.schemas.pipeline import (
    CallbackIntakeRequest,
    EmailIntakeRequest,
    LeadDetailOut,
    LeadHistoryOut,
    LeadListItemOut,
    LeadListOut,
    PipelineRunOut,
    StageDetailOut,
    TimelineEntryOut,
    TriggerPipelineRunRequest,
    display_status_for,
    run_status_for_display,
)

router = APIRouter(prefix="/leads", tags=["leads"])

# node_name -> human-readable label, in STAGE_ORDER's canonical order. Mirrored on the
# frontend by `lib/stageOrder.ts` (TypeScript can't import this Python list directly) —
# see architecture-plan-feature-08.md.
_STAGE_LABELS: dict[str, str] = {
    "intake_parsing": "Intake Parsing",
    "intent_classification": "Intent Classification",
    "data_enrichment": "Data Enrichment",
    "hubspot_crm_write": "HubSpot CRM Write",
    "human_review": "Human Review",
    "outcome_notification": "Outcome Notification",
}

SessionFactory = Callable[[], object]


def get_session_factory() -> SessionFactory:
    """FastAPI dependency, overridden in tests to bind the pipeline run and the
    response lookup to an isolated test DB (see `app.tests.conftest.db_session_factory`)."""
    return SessionLocal


def get_retry_graph_factory() -> RetryGraphFactory:
    """Feature 16: FastAPI dependency, overridden in tests to inject a retry graph
    built with fake tool bindings - same pluggable-graph-factory pattern
    `app.routers.reviews.get_resume_graph_factory` already established, for the same
    reason (testable without live HubSpot/Ollama credentials)."""
    return build_production_retry_graph


def _run_and_respond(intake: IntakeSlice, session_factory: SessionFactory) -> PipelineRunOut:
    lead_id = str(uuid4())
    final_state = run_pipeline(lead_id, LeadPipelineState(intake=intake), session_factory=session_factory)

    db = session_factory()
    try:
        run_row = db.get(PipelineRun, final_state.run.run_id)
        return PipelineRunOut.model_validate(run_row)
    finally:
        db.close()


@router.post("/webform", response_model=PipelineRunOut)
def submit_webform(
    payload: TriggerPipelineRunRequest, session_factory: SessionFactory = Depends(get_session_factory)
) -> PipelineRunOut:
    intake = IntakeSlice(
        source_channel="web_form",
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        message_body=payload.message_body,
        raw_input_ref=payload.raw_input_ref,
        received_at=datetime.now(timezone.utc),
    )
    return _run_and_respond(intake, session_factory)


@router.post("/email", response_model=PipelineRunOut)
def submit_email(
    payload: EmailIntakeRequest, session_factory: SessionFactory = Depends(get_session_factory)
) -> PipelineRunOut:
    intake = IntakeSlice(
        source_channel="email",
        message_body=payload.raw_text,
        raw_input_ref=payload.raw_input_ref,
        received_at=datetime.now(timezone.utc),
    )
    return _run_and_respond(intake, session_factory)


@router.post("/callback", response_model=PipelineRunOut)
def submit_callback(
    payload: CallbackIntakeRequest, session_factory: SessionFactory = Depends(get_session_factory)
) -> PipelineRunOut:
    intake = IntakeSlice(
        source_channel="callback",
        message_body=payload.transcript,
        raw_input_ref=payload.raw_input_ref,
        received_at=datetime.now(timezone.utc),
    )
    return _run_and_respond(intake, session_factory)


_SORTS: dict[str, tuple[str, str]] = {
    "created_desc": ("created_at", "desc"),
    "confidence_asc": ("confidence_score", "asc"),
    "confidence_desc": ("confidence_score", "desc"),
}


@router.get("", response_model=LeadListOut)
def list_leads(
    status: str | None = Query(default=None),
    source_channel: str | None = Query(default=None),
    sort: str = Query(default="created_desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session_factory: SessionFactory = Depends(get_session_factory),
) -> LeadListOut:
    """Feature 08: paginated/filterable/sortable lead list, backed entirely by
    `PipelineRun`'s own columns (including the two denormalized ones) — never a
    full-table Python-side filter, per architecture-plan-feature-08.md."""
    db = session_factory()
    try:
        query = db.query(PipelineRun)
        if status is not None:
            raw_status = run_status_for_display(status)
            if raw_status is None:
                raise HTTPException(status_code=422, detail=f"Unknown status filter: {status}")
            query = query.filter(PipelineRun.status == raw_status)
        if source_channel is not None:
            query = query.filter(PipelineRun.source_channel == source_channel)

        total = query.count()

        sort_key = _SORTS.get(sort)
        if sort_key is None:
            raise HTTPException(status_code=422, detail=f"Unknown sort: {sort}")
        column_name, direction = sort_key
        column = getattr(PipelineRun, column_name)
        query = query.order_by(column.desc() if direction == "desc" else column.asc())

        rows = query.offset((page - 1) * page_size).limit(page_size).all()

        items = [
            LeadListItemOut(
                lead_id=row.lead_id,
                run_id=row.id,
                status=display_status_for(row.status),
                source_channel=row.source_channel,
                confidence_score=row.confidence_score,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
        return LeadListOut(items=items, total=total, page=page, page_size=page_size)
    finally:
        db.close()


@router.get("/{lead_id}", response_model=LeadDetailOut)
def get_lead_detail(
    lead_id: str, session_factory: SessionFactory = Depends(get_session_factory)
) -> LeadDetailOut:
    """Feature 08: per-lead stage-by-stage trace, iterating the canonical `STAGE_ORDER`
    so an in-progress or failed-partway lead shows every later stage as `NOT_YET_RUN`
    rather than a blank/missing section — see architecture-plan-feature-08.md."""
    db = session_factory()
    try:
        # Feature 16: a lead can have more than one `PipelineRun` row once a retry has
        # happened (the non-unique `lead_id` Key Decision, first actually exercised by
        # Feature 16) - order by created_at desc so this always reflects the latest
        # attempt, never an arbitrary row. Previously safe without an ORDER BY only
        # because nothing ever created a second row for the same lead_id.
        run_row = (
            db.query(PipelineRun)
            .filter(PipelineRun.lead_id == lead_id)
            .order_by(PipelineRun.created_at.desc())
            .first()
        )
        if run_row is None:
            raise HTTPException(status_code=404, detail="Lead not found")

        traces_by_stage: dict[str, StageTrace] = {
            trace.stage_name: trace
            for trace in db.query(StageTrace).filter(StageTrace.run_id == run_row.id).all()
        }

        failed_stage: str | None = None
        error: str | None = None
        stages: list[StageDetailOut] = []
        for _slice_name, node_name, _feature_id in STAGE_ORDER:
            trace = traces_by_stage.get(node_name)
            if trace is None:
                stages.append(
                    StageDetailOut(
                        stage_key=node_name,
                        stage_label=_STAGE_LABELS[node_name],
                        status="NOT_YET_RUN",
                    )
                )
                continue

            decision = json.loads(trace.output_snapshot) if trace.output_snapshot is not None else None
            stages.append(
                StageDetailOut(
                    stage_key=node_name,
                    stage_label=_STAGE_LABELS[node_name],
                    status=trace.status,
                    decision=decision,
                    error=trace.error,
                    created_at=trace.created_at,
                )
            )
            if trace.status == "FAILED":
                failed_stage = node_name
                error = trace.error

        return LeadDetailOut(
            lead_id=run_row.lead_id,
            run_id=run_row.id,
            status=display_status_for(run_row.status),
            source_channel=run_row.source_channel,
            confidence_score=run_row.confidence_score,
            created_at=run_row.created_at,
            updated_at=run_row.updated_at,
            failed_stage=failed_stage,
            error=error,
            stages=stages,
        )
    finally:
        db.close()


@router.post("/{lead_id}/retry", response_model=PipelineRunOut)
def retry_lead(
    lead_id: str,
    session_factory: SessionFactory = Depends(get_session_factory),
    retry_graph_factory: RetryGraphFactory = Depends(get_retry_graph_factory),
) -> PipelineRunOut:
    """Feature 16: retry the lead's most recent FAILED run from the stage that raised
    - never a bespoke stage-calling code path, see `retry_pipeline`/`build_retry_graph`
    in `app.orchestrator.graph` and architecture-plan-feature-16.md."""
    try:
        final_state = retry_pipeline(lead_id, graph_factory=retry_graph_factory, session_factory=session_factory)
    except NoFailedRunError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db = session_factory()
    try:
        run_row = db.get(PipelineRun, final_state.run.run_id)
        return PipelineRunOut.model_validate(run_row)
    finally:
        db.close()


@router.get("/{lead_id}/history", response_model=LeadHistoryOut)
def get_lead_history(
    lead_id: str, session_factory: SessionFactory = Depends(get_session_factory)
) -> LeadHistoryOut:
    """Feature 11: full chronological history across every `PipelineRun` attempt
    sharing this `lead_id` (there is no uniqueness constraint on that column, and none
    is added here — see architecture-plan-feature-11.md's multi-attempt gap note),
    merging stage transitions with any actioned human-review decision. Deliberately
    distinct from `get_lead_detail` above: that endpoint answers "what's true now" for
    the most recent/only run via `.first()`; this one answers "what happened, in order"
    across however many runs exist, so it never uses `.first()`."""
    db = session_factory()
    try:
        run_rows = (
            db.query(PipelineRun).filter(PipelineRun.lead_id == lead_id).order_by(PipelineRun.created_at).all()
        )
        if not run_rows:
            raise HTTPException(status_code=404, detail="Lead not found")

        entries: list[TimelineEntryOut] = []
        run_ids = [run_row.id for run_row in run_rows]
        all_traces = (
            db.query(StageTrace)
            .filter(StageTrace.run_id.in_(run_ids))
            .order_by(StageTrace.created_at)
            .all()
        )
        traces_by_run: dict[str, list[StageTrace]] = {run_id: [] for run_id in run_ids}
        for trace in all_traces:
            traces_by_run[trace.run_id].append(trace)

        for run_row in run_rows:
            for trace in traces_by_run[run_row.id]:
                entries.append(
                    TimelineEntryOut(
                        kind="stage",
                        run_id=run_row.id,
                        stage_key=trace.stage_name,
                        stage_label=_STAGE_LABELS.get(trace.stage_name, trace.stage_name),
                        status=trace.status,
                        error=trace.error,
                        created_at=trace.created_at,
                    )
                )

        review_items = db.query(ReviewQueueItem).filter(ReviewQueueItem.lead_id == lead_id).all()
        for item in review_items:
            if item.status != "ACTIONED":
                # A PENDING item has no reviewer decision yet - emitting nothing here is
                # what keeps an auto-processed (or still-pending) lead's timeline free of
                # a fabricated review entry.
                continue
            entries.append(
                TimelineEntryOut(
                    kind="review_action",
                    run_id=item.run_id,
                    reviewer_action=item.reviewer_action,
                    corrected_intent_label=item.corrected_intent_label,
                    reviewer_name=item.reviewer_name,
                    created_at=item.actioned_at,
                )
            )

        entries.sort(key=lambda entry: entry.created_at)
        return LeadHistoryOut(lead_id=lead_id, entries=entries)
    finally:
        db.close()
