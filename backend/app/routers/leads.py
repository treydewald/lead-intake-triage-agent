from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.database.session import SessionLocal
from app.models.pipeline_run import PipelineRun
from app.orchestrator.graph import run_pipeline
from app.orchestrator.state import IntakeSlice, LeadPipelineState
from app.schemas.pipeline import (
    CallbackIntakeRequest,
    EmailIntakeRequest,
    PipelineRunOut,
    TriggerPipelineRunRequest,
)

router = APIRouter(prefix="/leads", tags=["leads"])

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
