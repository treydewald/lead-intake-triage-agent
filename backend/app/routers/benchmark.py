from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Query

from app.benchmark.harness import run_benchmark
from app.core.config import settings as default_settings
from app.database.session import SessionLocal
from app.models.benchmark import BenchmarkRun
from app.schemas.benchmark import BenchmarkRunListOut, BenchmarkRunOut, BenchmarkRunSummaryOut

router = APIRouter(prefix="/benchmark", tags=["benchmark"])

SessionFactory = Callable[[], object]


def get_session_factory() -> SessionFactory:
    """FastAPI dependency, overridden in tests to bind to an isolated test DB — same
    pattern as `app.routers.leads.get_session_factory`."""
    return SessionLocal


@router.post("/run", response_model=BenchmarkRunOut)
def trigger_benchmark_run(
    repeats: int = Query(default=3, ge=1, le=10),
    session_factory: SessionFactory = Depends(get_session_factory),
) -> BenchmarkRunOut:
    """Runs synchronously and returns the completed run — the dataset is small enough
    that this stays within a reasonable request timeout for local dev/demo use, per
    architecture-plan-feature-09.md's Feature-Specific Requirements."""
    run = run_benchmark(repeats=repeats, session_factory=session_factory, settings=default_settings)
    return BenchmarkRunOut.model_validate(run)


@router.get("/runs", response_model=BenchmarkRunListOut)
def list_benchmark_runs(session_factory: SessionFactory = Depends(get_session_factory)) -> BenchmarkRunListOut:
    db = session_factory()
    try:
        rows = db.query(BenchmarkRun).order_by(BenchmarkRun.created_at.desc()).all()
        return BenchmarkRunListOut(items=[BenchmarkRunSummaryOut.model_validate(row) for row in rows])
    finally:
        db.close()


@router.get("/runs/{run_id}", response_model=BenchmarkRunOut)
def get_benchmark_run(run_id: str, session_factory: SessionFactory = Depends(get_session_factory)) -> BenchmarkRunOut:
    db = session_factory()
    try:
        run = db.get(BenchmarkRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Benchmark run not found")
        return BenchmarkRunOut.model_validate(run)
    finally:
        db.close()
