from app.models.pipeline_run import PipelineRun, StageTrace


def test_pipeline_run_and_stage_trace_round_trip(db_session_factory):
    db = db_session_factory()
    try:
        run = PipelineRun(lead_id="lead-1", status="RUNNING")
        db.add(run)
        db.commit()
        db.refresh(run)

        trace = StageTrace(
            run_id=run.id,
            stage_name="intake_parsing",
            input_snapshot=None,
            output_snapshot='{"source_channel": "web_form"}',
            status="COMPLETED",
            error=None,
        )
        db.add(trace)
        db.commit()

        fetched = db.get(PipelineRun, run.id)
        assert fetched is not None
        assert fetched.lead_id == "lead-1"
        assert len(fetched.stage_traces) == 1
        assert fetched.stage_traces[0].stage_name == "intake_parsing"
    finally:
        db.close()


def test_stage_traces_queryable_per_lead(db_session_factory):
    db = db_session_factory()
    try:
        run = PipelineRun(lead_id="lead-2", status="RUNNING")
        db.add(run)
        db.commit()
        db.refresh(run)

        for stage_name in ["intake_parsing", "intent_classification"]:
            db.add(StageTrace(run_id=run.id, stage_name=stage_name, status="COMPLETED"))
        db.commit()

        traces = (
            db.query(StageTrace)
            .join(PipelineRun)
            .filter(PipelineRun.lead_id == "lead-2")
            .order_by(StageTrace.created_at)
            .all()
        )
        assert [t.stage_name for t in traces] == ["intake_parsing", "intent_classification"]
    finally:
        db.close()
