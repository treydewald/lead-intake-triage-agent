from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Callable
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import settings
from app.database.session import SessionLocal
from app.orchestrator.graph import build_production_resume_graph
from app.orchestrator.review_actions import GraphFactory, SessionFactory, apply_review_action

router = APIRouter(prefix="/slack", tags=["slack"])

# Slack's own recommended replay-protection window - reject anything older than this
# even if the signature itself is otherwise valid. See architecture-plan-feature-19.md's
# Risks section.
_MAX_TIMESTAMP_SKEW_SECONDS = 60 * 5

# The only two button actions this round supports (see architecture-plan-feature-19.md's
# Feature-Specific Requirements for why "edit" is explicitly out of scope).
_ACTION_ID_TO_REVIEW_ACTION: dict[str, str] = {
    "approve_lead": "approve",
    "reject_lead": "reject",
}


def get_session_factory() -> SessionFactory:
    """FastAPI dependency, overridden in tests - same pattern every other router uses."""
    return SessionLocal


def get_resume_graph_factory() -> GraphFactory:
    """FastAPI dependency, overridden in tests - same pattern
    `app.routers.reviews.get_resume_graph_factory` already established."""
    return build_production_resume_graph


def verify_slack_signature(*, signing_secret: str | None, timestamp: str | None, body: bytes, signature: str | None) -> bool:
    """Slack's own HMAC-SHA256 request-verification scheme: `v0={hmac(secret,
    f"v0:{timestamp}:{body}")}`, constant-time compared against the `X-Slack-Signature`
    header. Fails closed on any missing input (no secret configured, no signature
    header, no timestamp header) rather than treating a missing value as "skip the
    check" - see architecture-plan-feature-19.md's Risks section.

    Pure and independent of any live Slack service - fully unit-testable with a
    self-computed signature (`test_slack_signature.py`).
    """
    if not signing_secret or not timestamp or not signature:
        return False
    try:
        request_time = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - request_time) > _MAX_TIMESTAMP_SKEW_SECONDS:
        return False

    basestring = b"v0:" + timestamp.encode() + b":" + body
    computed = "v0=" + hmac.new(signing_secret.encode(), basestring, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


@router.post("/interactions")
async def slack_interactions(
    request: Request,
    session_factory: SessionFactory = Depends(get_session_factory),
    resume_graph_factory: GraphFactory = Depends(get_resume_graph_factory),
) -> dict:
    """Feature 19: Slack's interactive-component callback - a real inbound trust
    boundary. Signature verification happens before any parsing of the body's
    contents; a valid Approve/Reject click routes through the exact same
    `apply_review_action()` implementation `POST /reviews/{run_id}/action` uses. See
    architecture-plan-feature-19.md."""
    body = await request.body()
    if not verify_slack_signature(
        signing_secret=settings.slack_signing_secret,
        timestamp=request.headers.get("X-Slack-Request-Timestamp"),
        body=body,
        signature=request.headers.get("X-Slack-Signature"),
    ):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    fields = parse_qs(body.decode())
    raw_payload = fields.get("payload", [None])[0]
    if not raw_payload:
        raise HTTPException(status_code=400, detail="Missing payload field")

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Malformed payload JSON") from exc

    actions = payload.get("actions") or []
    if not actions:
        raise HTTPException(status_code=400, detail="No action in payload")

    action_id = actions[0].get("action_id")
    run_id = actions[0].get("value")
    review_action = _ACTION_ID_TO_REVIEW_ACTION.get(action_id)
    if review_action is None or not run_id:
        raise HTTPException(status_code=400, detail=f"Unrecognized action_id: {action_id}")

    reviewer_name = (payload.get("user") or {}).get("username")

    try:
        result = apply_review_action(
            run_id,
            action=review_action,
            corrected_intent_label=None,
            reviewer_name=reviewer_name,
            session_factory=session_factory,
            resume_graph_factory=resume_graph_factory,
        )
    except HTTPException as exc:
        # A business-outcome failure (already actioned / no such run) - Slack expects
        # 200 to acknowledge receipt; a non-2xx response causes Slack to retry, which
        # would misfire against an already-idempotent claim. See
        # architecture-plan-feature-19.md's System Behaviors.
        return {"response_type": "ephemeral", "text": f"Could not process this action: {exc.detail}"}

    return {
        "response_type": "in_channel",
        "replace_original": True,
        "text": f"Lead {result.lead_id} was {review_action}d by {reviewer_name or 'a reviewer'} via Slack.",
    }
