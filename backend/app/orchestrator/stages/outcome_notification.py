from __future__ import annotations

from typing import TYPE_CHECKING

from app.orchestrator.contracts import Stage
from app.orchestrator.state import NotificationInput, NotificationSlice, RunStatus

if TYPE_CHECKING:
    from app.orchestrator.tool_scope import ScopedToolProxy

_OUTCOME_TYPE_BY_STATUS = {
    RunStatus.RUNNING: "auto_processed",
    RunStatus.FAILED: "failed",
    RunStatus.AWAITING_REVIEW: "awaiting_review",
    RunStatus.REJECTED: "rejected",
}


def _lead_reference(data: NotificationInput) -> str:
    return data.intake.name or data.intake.phone or data.intake.email or data.run.lead_id or "unknown lead"


class OutcomeNotificationStage(Stage[NotificationInput, NotificationSlice]):
    """Feature 07: surfaces the pipeline's outcome as an in-app notification.

    Pure signaling, like `HumanReviewStage` — no tool access. `run.status` at call
    time is what distinguishes the outcome: this stage is only ever invoked once a
    terminal/review-pending status is already set (`RUNNING` here specifically means
    "about to complete successfully," since every other terminal path sets its own
    status before invoking this stage — see `.claude/portfolio-reference.md`'s Key
    Decisions and `architecture-plan-feature-07.md`).
    """

    name = "outcome_notification"
    input_schema = NotificationInput
    output_schema = NotificationSlice
    allowed_tools = frozenset()
    state_slice = "notification"
    input_slices = ("run", "intake", "crm_write")

    def run(self, data: NotificationInput, tools: "ScopedToolProxy") -> NotificationSlice:
        outcome_type = _OUTCOME_TYPE_BY_STATUS.get(data.run.status, "auto_processed")
        lead_ref = _lead_reference(data)

        if outcome_type == "auto_processed":
            message = f"Lead {lead_ref} was auto-processed and written to CRM."
            detail_link = f"/leads/{data.run.lead_id}"
        elif outcome_type == "awaiting_review":
            message = f"Lead {lead_ref} is awaiting human review."
            detail_link = f"/reviews/{data.run.run_id}"
        elif outcome_type == "rejected":
            message = f"Lead {lead_ref}'s classification was rejected by a reviewer."
            detail_link = f"/reviews/{data.run.run_id}"
        else:  # failed
            message = f"Lead {lead_ref}'s pipeline run failed at {data.run.failed_stage}: {data.run.error}"
            detail_link = f"/leads/{data.run.lead_id}"

        return NotificationSlice(
            notified=True,
            outcome_type=outcome_type,
            message=message,
            detail_link=detail_link,
        )
