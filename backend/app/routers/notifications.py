from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends

from app.database.session import SessionLocal
from app.models.notification import Notification
from app.schemas.notification import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])

SessionFactory = Callable[[], object]


def get_session_factory() -> SessionFactory:
    """FastAPI dependency, overridden in tests - same pattern as
    `app.routers.leads.get_session_factory`."""
    return SessionLocal


@router.get("", response_model=list[NotificationOut])
def list_notifications(session_factory: SessionFactory = Depends(get_session_factory)) -> list[NotificationOut]:
    db = session_factory()
    try:
        items = db.query(Notification).order_by(Notification.created_at.desc()).all()
        return [NotificationOut.model_validate(item) for item in items]
    finally:
        db.close()
