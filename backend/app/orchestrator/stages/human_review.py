from __future__ import annotations

from typing import TYPE_CHECKING

from app.orchestrator.contracts import Stage
from app.orchestrator.state import ClassificationSlice, ReviewSlice

if TYPE_CHECKING:
    from app.orchestrator.tool_scope import ScopedToolProxy


class HumanReviewStage(Stage[ClassificationSlice, ReviewSlice]):
    """Feature 06: signals that a lead needs a human decision before CRM Write.

    The routing decision that a review is needed was already made by
    `_route_after_enrich` before this stage ever runs — this stage's only job is to
    mark the pending run as queued. No tool access: this is the first stage whose
    entire job is signaling, not touching external state, so `allowed_tools` stays
    empty per `.claude/portfolio-reference.md`'s Key Decisions.
    """

    name = "human_review"
    input_schema = ClassificationSlice
    output_schema = ReviewSlice
    allowed_tools = frozenset()
    state_slice = "review"
    input_slice = "classification"

    def run(self, data: ClassificationSlice, tools: "ScopedToolProxy") -> ReviewSlice:
        return ReviewSlice(queued=True, paused_at_stage="crm_write")
