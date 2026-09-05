from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database.session import SessionLocal
from app.models.pipeline_run import PipelineRun, StageTrace
from app.orchestrator.graph import STAGE_ORDER, run_pipeline
from app.orchestrator.state import IntakeSlice, LeadPipelineState
from app.schemas.pipeline import (
    CallbackIntakeRequest,
    EmailIntakeRequest,
    LeadDetailOut,
    LeadListItemOut,
    LeadListOut,
    PipelineRunOut,
    StageDetailOut,
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
        run_row = db.query(PipelineRun).filter(PipelineRun.lead_id == lead_id).first()
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
