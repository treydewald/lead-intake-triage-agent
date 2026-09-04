from __future__ import annotations

from app.orchestrator.stages.human_review import HumanReviewStage
from app.orchestrator.state import ClassificationSlice
from app.orchestrator.tool_scope import ToolRegistry


def test_human_review_stage_returns_queued_review_slice():
    stage = HumanReviewStage()
    registry = ToolRegistry()
    proxy = registry.scoped_proxy(stage.allowed_tools, stage.name)

    result = stage.run(
        ClassificationSlice(intent_label="browser", confidence_score=0.2, model_used="test-model"), proxy
    )

    assert result.queued is True
    assert result.paused_at_stage == "crm_write"
    assert result.reviewer_action is None
    assert result.corrected_intent_label is None


def test_human_review_stage_declares_no_tool_access():
    # This stage should never gain tool access - if a future change adds one, that's a
    # signal review logic is creeping into what should stay a pure gate.
    assert HumanReviewStage.allowed_tools == frozenset()
